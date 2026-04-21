# New Schema — Reference Document

> Context for AI assistants working on this project.
> Read `readme_sum_up.md` first for the full project overview.

---

## What this schema is for

The **new schema** records, for every analysed candle, what would have happened if you had opened **both** a LONG and a SHORT trade simultaneously. The three direction algorithms (linear, quadratic/logarithmic, candle) are recorded as informational signals only — they do **not** filter which trade gets evaluated.

This produces a large table per ticker+timeframe pair that can later be mined to answer questions like:
- "When linear says UP and candle says UP, how often does the LONG trade win?"
- "Is the quadratic method a better predictor than the candle method for EURUSD H1?"
- "What is the win-rate of each method as a direction filter over this dataset?"

---

## Table structure

One table per **ticker + timeframe** pair, named `{ticker_lower}_{timeframe_lower}`:

| Column | Type | Notes |
|--------|------|-------|
| `id` | SERIAL PK | auto |
| `ticker` | VARCHAR(20) | e.g. `EURUSD` |
| `timeframe` | VARCHAR(10) | e.g. `1H` |
| `full_date_open` | TIMESTAMP | candle datetime (cutoff point) |
| `linear_direction` | VARCHAR(10) | `UP` / `DOWN` / `NEUTRAL` |
| `logarithmic_direction` | VARCHAR(10) | quadratic method output |
| `candle_direction` | VARCHAR(10) | candlestick pattern output |
| `long_tp` | DOUBLE PRECISION | level above price (TP for LONG) |
| `long_sl` | DOUBLE PRECISION | level below price (SL for LONG) |
| `short_tp` | DOUBLE PRECISION | level below price (TP for SHORT) |
| `short_sl` | DOUBLE PRECISION | level above price (SL for SHORT) |
| `end_up_reason` | VARCHAR(20) | `TAKE_PROFIT` / `STOP_LOSS` / `MAX_DURATION` / `OPEN` / `INVALID` / `NO_FUTURE_DATA` |
| `end_up_close_price` | DOUBLE PRECISION | price at which the LONG trade closed |
| `end_up_close_date` | TIMESTAMP | when the LONG trade closed |
| `end_down_reason` | VARCHAR(20) | same set of values, for the SHORT trade |
| `end_down_close_price` | DOUBLE PRECISION | |
| `end_down_close_date` | TIMESTAMP | |
| `created_at` | TIMESTAMP | row generation time |

**Unique constraint:** `(ticker, timeframe, full_date_open)` — re-running the batch is safe (ON CONFLICT DO NOTHING).

**Indices:** `full_date_open`, all three direction columns, `end_up_reason`, `end_down_reason`.

---

## Tables produced

12 tables total from `input_data/*_1H.txt` and `*_1D.txt`:

```
audusd_1h    audusd_1d
eurchf_1h    eurchf_1d
eurusd_1h    eurusd_1d
gbpusd_1h    gbpusd_1d
usdjpy_1h    usdjpy_1d
xauusd_1h    xauusd_1d
```

---

## How to run

```bash
# Full run — every candle, all pairs
python run_new_schema.py

# Preview first 3 rows without touching DB
python run_new_schema.py --dry-run

# Only EURUSD, only 1H
python run_new_schema.py --pair EURUSD --tf 1H

# Every 10th candle (faster, useful for testing)
python run_new_schema.py --step 10

# Combine flags
python run_new_schema.py --pair EURUSD --step 5 --dry-run
```

---

## Code changes made (2026-04-05)

All additions are **additive only** — no existing logic was modified.

### `one_day_proceeding/trade_finalizer/trade_finalizer.py`
Added `finalize_both()` method:
- Always runs `_check_long_trade()` AND `_check_short_trade()` regardless of the `direction` field
- Returns `{"long": {...}, "short": {...}}`
- Handles `NO_FUTURE_DATA` and `error` gracefully

### `one_day_proceeding/one_day_proceeding.py`
Added `run_new_schema()` method:
- Calls `_find_levels()` once (direction-independent)
- Runs all 3 `DirectionGuesser` methods to get direction signals
- Calls `tradeMaker(direction="UP")` — always UP to ensure all 4 TP/SL values (long_tp, long_sl, short_tp, short_sl) are geometrically correct
- Calls `TradeFinalizer.finalize_both()` for both outcomes
- Returns flat dict ready for `OneDayOutput.to_new_schema_row()`

