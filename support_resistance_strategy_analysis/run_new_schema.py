"""
run_new_schema.py
─────────────────
Batch runner for the new analysis schema.

For every *_1H.txt and *_1D.txt file in input_data/ it:
  1. Loads the OHLC data
  2. Iterates through each candle (step=1 by default — every candle)
  3. Calls OneDayProceeding.run_new_schema() at each cutoff point
  4. Saves the result row to PostgreSQL via create_new_schema_table / insert_new_schema_row

DB tables are named:  {ticker_lower}_{timeframe_lower}
  e.g.  eurusd_1h,  gbpusd_1d,  xauusd_1h  …

Run:
    python run_new_schema.py                   # all pairs, step=1
    python run_new_schema.py --step 10         # every 10th candle
    python run_new_schema.py --pair EURUSD     # single pair only
    python run_new_schema.py --tf 1H           # single timeframe only
    python run_new_schema.py --dry-run         # no DB writes, prints rows only
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2

# ── Paths ──────────────────────────────────────────────────────────────────────

BASE         = Path(__file__).parent
SETTINGS_DIR = BASE / "settings_jsons"
INPUT_DIR    = BASE / "input_data"
PIPELINE_CFG = SETTINGS_DIR / "pipeline_config.json"

LEVEL_SETTINGS_PATH      = str(SETTINGS_DIR / "level_finder_settings.json")
TRADE_MAKER_SETTINGS_PATH = str(SETTINGS_DIR / "trade_maker_settings.json")

# ── Timeframe normalisation ────────────────────────────────────────────────────
# Filename uses "1H" / "1D"; LevelHandler JSON keys and OneDayProceeding expect "H1" / "D1"

TF_FILE_TO_INTERNAL = {"1H": "H1", "1D": "D1"}

# Pairs and timeframes we process
TARGET_TIMEFRAMES = {"1H", "1D"}


# ── Config ─────────────────────────────────────────────────────────────────────

with open(PIPELINE_CFG, encoding="utf-8") as f:
    _cfg = json.load(f)

DB_PARAMS = {k: _cfg["database"][k] for k in ("host", "port", "user", "password", "database")}

# Minimum number of historical bars before the first analysis
MIN_HISTORY = 200


# ── File discovery ─────────────────────────────────────────────────────────────

def discover_files(pair_filter: str = None, tf_filter: str = None):
    """
    Returns list of (path, ticker, file_timeframe, internal_timeframe, table_name)
    for all matching *_1H.txt and *_1D.txt files.
    """
    files = []
    for path in sorted(INPUT_DIR.glob("*.txt")):
        stem  = path.stem           # e.g. EURUSD_1H
        parts = stem.rsplit("_", 1)
        if len(parts) != 2:
            continue
        ticker, tf = parts[0].upper(), parts[1].upper()

        if tf not in TARGET_TIMEFRAMES:
            continue
        if pair_filter and ticker != pair_filter.upper():
            continue
        if tf_filter and tf != tf_filter.upper():
            continue

        internal_tf = TF_FILE_TO_INTERNAL[tf]
        table_name  = f"{ticker.lower()}_{tf.lower()}"   # e.g. eurusd_1h
        files.append((path, ticker, tf, internal_tf, table_name))

    return files


# ── Data loading ───────────────────────────────────────────────────────────────

def load_file(path: Path) -> pd.DataFrame:
    """Loads a 7-column headerless OHLC file into a DatetimeIndex DataFrame."""
    df = pd.read_csv(
        path,
        names=["date", "hour", "open", "high", "low", "close", "w_avre"],
        header=None,
    )
    df["datetime"] = pd.to_datetime(
        df["date"].astype(str) + df["hour"].astype(str).str.zfill(6),
        format="%Y%m%d%H%M%S",
    )
    df.set_index("datetime", inplace=True)
    return df


# ── DB helpers ─────────────────────────────────────────────────────────────────

def connect_db() -> psycopg2.extensions.connection:
    conn = psycopg2.connect(**DB_PARAMS)
    conn.autocommit = False
    return conn


# ── Core processing ────────────────────────────────────────────────────────────

def process_file(
    conn,
    path: Path,
    ticker: str,
    tf_display: str,
    tf_internal: str,
    table_name: str,
    step: int,
    dry_run: bool,
):
    from one_day_proceeding.one_day_proceeding import OneDayProceeding
    from one_day_proceeding.one_day_output.one_day_output import OneDayOutput
    from database_handling.table_manager import create_new_schema_table, insert_new_schema_row

    print(f"\n{'─'*60}")
    print(f"  {ticker} {tf_display}  →  table: {table_name}")
    print(f"  File: {path.name}")

    df = load_file(path)
    print(f"  Rows: {len(df):,}  |  {df.index[0]}  →  {df.index[-1]}")

    if not dry_run:
        create_new_schema_table(conn, table_name)
        print(f"  Table ready.")

    total_candles  = len(df)
    cutoff_indices = range(MIN_HISTORY, total_candles, step)
    n_total        = len(cutoff_indices)

    inserted = skipped = errors = 0
    t0 = time.time()

    for i, idx in enumerate(cutoff_indices):
        cutoff = df.index[idx]

        try:
            processor = OneDayProceeding(
                df                         = df,
                cutoff_datetime            = cutoff,
                timeframe                  = tf_internal,
                level_finder_settings_path = LEVEL_SETTINGS_PATH,
                trade_maker_settings_path  = TRADE_MAKER_SETTINGS_PATH,
            )
            result = processor.run_new_schema()

            if "error" in result:
                skipped += 1
                continue

            row = OneDayOutput.to_new_schema_row(result, ticker, tf_display)
            if row is None:
                skipped += 1
                continue

            if dry_run:
                if i < 3:          # print first 3 rows for preview
                    print(f"  [DRY-RUN] {row}")
                inserted += 1
            else:
                ok = insert_new_schema_row(conn, table_name, row)
                if ok:
                    inserted += 1
                else:
                    skipped += 1   # duplicate or conflict

        except Exception as exc:
            errors += 1
            print(f"  [ERROR] idx={idx} cutoff={cutoff}: {exc}")

        # Progress report every 500 iterations
        if (i + 1) % 500 == 0 or (i + 1) == n_total:
            elapsed  = time.time() - t0
            pct      = (i + 1) / n_total * 100
            rate     = (i + 1) / elapsed if elapsed > 0 else 0
            eta_sec  = (n_total - i - 1) / rate if rate > 0 else 0
            print(
                f"  [{i+1:>{len(str(n_total))}}/{n_total}] "
                f"{pct:5.1f}%  |  ins={inserted}  skip={skipped}  err={errors}  "
                f"|  {rate:.1f} rows/s  ETA {eta_sec/60:.1f} min"
            )

    elapsed = time.time() - t0
    print(f"\n  Done in {elapsed:.1f}s — inserted={inserted}  skipped={skipped}  errors={errors}")
    return inserted, skipped, errors


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="New-schema batch processor")
    parser.add_argument("--step",    type=int,  default=1,     help="Candle step (default=1, every candle)")
    parser.add_argument("--pair",    type=str,  default=None,  help="Filter to one ticker, e.g. EURUSD")
    parser.add_argument("--tf",      type=str,  default=None,  help="Filter to one timeframe, e.g. 1H")
    parser.add_argument("--dry-run", action="store_true",      help="Skip DB writes, preview output only")
    args = parser.parse_args()

    files = discover_files(pair_filter=args.pair, tf_filter=args.tf)
    if not files:
        print("[ERROR] No matching files found in input_data/")
        sys.exit(1)

    print(f"{'═'*60}")
    print(f"  NEW SCHEMA BATCH RUNNER")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Files found : {len(files)}")
    print(f"  Step        : {args.step}")
    print(f"  Dry-run     : {args.dry_run}")
    print(f"  DB          : {DB_PARAMS['host']}:{DB_PARAMS['port']}/{DB_PARAMS['database']}")
    print(f"{'═'*60}")

    conn = None
    if not args.dry_run:
        print("\nConnecting to PostgreSQL …")
        try:
            conn = connect_db()
            print("  Connected OK")
        except Exception as e:
            print(f"[ERROR] DB connection failed: {e}")
            sys.exit(1)

    grand_inserted = grand_skipped = grand_errors = 0

    try:
        for (path, ticker, tf_display, tf_internal, table_name) in files:
            ins, sk, err = process_file(
                conn       = conn,
                path       = path,
                ticker     = ticker,
                tf_display = tf_display,
                tf_internal= tf_internal,
                table_name = table_name,
                step       = args.step,
                dry_run    = args.dry_run,
            )
            grand_inserted += ins
            grand_skipped  += sk
            grand_errors   += err
    finally:
        if conn:
            conn.close()

    print(f"\n{'═'*60}")
    print(f"  ALL FILES DONE")
    print(f"  Total inserted : {grand_inserted:,}")
    print(f"  Total skipped  : {grand_skipped:,}")
    print(f"  Total errors   : {grand_errors:,}")
    print(f"{'═'*60}")


if __name__ == "__main__":
    main()
