# Context for Statistics & Data Representation Session

> This document is written for an AI assistant starting fresh in a new chat.
> It contains everything needed to build statistical analysis and visualization tools
> on top of the trading database built in the previous session.
> Read this fully before writing any code.

---

## Project in one paragraph

This is a forex trading backtesting system (bachelor's thesis). It detects support/resistance
levels from OHLC candle data, then simulates opening BOTH a long and a short trade at every
candle. All trades close either at a TP level, a SL level, or after a 7-day deadline. The
result is a PostgreSQL database with one table per currency pair + timeframe combination,
each holding tens of thousands of rows — one per analysed candle. The goal of the statistics
session is to analyse which combination of direction signals (linear, logarithmic, candle)
predicts correctly, and how profitable each strategy variation would have been.

---

## Database connection

**Engine:** PostgreSQL (psycopg2)

```python
import psycopg2

import os
conn = psycopg2.connect(
    host     = os.getenv("POSTGRES_HOST", "localhost"),
    port     = int(os.getenv("POSTGRES_PORT", 5432)),
    database = os.getenv("POSTGRES_DB", "forex_analysis"),
    user     = os.getenv("POSTGRES_USER", "postgres"),
    password = os.getenv("POSTGRES_PASSWORD")
)
```

Or with pandas:
```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine(os.getenv("DATABASE_URL", "postgresql://postgres:your_password@localhost:5432/forex_analysis"))
df = pd.read_sql("SELECT * FROM eurusd_1h LIMIT 10", engine)
```

---

## Tables in the database

One table per ticker + timeframe. Naming: `{ticker_lower}_{timeframe_lower}`.

| Table | Pair | Timeframe | Expected rows (step=1) |
|-------|------|-----------|------------------------|
| `eurusd_1h` | EURUSD | 1H | ~148,500 |
| `eurusd_1d` | EURUSD | 1D | ~6,200 |
| `gbpusd_1h` | GBPUSD | 1H | ~148,500 |
| `gbpusd_1d` | GBPUSD | 1D | ~6,200 |
| `audusd_1h` | AUDUSD | 1H | ~148,500 |
| `audusd_1d` | AUDUSD | 1D | ~6,200 |
| `eurchf_1h` | EURCHF | 1H | ~148,500 |
| `eurchf_1d` | EURCHF | 1D | ~6,200 |
| `usdjpy_1h` | USDJPY | 1H | ~148,500 |
| `usdjpy_1d` | USDJPY | 1D | ~6,200 |
| `xauusd_1h` | XAUUSD | 1H | ~148,500 |
| `xauusd_1d` | XAUUSD | 1D | ~6,200 |

**Check what is currently populated:**
```sql
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

---

## Full table schema (every column explained)

```sql
-- Example: eurusd_1h
id                     SERIAL PRIMARY KEY       -- auto-increment, ignore in analysis
ticker                 VARCHAR(20)              -- always "EURUSD" in this table
timeframe              VARCHAR(10)              -- always "1H" in this table
full_date_open         TIMESTAMP                -- the candle datetime used as analysis cutoff

-- Direction signals — three independent algorithms, output: UP / DOWN / NEUTRAL
linear_direction       VARCHAR(10)              -- linear regression slope of last 20 bars
logarithmic_direction  VARCHAR(10)              -- quadratic regression derivative at last bar
candle_direction       VARCHAR(10)              -- candlestick pattern score (last 10 bars)

-- TP/SL levels (computed from support/resistance levels, SAME for all 3 methods)
long_tp                DOUBLE PRECISION         -- level above price → TP for LONG trade
long_sl                DOUBLE PRECISION         -- level below price → SL for LONG trade
short_tp               DOUBLE PRECISION         -- level below price → TP for SHORT trade
short_sl               DOUBLE PRECISION         -- level above price → SL for SHORT trade

-- Note: long_sl == short_tp  and  long_tp == short_sl  (they are mirror levels)
-- TP index used: 3 (3rd level above/below price)
-- SL index used: 3 (symmetric)

-- LONG trade outcome (UP direction)
end_up_reason          VARCHAR(20)              -- how the LONG trade ended (see below)
end_up_close_price     DOUBLE PRECISION         -- price at close (TP/SL level or last bar)
end_up_close_date      TIMESTAMP                -- when the trade closed

-- SHORT trade outcome (DOWN direction)
end_down_reason        VARCHAR(20)              -- how the SHORT trade ended
end_down_close_price   DOUBLE PRECISION         -- price at close
end_down_close_date    TIMESTAMP                -- when the trade closed

created_at             TIMESTAMP                -- row generation timestamp, ignore in analysis
```

---

## Outcome values (`end_up_reason` / `end_down_reason`)

| Value | Meaning | Win? |
|-------|---------|------|
| `TAKE_PROFIT` | Price reached the TP level | YES |
| `STOP_LOSS` | Price reached the SL level | NO |
| `MAX_DURATION` | 7-day deadline expired, closed at last bar | NEUTRAL (neither) |
| `OPEN` | No deadline, trade still open (should not appear — deadline IS set) | N/A |
| `INVALID` | Levels could not be computed (too few bars, data issue) | SKIP |
| `NO_FUTURE_DATA` | Cutoff was at end of file | SKIP |

**For win-rate analysis, filter to only `TAKE_PROFIT` and `STOP_LOSS` rows.**
`MAX_DURATION` rows are valid but represent inconclusive trades — handle separately.

---

## Direction methods explained (for context in charts/labels)

| Column | Internal name | Algorithm |
|--------|--------------|-----------|
| `linear_direction` | linear | Linear regression slope over last 20 bars of `w_avre` (weighted average price). Positive slope → UP. |
| `logarithmic_direction` | quadratic | Quadratic (parabolic) regression over last 20 bars of `w_avre`. Uses derivative at the last point. Called "logarithmic" in the user-facing schema (historical naming choice). |
| `candle_direction` | candle | Scores the last 10 candles based on recognised patterns: Hammer, Engulfing, Morning Star, etc. Score > 1 → UP, < -1 → DOWN. |

All three output: `UP`, `DOWN`, or `NEUTRAL`.

---

## Trade setup parameters (for reference in charts)

These settings were active during data generation. They affect what the TP/SL levels mean.

```
tp_level_index : 3        ← 3rd S/R level above price used as TP
sl_level_index : -3       ← 3rd S/R level below price used as SL (symmetric)
max_duration   : 7 days   ← trades that don't close in 7 days → MAX_DURATION
levels_count   : 5        ← max 5 S/R levels per side of price
```

The TP/SL ratio is roughly symmetric (same index distance above and below). In other words,
the expected R:R ratio is approximately 1:1, making win-rate the primary metric.

---

## Key analytical questions to answer

These are the research goals. The statistics tools should be able to answer all of them.

### 1. Per-method direction accuracy (core question)
> "When linear says UP, does the LONG trade win more than 50% of the time?"

For each direction method × direction value × ticker × timeframe:
- Win rate of LONG when method says UP
- Win rate of SHORT when method says DOWN
- What happens when method says NEUTRAL?

### 2. Method agreement vs. disagreement
> "When all 3 methods agree on UP, is the win rate higher than when they disagree?"

Combinations: 3 methods × 3 values = 27 combinations. Most common are full agreement (UUU, DDD) and partial agreement (UUD, DDN, etc.).

### 3. Cross-pair comparison
> "Does the linear method work better on EURUSD than on XAUUSD?"

Same stats, grouped by ticker instead of method.

### 4. 1H vs 1D comparison
> "Is direction prediction more accurate on daily candles than hourly?"

Same stats, grouped by timeframe.

### 5. MAX_DURATION analysis
> "How often do trades expire without hitting TP or SL?"

High MAX_DURATION rate = price is ranging inside levels. Interesting segmented by direction.

### 6. Temporal patterns
> "Has the strategy become more or less effective over the years?"

Group by year or quarter, plot win rate over time.

### 7. Pair of methods as filter
> "Use linear as primary signal, use candle as confirmation — does adding candle confirmation improve linear's win rate?"

---

## Suggested statistics to compute

```python
# For any given table and method column:

# 1. Basic win rate by direction signal
SELECT
    {method_col},
    COUNT(*) AS total,
    SUM(CASE WHEN {outcome_col} = 'TAKE_PROFIT' THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN {outcome_col} = 'STOP_LOSS'   THEN 1 ELSE 0 END) AS losses,
    SUM(CASE WHEN {outcome_col} = 'MAX_DURATION' THEN 1 ELSE 0 END) AS timeouts,
    ROUND(100.0 * wins / NULLIF(wins + losses, 0), 2) AS win_rate_pct
FROM {table}
WHERE {outcome_col} IN ('TAKE_PROFIT', 'STOP_LOSS', 'MAX_DURATION')
GROUP BY {method_col}
ORDER BY {method_col};

# 2. All 3 methods combined (27 combinations)
SELECT
    linear_direction, logarithmic_direction, candle_direction,
    COUNT(*) AS total,
    ROUND(100.0 * SUM(CASE WHEN end_up_reason = 'TAKE_PROFIT' THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN end_up_reason IN ('TAKE_PROFIT','STOP_LOSS') THEN 1 ELSE 0 END), 0), 1)
    AS long_win_pct,
    ROUND(100.0 * SUM(CASE WHEN end_down_reason = 'TAKE_PROFIT' THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN end_down_reason IN ('TAKE_PROFIT','STOP_LOSS') THEN 1 ELSE 0 END), 0), 1)
    AS short_win_pct