### `one_day_proceeding/one_day_output/one_day_output.py`
Added `to_new_schema_row(result, ticker, timeframe)` classmethod:
- Flattens `run_new_schema()` output into a DB-ready dict
- Returns `None` if the result contains an `"error"` key

### `database_handling/table_manager/table_manager.py`
Added three new functions:
- `create_new_schema_table(conn, table_name)` — creates the table + indices
- `_create_new_schema_indices(conn, table_name)` — internal, called by above
- `insert_new_schema_row(conn, table_name, row)` — single-row insert with conflict skip

### `database_handling/table_manager/__init__.py`
Exported `create_new_schema_table` and `insert_new_schema_row`.

### `run_new_schema.py` (new file, project root)
Standalone batch runner. See "How to run" above.

---

## Key design decisions

### Why tradeMaker is always called with direction="UP"
`tradeMaker` has a bug in the `direction="DOWN"` branch: it assigns `short_tp` to `level[+3]`
(above price) and `short_sl` to `level[-3]` (below price), which is geometrically wrong for a
short trade. The `direction="UP"` branch correctly sets all 4 values:
- `long_tp  = level[+tp_index]`  ✓ above price
- `long_sl  = level[sl_index]`   ✓ below price (negative index)
- `short_tp = level[-tp_index]`  ✓ below price (mirrored)
- `short_sl = level[+|sl_index|]`✓ above price (mirrored)

The direction field is only stored for analysis; it does not influence TP/SL values.

### Why one table per ticker+timeframe (not one big table)
Consistent with the existing `database_handling` design. Smaller tables = faster queries.
Also makes it trivial to add/remove a pair without touching others.

### Why step=1 (every candle)
The aim is maximum data for statistical analysis. With 7-day `max_duration` from JSON settings,
there is meaningful overlap between adjacent rows, but that is intentional — every candle is
a valid trade entry point.

### `end_*_reason` values
Sourced from `TradeFinalizer._scan_future_data()`:
- `TAKE_PROFIT` — TP level hit
- `STOP_LOSS` — SL level hit (or same-bar hit as TP → conservative SL)
- `MAX_DURATION` — trade ran out of time (7 days default from `trade_maker_settings.json`)
- `OPEN` — neither hit within future data (no max_duration set)
- `INVALID` — missing TP/SL or trade error
- `NO_FUTURE_DATA` — cutoff was at the very end of the dataset

---

## Settings that affect this schema

| Setting | File | Effect |
|---------|------|--------|
| `trade_maker.tp_level_index` | `trade_maker_settings.json` | Which level above price becomes TP |
| `trade_maker.sl_level_index` | `trade_maker_settings.json` | Which level below price becomes SL |
| `trade_maker.max_duration`   | `trade_maker_settings.json` | How long trades run before `MAX_DURATION` |
| `levels_handler.levels_count`| `trade_maker_settings.json` | Levels per side of price |
| `H1` / `D1` sections         | `level_finder_settings.json` | S/R detection parameters |

---

## Querying the data

```sql
-- Win rates by direction method for EURUSD 1H LONG trades
SELECT
    linear_direction,
    COUNT(*)                                                       AS total,
    SUM(CASE WHEN end_up_reason = 'TAKE_PROFIT' THEN 1 ELSE 0 END) AS wins,
    ROUND(
        100.0 * SUM(CASE WHEN end_up_reason = 'TAKE_PROFIT' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0), 2
    )                                                              AS win_pct
FROM eurusd_1h
WHERE end_up_reason IN ('TAKE_PROFIT', 'STOP_LOSS')
GROUP BY linear_direction
ORDER BY linear_direction;

-- Compare UP vs DOWN agreement between methods
SELECT
    linear_direction,
    logarithmic_direction,
    candle_direction,
    COUNT(*) AS occurrences,
    ROUND(100.0 * SUM(CASE WHEN end_up_reason = 'TAKE_PROFIT' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 1) AS long_win_pct,
    ROUND(100.0 * SUM(CASE WHEN end_down_reason = 'TAKE_PROFIT' THEN 1 ELSE 0 END)
          / NULLIF(COUNT(*), 0), 1) AS short_win_pct
FROM eurusd_1h
WHERE end_up_reason   IN ('TAKE_PROFIT', 'STOP_LOSS')
  AND end_down_reason IN ('TAKE_PROFIT', 'STOP_LOSS')
GROUP BY linear_direction, logarithmic_direction, candle_direction
ORDER BY occurrences DESC;
```
