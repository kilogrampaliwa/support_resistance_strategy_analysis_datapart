# Support & Resistance Strategy Analysis

A Python backtesting system for evaluating support/resistance-based trading strategies on historical Forex OHLC data. Built as a bachelor's thesis project.

The system scans historical candles, detects support/resistance levels, simulates both a LONG and SHORT trade at each candle, and records the outcome in PostgreSQL for statistical analysis.

---

## What it does

For every candle in a dataset the pipeline:

1. **Detects S/R levels** — combines pivot high/low detection with price-frequency histograms across multiple lookback windows (50, 100, 200, all bars).
2. **Estimates trend direction** — runs three independent algorithms (linear regression, quadratic regression, candlestick pattern scoring), each returning `UP` / `DOWN` / `NEUTRAL`.
3. **Sets TP/SL targets** — assigns Take Profit and Stop Loss at the 3rd S/R level above and below the current price (configurable).
4. **Validates outcomes** — scans forward in time to find whether each trade would have hit TP, SL, or expired after a 7-day deadline.
5. **Stores results** in PostgreSQL — one row per candle, one table per ticker+timeframe pair.

The resulting database is used to answer questions such as:
- *When the linear method says UP, does the LONG trade win more than 50% of the time?*
- *Does combining all three direction methods improve the win rate?*
- *Is the strategy more effective on daily candles than hourly?*

---

## Architecture

```
input_data/               ← OHLC .txt files (place locally, not committed)
        │
        ▼
proceed_datasets/           ← Batch orchestration
  ├── dataset_processor.py  ← Entry point
  ├── data_loader/          ← Auto-detect CSV/TXT format
  ├── timeframe_detector/   ← Detect H1/D1/M15/etc. from data or filename
  ├── batch_processor/      ← Iterate DataFrame, dispatch per candle
  └── progress_tracker/     ← Progress %, ETA, error counts
        │
        ▼
one_day_proceeding/         ← Per-candle analysis core
  ├── one_day_proceeding.py ← Main orchestrator (OneDayProceeding)
  ├── levels_finder/        ← Pivot + frequency S/R detection
  ├── levels_handler/       ← Multi-window aggregation and dedup
  ├── direction_guesser/    ← linear / quadratic / candle methods
  ├── trade_maker/          ← TP/SL assignment from levels
  ├── trade_finalizer/      ← Scan future data for TP/SL hit
  └── one_day_output/       ← Flatten result to DB row
        │
        ▼
database_handling/          ← PostgreSQL interface
  ├── database_interface.py ← TradingDatabase facade (use this)
  ├── database_manager/     ← Connection management
  ├── table_manager/        ← Schema creation, indices
  ├── data_operations/      ← CRUD operations
  ├── query_builder/        ← Pre-built analytics queries
  └── database_cleaner/     ← TRUNCATE + VACUUM
```

---

## Requirements

- Python 3.10+
- PostgreSQL 13+

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Dependencies: `pandas`, `numpy`, `psycopg2-binary`, `python-dotenv`, `requests`

---

## Setup

### 1. Configure the database

Copy the example env file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_DB=forex_analysis
```

Create the database in PostgreSQL:

```sql
CREATE DATABASE forex_analysis;
```

### 2. Add input data

Place OHLC data files in `input_data/`. Expected format — one file per pair+timeframe, no header, comma-separated:

```
20010102,000000,0.56170,0.56220,0.56140,0.56220,0.56190
```

Columns: `date (YYYYMMDD), time (HHMMSS), open, high, low, close, weighted_avg`

Supported filenames: `EURUSD_1H.txt`, `EURUSD_1D.txt`, `GBPUSD_1H.txt`, etc.

### 3. Run the integration test

```bash
python smoke_test.py
```

This verifies the full pipeline end-to-end without writing large amounts of data.

---

## Running the full backtest

```bash
# Full run — every candle, all pairs in input_data/
python run_new_schema.py

# Preview only — no database writes
python run_new_schema.py --dry-run

# Single pair
python run_new_schema.py --pair EURUSD

# Single timeframe
python run_new_schema.py --tf 1D

# Subsample — every Nth candle (faster testing)
python run_new_schema.py --step 10