FROM eurusd_1h
GROUP BY linear_direction, logarithmic_direction, candle_direction
ORDER BY total DESC;

# 3. Year-over-year win rate
SELECT
    EXTRACT(YEAR FROM full_date_open) AS year,
    COUNT(*) AS total,
    ROUND(100.0 * SUM(CASE WHEN end_up_reason = 'TAKE_PROFIT' THEN 1 ELSE 0 END)
          / NULLIF(SUM(CASE WHEN end_up_reason IN ('TAKE_PROFIT','STOP_LOSS') THEN 1 ELSE 0 END), 0), 1)
    AS long_win_pct
FROM eurusd_1h
GROUP BY year ORDER BY year;
```

---

## Suggested visualisations

| Chart | Type | X axis | Y axis | Grouped by |
|-------|------|--------|--------|------------|
| Win rate by direction method | Grouped bar | Method (lin/log/cnd) | Win % | UP / DOWN / NEUTRAL |
| Method agreement heatmap | Heatmap | linear_direction | logarithmic_direction | Color = win rate |
| Win rate over time | Line chart | Year / Quarter | Win % | Per method |
| Outcome distribution | Stacked bar | Ticker | Count | TP / SL / MAX_DURATION / INVALID |
| Cross-pair win rate | Heatmap | Ticker | Timeframe | Color = win rate |
| Agreement vs win rate | Scatter / bar | # methods agreeing (0-3) | Win % | LONG / SHORT |
| Direction frequency | Bar | Direction combo | Count | — |

---

## Recommended Python libraries

```python
import psycopg2          # DB connection
import pandas as pd      # data manipulation
import matplotlib.pyplot as plt  # base charts
import seaborn as sns    # heatmaps, styled charts
import plotly.express as px      # interactive charts (optional)
from sqlalchemy import create_engine  # for pd.read_sql
```

---

## Data loading pattern (use this as base)

```python
import pandas as pd
from sqlalchemy import create_engine

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:your_password@localhost:5432/forex_analysis")
engine = create_engine(DB_URL)

