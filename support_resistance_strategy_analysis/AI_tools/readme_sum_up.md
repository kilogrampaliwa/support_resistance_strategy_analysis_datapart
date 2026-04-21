# sr_analysis — AI Context Document

> **Purpose:** This file is the primary context brief for any AI assistant (Claude Code, ChatGPT, Gemini, etc.) working on this project.
> Read this before touching any code. It is maintained manually — update it when the architecture changes.

---

## Project Identity

**Name:** `support_resistance_strategy_analysis`
**Type:** Bachelor's thesis (praca licencjacka) — Python backtesting system
**Domain:** Forex trading — support/resistance level detection and strategy evaluation
**Base path:** project root

---

## What the System Does

This is a **backtesting pipeline** for a support/resistance trading strategy. Given historical OHLC forex data:

1. It scans backwards from a chosen **cutoff point** to detect S/R price levels.
2. It detects the current **trend direction** (UP / DOWN / NEUTRAL).
3. It generates a **trade signal** (TP and SL targets) based on the nearest levels.
4. It scans **forward** from the cutoff to validate whether the trade would have hit TP or SL.
5. The result is stored in **PostgreSQL** for statistical analysis.

Running this across thousands of cutoff points in a dataset constitutes a **full backtest**.

---

## Architecture Overview

```
input_data/               ← Raw OHLC .csv / .txt files (forex pairs)
        │
        ▼
proceed_datasets/           ← Top-level batch orchestration
  ├── dataset_processor.py  ← Entry point: scan files, detect timeframes, dispatch
  ├── data_loader/          ← Load .csv/.txt with auto-detect (sep, headers, datetime)
  ├── timeframe_detector/   ← Detect H1/D1/M5/etc. from data or filename
  ├── batch_processor/      ← Iterate a DataFrame, call one_day_proceeding per step
  └── progress_tracker/     ← Progress %, ETA, success/fail counts
        │
        ▼
one_day_proceeding/         ← Per-cutoff analysis core
  ├── one_day_proceeding.py ← Main orchestrator (OneDayProceeding class)
  ├── levels_finder/        ← Pivot + frequency-based S/R detection (LevelsFinder)
  ├── levels_handler/       ← Multi-window aggregation, dedup, enforce N levels/side (LevelHandler)
  ├── direction_guesser/    ← Trend direction: linear / quadratic / candle (DirectionGuesser)
  ├── trade_maker/          ← TP/SL assignment from levels (tradeMaker function)
  ├── trade_finalizer/      ← Scan future data for TP/SL hit (TradeFinalizer)
  └── one_day_output/       ← Flatten result to DB row (OneDayOutput)
        │
        ▼
database_handling/          ← PostgreSQL interface layer
  ├── database_interface.py ← TradingDatabase — combined facade (entry point)
  ├── database_manager/     ← Connection, table creation, per pair+timeframe tables
  ├── data_operations/      ← CRUD: insert, query, delete, update
  ├── query_builder/        ← Pre-built analytics queries, custom SQL
  ├── table_manager/        ← Config-derived table naming (e.g. trades_d1h1_l5_tp2_sl1_lin)
  └── database_cleaner/     ← TRUNCATE + VACUUM + verify empty
```

---

## Current API State (as of 2026-04-05)

### `OneDayProceeding` — KEY EVOLUTION
The class supports **two operating modes**:

**Single method (original):**
```python
processor = OneDayProceeding(df, cutoff_datetime, timeframe="H1", direction_method="linear",
    level_finder_settings_path="settings_jsons/level_finder_settings.json",
    trade_maker_settings_path="settings_jsons/trade_maker_settings.json")
trade_data  = processor.run_analysis()
future_data = processor.get_future_data()
```

**All methods at once (current default in smoke_test.py):**
```python
processor = OneDayProceeding(df, cutoff_datetime, timeframe="H1",
    level_finder_settings_path=..., trade_maker_settings_path=...)
results = processor.run_all_methods()
# returns dict: {"linear": finalized_dict, "quadratic": finalized_dict, "candle": finalized_dict}
# max_duration_seconds is read internally from trade_maker_settings.json
```

### `OneDayOutput.from_all_methods()` — NEW classmethod
Flattens all 3 method results into a **single combined DB row**:
```python
row = OneDayOutput.from_all_methods(results)
# row keys prefixed: lin_*, quad_*, cnd_*
# e.g. lin_tp_long, quad_outcome, cnd_direction, max_duration_seconds
```

### `TradeFinalizer` — max_duration_seconds
```python
TradeFinalizer(trade_data, future_df, max_duration_seconds=None)
# max_duration_seconds caps how far into future the scan goes
# read from trade_maker_settings.json under trade_maker.max_duration: {value, unit}
```

---

## Settings Files (all in `settings_jsons/`)

