"""
smoke_test.py
─────────────
Step-by-step test of the new multi-method pipeline.

What it does:
  1. Find first CSV in input_data/
  2. Connect to PostgreSQL
  3. Create table for this settings combo (new schema)
  4. Run run_all_methods() on one cutoff point
  5. Build combined DB row via OneDayOutput.from_all_methods()
  6. Print the row — optionally insert to DB

Run:
  python smoke_test.py
"""

import json
import sys
from pathlib import Path

import pandas as pd
import psycopg2

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE = Path(__file__).parent
SETTINGS_DIR  = BASE / "settings_jsons"
INPUT_DIR     = BASE / "input_data"
PIPELINE_CFG  = SETTINGS_DIR / "pipeline_config.json"

LEVEL_SETTINGS_PATH     = str(SETTINGS_DIR / "level_finder_settings.json")
TRADE_MAKER_SETTINGS_PATH = str(SETTINGS_DIR / "trade_maker_settings.json")

# ── Config ────────────────────────────────────────────────────────────────────

with open(PIPELINE_CFG, encoding="utf-8") as f:
    cfg = json.load(f)

DB_PARAMS = {k: cfg["database"][k] for k in ("host", "port", "user", "password", "database")}
TIMEFRAME = cfg["analysis"]["timeframe"]   # "H1"

# how many bars from the start to use as cutoff for this test
TEST_CUTOFF_BAR = 500


# ── Step 1: find CSV ──────────────────────────────────────────────────────────

def load_csv() -> tuple[pd.DataFrame, Path]:
    # prefer H1 files; fallback to first available
    all_csvs = sorted(INPUT_DIR.glob("*.csv")) + sorted(INPUT_DIR.glob("*.txt"))
    if not all_csvs:
        print(f"[ERROR] No CSV/TXT files in {INPUT_DIR}")
        sys.exit(1)

    h1_csvs = [p for p in all_csvs if "h1" in p.stem.lower() or "1h" in p.stem.lower()]
    path = h1_csvs[0] if h1_csvs else all_csvs[0]
    if not h1_csvs:
        print(f"    [WARN] No H1 file found — using {path.name}. Set TIMEFRAME accordingly.")
    print(f"[1] Loading: {path.name}")

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
    print(f"    Rows: {len(df)} | Range: {df.index[0]} → {df.index[-1]}")
    return df, path


# ── Step 2: DB connection ─────────────────────────────────────────────────────

def connect_db() -> psycopg2.extensions.connection:
    print(f"\n[2] Connecting to PostgreSQL: {DB_PARAMS['host']}:{DB_PARAMS['port']}/{DB_PARAMS['database']}")
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        conn.autocommit = False
        print("    Connected OK")
        return conn
    except Exception as e:
        print(f"[ERROR] DB connection failed: {e}")
        print("    Check DB_PARAMS in pipeline_config.json and that PostgreSQL is running.")
        sys.exit(1)


# ── Step 3: create table ──────────────────────────────────────────────────────

def ensure_table(conn, table_name: str):
    print(f"\n[3] Ensuring table: {table_name}")
    from database_handling.table_manager.table_manager import create_table_if_not_exists
    try:
        create_table_if_not_exists(conn, table_name)
        conn.commit()
        print("    Table ready")
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Table creation failed: {e}")
        raise


# ── Step 4: run all methods ───────────────────────────────────────────────────

def run_analysis(df: pd.DataFrame) -> dict:
    from one_day_proceeding.one_day_proceeding import OneDayProceeding

    cutoff = df.index[TEST_CUTOFF_BAR]
    print(f"\n[4] Running all methods | cutoff: {cutoff} (bar {TEST_CUTOFF_BAR})")

    processor = OneDayProceeding(
        df                         = df,
        cutoff_datetime            = cutoff,
        timeframe                  = TIMEFRAME,
        level_finder_settings_path = LEVEL_SETTINGS_PATH,
        trade_maker_settings_path  = TRADE_MAKER_SETTINGS_PATH,
    )

    # max_duration_seconds is now read from JSON internally
    results = processor.run_all_methods()

    for method, result in results.items():
        outcome  = result.get("outcome", "?")
        direction = result.get("direction", "?")
        print(f"    {method:12s} → direction={direction:8s} outcome={outcome}")

    return results


# ── Step 5: build combined row ────────────────────────────────────────────────

def build_row(results: dict) -> dict:
    from one_day_proceeding.one_day_output.one_day_output import OneDayOutput

    print("\n[5] Building combined DB row")
    # max_duration_seconds is now read from JSON internally
    row = OneDayOutput.from_all_methods(results)

    # print key fields
    print(f"    open_price    : {row.get('open_price')}")
    print(f"    open_datetime : {row.get('open_datetime')}")
    print(f"    max_duration  : {row.get('max_duration_seconds')}s")
    for prefix, name in [("lin", "linear"), ("quad", "quadratic"), ("cnd", "candle")]:
        print(f"    {name:12s} → tp_long={row.get(f'{prefix}_tp_long')}  outcome={row.get(f'{prefix}_outcome')}")

    return row


# ── Step 6: insert ────────────────────────────────────────────────────────────

def insert_row(conn, table_name: str, row: dict):
    from database_handling.data_operations.data_operations import DataOperations

    print(f"\n[6] Inserting row into {table_name}")
    ops = DataOperations(conn)
    try:
        ops.insert_trade(table_name, **row)
        conn.commit()
        print("    Insert OK")
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Insert failed: {e}")
        raise


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("═" * 55)
    print("  SMOKE TEST — new multi-method pipeline")
    print("═" * 55)

    df, csv_path = load_csv()

    # table name: symbol + timeframe (e.g. eurusd_H1_test)
    symbol     = csv_path.stem.lower()
    table_name = f"{symbol}_{TIMEFRAME.lower()}_test"
    print(f"\n    Symbol: {symbol} | Table: {table_name}")

    conn = connect_db()

    try:
        ensure_table(conn, table_name)
        results = run_analysis(df)
        row     = build_row(results)

        print("\n─── Insert to DB? ───")
        ans = input("Insert row? (y/n): ").strip().lower()
        if ans == "y":
            insert_row(conn, table_name, row)
        else:
            print("    Skipped — row printed above only")

    finally:
        conn.close()
        print("\n[DONE] Connection closed")


if __name__ == "__main__":
    main()