def load_table(table_name: str) -> pd.DataFrame:
    """Load full table into DataFrame."""
    return pd.read_sql(f"SELECT * FROM {table_name}", engine,
                       parse_dates=["full_date_open", "end_up_close_date",
                                    "end_down_close_date", "created_at"])

def load_filtered(table_name: str, outcomes_only: bool = True) -> pd.DataFrame:
    """Load only rows with decisive outcomes (TP or SL), skip INVALID/NO_FUTURE_DATA."""
    where = ""
    if outcomes_only:
        where = "WHERE end_up_reason IN ('TAKE_PROFIT','STOP_LOSS','MAX_DURATION')"
    return pd.read_sql(f"SELECT * FROM {table_name} {where}", engine,
                       parse_dates=["full_date_open", "end_up_close_date",
                                    "end_down_close_date"])

# Helper: add boolean win columns
def add_win_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["long_win"]  = df["end_up_reason"]   == "TAKE_PROFIT"
    df["short_win"] = df["end_down_reason"]  == "TAKE_PROFIT"
    df["long_decisive"]  = df["end_up_reason"].isin(["TAKE_PROFIT", "STOP_LOSS"])
    df["short_decisive"] = df["end_down_reason"].isin(["TAKE_PROFIT", "STOP_LOSS"])
    return df

