# For User — Practical Guide

How to actually run this system, what to expect, and what to watch out for.
Written for the project owner, not for AI.

---

## Will PostgreSQL tables be created correctly?

**Short answer: YES — automatically, before any data is inserted.**

Here is exactly what happens when you run `run_new_schema.py` without `--dry-run`:

1. The script connects to PostgreSQL using the credentials in `settings_jsons/pipeline_config.json`.
2. For each file (e.g. `EURUSD_1H.txt`), before touching any data, it calls `create_new_schema_table(conn, "eurusd_1h")`.
3. That function runs `CREATE TABLE IF NOT EXISTS eurusd_1h (...)` — safe to run repeatedly, does nothing if the table already exists.
4. Then it creates 6 indices on the table (for date, directions, and outcomes).
5. Then the loop starts inserting rows one by one.

**The 12 tables that will be created:**

| Table | Source file |
|-------|-------------|
| `eurusd_1h` | EURUSD_1H.txt |
| `eurusd_1d` | EURUSD_1D.txt |
| `gbpusd_1h` | GBPUSD_1H.txt |
| `gbpusd_1d` | GBPUSD_1D.txt |
| `audusd_1h` | AUDUSD_1H.txt |
| `audusd_1d` | AUDUSD_1D.txt |
| `eurchf_1h` | EURCHF_1H.txt |
| `eurchf_1d` | EURCHF_1D.txt |
| `usdjpy_1h` | USDJPY_1H.txt |
| `usdjpy_1d` | USDJPY_1D.txt |
| `xauusd_1h` | XAUUSD_1H.txt |
| `xauusd_1d` | XAUUSD_1D.txt |

**You can verify in psql or pgAdmin:**
```sql
\dt          -- lists all tables
SELECT COUNT(*) FROM eurusd_1h;   -- check row count after run
```

---

## Step-by-step: running the full batch

### Step 1 — Verify DB connection
Make sure PostgreSQL is running and credentials in `settings_jsons/pipeline_config.json` are correct:
```json
"database": {
    "host": "localhost",
    "port": 5432,
    "user": "your_db_user",
    "password": "${POSTGRES_PASSWORD}",
    "database": "forex_analysis"
}
```
The database `forex_analysis` must already exist. The tables inside it will be created automatically.

### Step 2 — Test one pair first (real write)
```bash
python run_new_schema.py --pair EURUSD --tf 1H --step 100
```
This inserts ~1,486 rows into `eurusd_1h`. Fast (~70 seconds). Check the result in PostgreSQL before going further.

### Step 3 — Verify the data looks right
```sql
SELECT * FROM eurusd_1h LIMIT 5;
SELECT COUNT(*) FROM eurusd_1h;
SELECT end_up_reason, COUNT(*) FROM eurusd_1h GROUP BY end_up_reason;
SELECT end_down_reason, COUNT(*) FROM eurusd_1h GROUP BY end_down_reason;
```
You should see a mix of `TAKE_PROFIT`, `STOP_LOSS`, and `MAX_DURATION` in the reason columns.

### Step 4 — Full run (all pairs, all timeframes, every candle)
```bash
python run_new_schema.py --step 1
```
This is a long job. See timing estimates below.

---

## Time estimates

At step=1 (every candle), measured ~21 rows/second on EURUSD 1H.

| File | Rows | Estimated time |
|------|------|----------------|
| `*_1H.txt` (each) | ~148,000 rows | ~2 hours |
| `*_1D.txt` (each) | ~6,000 rows | ~5 minutes |
| **All 6 pairs × 1H** | ~890,000 rows | **~12 hours** |
| **All 6 pairs × 1D** | ~36,000 rows | **~30 minutes** |
| **Grand total** | ~926,000 rows | **~13 hours** |

**Recommendation:** Run it overnight.
```bash
python run_new_schema.py --step 1
```
You can interrupt at any time (Ctrl+C) — the data already inserted is committed and safe. Re-running will skip duplicates automatically (`ON CONFLICT DO NOTHING`).

---

## Re-running safely