| File | Purpose |
|------|---------|
| `level_finder_settings.json` | LevelsFinder params per timeframe (back_window_size, pivot_window, freq bins, merge_margin) |
| `trade_maker_settings.json` | TP/SL indices, fallback strategy, padding pct, levels_count, max_duration |
| `direction_config.json` | Which direction method to use: `{"direction": {"method": "quadratic"}}` |
| `pipeline_config.json` | Full pipeline config: DB params, backtesting rules, Wall Street open timing, etc. |

---

## Database

- **Engine:** PostgreSQL (psycopg2)
- **Default:** host=localhost, port=5432, db=`forex_analysis` — credentials from `.env` (see `.env.example`)
- **Table naming convention:** `{symbol}_{timeframe}` for simple per-pair tables (e.g. `eurusd_h1`), OR config-derived names like `trades_d1h1_l5_tp2_sl1_lin` when using `TableManager`.
- **Env vars:** `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- **Smoke test table:** `{symbol}_{timeframe}_test` (e.g. `eurusd_h1_test`)

---

## Data Format

Input files: CSV/TXT, **no header**, format per row:
```
20010102,000000,0.56170,0.56220,0.56140,0.56220,0.56190
date,    hour,  open,   high,   low,    close,  w_avre
```

- `w_avre` = weighted average price (used by linear/quadratic direction methods)
- `date` format: `YYYYMMDD`
- `hour` format: `HHMMSS` (zero-padded to 6 digits)

---

## Direction Methods

| Method | Input | Logic |
|--------|-------|-------|
| `linear` | `w_avre` last 20 bars | Slope of fitted line vs threshold |
| `quadratic` | `w_avre` last 20 bars | Derivative of fitted parabola at last point |
| `candle` | OHLC last 10 bars | Cumulative score of recognized candlestick patterns |

All return: `"UP"`, `"DOWN"`, or `"NEUTRAL"`.

---

## Trade Logic Summary

1. **Levels** are detected via pivot highs/lows + price frequency histograms, across multiple lookback windows (50, 100, 200, all).
2. Current price is the last `close` in historical window.
3. **TP** = level at index `+tp_level_index` above price (with inward padding).
4. **SL** = level at index `sl_level_index` below price (negative index, with inward padding).
5. **Validation**: scan future bars — LONG: `high >= tp` → TAKE_PROFIT, `low <= sl` → STOP_LOSS. SHORT: mirrored.
6. Same-bar TP+SL hit → conservatively STOP_LOSS.
7. Outcomes: `TAKE_PROFIT` | `STOP_LOSS` | `OPEN` | `INVALID` | `NO_FUTURE_DATA`

---

## Key Files to Know

| File | What it is |
|------|-----------|
| `smoke_test.py` | Integration test for full pipeline — start here to verify things work |
| `one_day_proceeding/one_day_proceeding.py` | Core orchestrator — read this to understand the main flow |
| `settings_jsons/pipeline_config.json` | Master config (DB, backtesting rules, timing) |
| `settings_jsons/trade_maker_settings.json` | Trade params including max_duration |
| `database_handling/database_interface.py` | TradingDatabase facade — use this for all DB operations |
| `proceed_datasets/dataset_processor.py` | Top-level batch processor entry point |

---

## Project Status Notes (as of 2026-04-05)

- **READMEs vs code divergence:** Module READMEs describe v1.0 single-method architecture. The code has evolved to multi-method (`run_all_methods` + `from_all_methods`). READMEs have NOT been updated yet.
- **`proceed_datasets/` `__init__` files** exist but the top-level `dataset_processor.py` is not visible in the module (only `__init__.py` files shown) — needs verification.

---

## How to Work on This Project

### Before making any change:
1. Read the relevant module source file — do not rely solely on README (they lag behind).
2. Understand which settings JSON the module reads and from what path.
3. Check `smoke_test.py` — it's the integration test and shows the expected API.

### When modifying the pipeline:
- The main flow is: `OneDayProceeding.run_all_methods()` → `OneDayOutput.from_all_methods()` → `DataOperations.insert_trade()`
- DB row schema must match the table created by `TableManager.create_table_if_not_exists()`.
- Adding a new field to the DB row requires updating both `OneDayOutput` and the `CREATE TABLE` statement.

### When adding a new direction method:
- Add to `DirectionGuesser` with a new strategy class under `direction_guesser/`.
- Update `OneDayProceeding.run_all_methods()` to include the new method name.
- Update `OneDayOutput.from_all_methods()` to include the new method's prefix.
- Add a new prefix column set to the DB table schema.

### When changing settings JSON structure:
- Check all callers: `LevelHandler`, `TradeMaker`, `OneDayProceeding._read_max_duration_seconds()`, `TableManager.generate_table_name_from_config()`.

---

## Dependencies

```
pandas
numpy
psycopg2
requests    (for LLM API calls in AI_TEMP_WORK_FOLDER)
```

See `requirements.txt` in project root for the full list.