# Usage
df = load_filtered("eurusd_1h")
df = add_win_columns(df)
print(df["linear_direction"].value_counts())
print(df.groupby("linear_direction")["long_win"].mean())
```

---

## Important caveats for analysis

### Overlapping trades
With step=1 (every candle), adjacent rows represent overlapping trades. Row at 10:00 and row
at 11:00 share most of their future data window. This means rows are **not statistically
independent**. For pure statistical tests, subsample or use step >= max_duration in bars
(7 days × 24 hours = 168 bars for 1H). For trend analysis over time this overlap is fine.

### NEUTRAL is valid data
`NEUTRAL` direction means no clear signal. It's worth including in analysis — if NEUTRAL rows
have a 50/50 outcome, that confirms the model is not misleading when unsure.

### MAX_DURATION is not a loss
Trades that hit MAX_DURATION closed at the last bar's price. This could be slightly profitable
or slightly losing depending on price movement. Currently the table does NOT store the open
price, so you cannot compute exact P/L for these rows. They should be treated as a separate
category, not merged into wins or losses.

### open_price is missing
The entry price at the cutoff candle is **not stored** in the current schema. This was an
oversight. P/L percentage cannot be computed from the table alone. TP/SL prices are available
and can be used as proxies for the range, but exact P/L requires the open price.
If needed, it can be added by re-running the batch (backwards compatible — ON CONFLICT DO NOTHING).

### Data range
Files cover approximately 2001–2025. Some pairs may have different date ranges.
Always check with:
```sql
SELECT MIN(full_date_open), MAX(full_date_open), COUNT(*) FROM eurusd_1h;
```

---

## File locations (for reference)

```
project_root/
├── run_new_schema.py                 ← batch runner that populated the DB
├── settings_jsons/
│   ├── trade_maker_settings.json     ← tp/sl indices, max_duration
│   ├── level_finder_settings.json    ← S/R detection params per timeframe
│   └── pipeline_config.json          ← DB config (uses env vars)
├── AI_tools/
│   ├── readme_sum_up.md              ← full project overview
│   ├── new_schema.md                 ← technical details of this schema
│   ├── for_user.md                   ← user-facing run instructions
│   └── statistics_and_viz_context.md ← THIS FILE
├── one_day_proceeding/               ← core analysis pipeline (don't touch)
└── database_handling/                ← DB interface layer (don't touch)
```

---

## What NOT to touch

The analysis pipeline is complete and verified. Do not modify:
- Anything inside `one_day_proceeding/`
- Anything inside `database_handling/`
- `run_new_schema.py`

Build new standalone scripts or a new module (e.g. `analytics/`) on top of the database.

---

## Suggested first steps in the new session

1. Connect to DB and verify which tables exist and how many rows each has.
2. Load `eurusd_1h`, compute basic win rates per direction method.
3. Build a function `win_rate_by_direction(table, method_col, outcome_col)` that works for any table + method combination.
4. Build a function `compare_all_tables(tables, method)` for cross-pair/timeframe comparison.
5. Plot a heatmap of win rates across all method × direction combinations.
6. Add temporal analysis (win rate by year).
7. Package everything into a report generator.