# Combine flags
python run_new_schema.py --pair GBPUSD --tf 1H --step 50
```

The run is resumable — rows use `ON CONFLICT DO NOTHING`, so interrupted runs can be restarted safely.

**Time estimate** at `--step 1` (every candle), ~21 rows/second:

| Dataset | Rows | Time |
|---------|------|------|
| Single pair, 1H | ~148,000 | ~2 hours |
| Single pair, 1D | ~6,200 | ~5 min |
| 6 pairs × 1H | ~890,000 | ~12 hours |
| 6 pairs × 1D | ~36,000 | ~30 min |

---

## Database schema

Tables are named `{ticker_lower}_{timeframe_lower}` (e.g. `eurusd_1h`, `gbpusd_1d`).

| Column | Type | Description |
|--------|------|-------------|
| `ticker` | VARCHAR | e.g. `EURUSD` |
| `timeframe` | VARCHAR | e.g. `1H` |
| `full_date_open` | TIMESTAMP | Candle datetime (analysis cutoff) |
| `linear_direction` | VARCHAR | `UP` / `DOWN` / `NEUTRAL` |
| `logarithmic_direction` | VARCHAR | Quadratic method output |
| `candle_direction` | VARCHAR | Candlestick pattern output |
| `long_tp / long_sl` | DOUBLE | TP/SL levels for a LONG trade |
| `short_tp / short_sl` | DOUBLE | TP/SL levels for a SHORT trade |
| `end_up_reason` | VARCHAR | How the LONG trade closed |
| `end_up_close_price` | DOUBLE | Price at LONG trade close |
| `end_up_close_date` | TIMESTAMP | When LONG trade closed |
| `end_down_reason` | VARCHAR | How the SHORT trade closed |
| `end_down_close_price` | DOUBLE | Price at SHORT trade close |
| `end_down_close_date` | TIMESTAMP | When SHORT trade closed |

**Outcome values** (`end_up_reason` / `end_down_reason`):

| Value | Meaning |
|-------|---------|
| `TAKE_PROFIT` | Price hit the TP level — trade won |
| `STOP_LOSS` | Price hit the SL level — trade lost |
| `MAX_DURATION` | 7-day deadline expired |
| `INVALID` | Levels could not be computed |
| `NO_FUTURE_DATA` | Cutoff was at end of file |

---

## Configuration

All settings live in `settings_jsons/`:

| File | Purpose |
|------|---------|
| `pipeline_config.json` | DB connection, backtesting rules, Wall Street open timing |
| `trade_maker_settings.json` | TP/SL indices, max trade duration, levels count |
| `level_finder_settings.json` | S/R detection parameters per timeframe |
| `direction_config.json` | Which direction method to use as default |

---

## Example queries

```sql
-- Win rates by direction method for EURUSD 1H LONG trades
SELECT
    linear_direction,
    COUNT(*) AS total,
    ROUND(100.0 * SUM(CASE WHEN end_up_reason = 'TAKE_PROFIT' THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN end_up_reason IN ('TAKE_PROFIT','STOP_LOSS') THEN 1 ELSE 0 END), 0), 2)
    AS win_pct
FROM eurusd_1h
WHERE end_up_reason IN ('TAKE_PROFIT', 'STOP_LOSS')
GROUP BY linear_direction;

-- Method agreement vs win rate
SELECT
    linear_direction, logarithmic_direction, candle_direction,
    COUNT(*) AS total,
    ROUND(100.0 * SUM(CASE WHEN end_up_reason = 'TAKE_PROFIT' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 1) AS long_win_pct
FROM eurusd_1h
WHERE end_up_reason IN ('TAKE_PROFIT', 'STOP_LOSS')
GROUP BY linear_direction, logarithmic_direction, candle_direction
ORDER BY total DESC;
```

See `AI_tools/statistics_and_viz_context.md` for a full analytics guide and visualization recipes.

---

## Project structure

```
.
├── run_new_schema.py          ← Main batch runner
├── smoke_test.py              ← Integration test
├── fix_datetime_format.py     ← Utility: fix datetime format in data files
├── requirements.txt
├── .env.example               ← Copy to .env and fill credentials
├── keys.json.example          ← Copy to keys.json if using LLM tools
├── settings_jsons/            ← All JSON configuration files
├── one_day_proceeding/        ← Per-candle analysis pipeline
├── proceed_datasets/          ← Batch processing orchestration
├── database_handling/         ← PostgreSQL interface layer
├── prepare_input_data/        ← Utilities for preparing input data files
└── AI_tools/                  ← Technical documentation
```

---

## Documentation

Detailed documentation for each module is in its `README.md`. Cross-cutting docs:

- `AI_tools/readme_sum_up.md` — full architecture reference
- `AI_tools/new_schema.md` — database schema design and rationale
- `AI_tools/for_user.md` — practical run guide with timing estimates
- `AI_tools/statistics_and_viz_context.md` — analytics and visualization guide