The table has a unique constraint on `(ticker, timeframe, full_date_open)`. This means:
- Running the same command twice will **not create duplicates**
- Interrupted runs can be **resumed** by just running again
- You can safely re-run any pair/timeframe after a crash

---

## Useful CLI options

```bash
# Dry run — no DB, just preview 3 rows per file
python run_new_schema.py --dry-run

# One specific pair
python run_new_schema.py --pair EURUSD

# One timeframe only
python run_new_schema.py --tf 1D

# Faster test run (every 100th candle)
python run_new_schema.py --step 100

# All combinations work together
python run_new_schema.py --pair GBPUSD --tf 1H --step 50 --dry-run
```

---

## What to do if something goes wrong

### "DB connection failed"
- Is PostgreSQL running?
- Check credentials in `settings_jsons/pipeline_config.json`
- Does the database `forex_analysis` exist? Create it if not:
  ```sql
  CREATE DATABASE forex_analysis;
  ```

### "No matching files found in input_data/"
- Check that the files are named exactly `EURUSD_1H.txt`, `EURUSD_1D.txt`, etc.
- Only `_1H` and `_1D` timeframes are processed (not 15m, 1W, MN)

### Errors during processing (non-zero error count)
- Individual row errors are printed and skipped — the run continues
- Re-run after fixing; duplicates are skipped automatically

### Table seems empty after run
- Check the error count in the final summary
- Try `--dry-run` to confirm data is being generated correctly
- Check that the DB name in config matches where you are looking

---

## What the data means (quick reference)

Each row = one analysed candle (one cutoff point in historical data).

| Column | Meaning |
|--------|---------|
| `full_date_open` | The candle datetime used as analysis cutoff |
| `linear_direction` | What linear regression says: UP / DOWN / NEUTRAL |
| `logarithmic_direction` | What quadratic regression says |
| `candle_direction` | What candlestick patterns say |
| `long_tp / long_sl` | The TP and SL levels for a LONG trade at this candle |
| `short_tp / short_sl` | The TP and SL levels for a SHORT trade |
| `end_up_reason` | How the LONG trade actually ended |
| `end_up_close_price` | Price when the LONG trade closed |
| `end_up_close_date` | When the LONG trade closed |
| `end_down_reason` | How the SHORT trade actually ended |
| `end_down_close_price` | Price when the SHORT trade closed |
| `end_down_close_date` | When the SHORT trade closed |

**Possible reasons (outcomes):**
- `TAKE_PROFIT` — price hit the TP level → trade won
- `STOP_LOSS` — price hit the SL level → trade lost
- `MAX_DURATION` — neither hit within 7 days → closed at last bar price (configurable in `settings_jsons/trade_maker_settings.json`)
- `OPEN` — no max_duration set and neither hit (shouldn't appear — max_duration IS set)
- `INVALID` — something was wrong with the levels or trade setup
- `NO_FUTURE_DATA` — cutoff was too close to the end of the file

---

## Settings that control the analysis

All in `settings_jsons/`:

| What to change | File | Key |
|----------------|------|-----|
| TP level (how far above) | `trade_maker_settings.json` | `trade_maker.tp_level_index` (currently 3) |
| SL level (how far below) | `trade_maker_settings.json` | `trade_maker.sl_level_index` (currently -3) |
| Max trade duration | `trade_maker_settings.json` | `trade_maker.max_duration` (currently 7 days) |
| S/R detection sensitivity | `level_finder_settings.json` | per-timeframe blocks |
| PostgreSQL connection | `pipeline_config.json` | `database` block |

**Important:** If you change settings, the old and new data are not comparable. Truncate the tables and re-run, or use a different table naming scheme.

---

## Files added to the project (2026-04-05)

| File | What it does |
|------|-------------|
| `run_new_schema.py` | The batch runner — this is what you run |
| `AI_tools/new_schema.md` | Technical reference for AI assistants |
| `AI_tools/for_user.md` | This file |
| `AI_tools/readme_sum_up.md` | Full project overview for AI assistants |
