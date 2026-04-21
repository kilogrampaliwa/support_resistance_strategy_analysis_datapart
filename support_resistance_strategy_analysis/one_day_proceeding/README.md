# one_day_proceeding

A trading analysis pipeline that scans historical OHLC data up to a chosen cutoff point, detects support/resistance levels, predicts direction, and generates a trade signal — then validates it against what actually happened next.

---

## How it works — the big picture

You give it a full price dataset and a **cutoff point** (a datetime index). The system splits your data right there:

- Everything **up to** the cutoff → used to *build* the trade signal
- Everything **after** the cutoff → used to *validate* whether the trade won or lost

```
Your full OHLC dataset
        │
        ├──────────────────────┬──────────────────────
        │                      │
   [HISTORICAL]            [FUTURE]
   up to cutoff            after cutoff
        │                      │
  ┌─────▼──────────┐           │
  │  LevelsFinder  │           │
  │  LevelHandler  │           │
  └─────┬──────────┘           │
        │                      │
  ┌─────▼──────────┐           │
  │ DirectionGuesser│          │
  └─────┬──────────┘           │
        │                      │
  ┌─────▼──────────┐           │
  │   TradeMaker   │           │
  └─────┬──────────┘           │
        │                      │
        └──────────┬───────────┘
                   │
            ┌──────▼──────────┐
            │  TradeFinalizer │   Did price hit TP or SL?
            └──────┬──────────┘
                   │
            ┌──────▼──────────┐
            │  OneDayOutput   │   Format for DB / CSV / SQL
            └─────────────────┘
```

---

## Quickstart

### 1. Prepare your data

```python
import pandas as pd

# CSV format (no header): date, hour, open, high, low, close, w_avre
# Example row: 20010102,000000,0.56170,0.56220,0.56140,0.56220,0.56190

df = pd.read_csv(
    'data.csv',
    names=['date', 'hour', 'open', 'high', 'low', 'close', 'w_avre']
)

# Build datetime index (required)
df['datetime'] = pd.to_datetime(
    df['date'].astype(str) + df['hour'].astype(str).str.zfill(6),
    format='%Y%m%d%H%M%S'
)
df.set_index('datetime', inplace=True)
```

### 2. Run a single analysis

```python
from one_day_proceeding.one_day_proceeding import OneDayProceeding
from one_day_proceeding.trade_finalizer.trade_finalizer import TradeFinalizer
from one_day_proceeding.one_day_output.one_day_output import OneDayOutput

cutoff = df.index[500]  # analyze first 500 bars, validate on the rest

processor = OneDayProceeding(
    df=df,
    cutoff_datetime=cutoff,
    timeframe="H1",           # "H1" or "D1"
    direction_method="linear" # "linear", "quadratic", or "candle"
)

trade_data  = processor.run_analysis()
future_data = processor.get_future_data()

finalized = TradeFinalizer(trade_data, future_data).finalize()
row       = OneDayOutput(finalized).to_row()

print(row['direction'], row['outcome'], row['profit_loss_pct'])
```

### 3. Batch backtest

```python
results = []

for i in range(200, len(df) - 100, 100):
    cutoff = df.index[i]

    processor   = OneDayProceeding(df, cutoff, timeframe="H1")
    trade_data  = processor.run_analysis()
    future_data = processor.get_future_data()

    finalized = TradeFinalizer(trade_data, future_data).finalize()
    results.append(OneDayOutput(finalized).to_row())

df_results = pd.DataFrame(results)
print(f"Win rate : {df_results['win'].mean()*100:.1f}%")
print(f"Avg P/L  : {df_results['profit_loss_pct'].mean():.2f}%")
```

---

## Module logic

### LevelsFinder + LevelHandler — level detection

`LevelsFinder` scans the historical window for price zones that acted as support or resistance. It uses two complementary approaches:

- **Pivot-based** — finds pivot highs and lows (local extremes), bins them, and keeps zones that appear frequently
- **Price-frequency** — histograms all OHLC prices and keeps high-density zones

`LevelHandler` wraps `LevelsFinder`, running it across multiple lookback windows (50, 100, 200, all data), merging nearby levels, and enforcing a minimum level count. If too few levels are found, it mirrors existing ones symmetrically around the current price.

Together they produce a short, clean, non-redundant list of price zones.

**Key settings (`level_finder_settings.json`):**

```json
{
  "H1": {
    "back_window_size": 200,   // bars to look back
    "pivot_window": 5,         // half-window for pivot detection
    "strong_freq_bin": 0.001,  // bin width for pivot frequency
    "strong_freq_threshold": 2,
    "simple_freq_bin": 0.002,  // bin width for price frequency
    "simple_freq_threshold": 3,
    "merge_margin": 0.005      // merge levels closer than this %
  }
}
```

---

### DirectionGuesser — trend direction

Predicts whether price is trending **UP**, **DOWN**, or **NEUTRAL** at the cutoff point. Three methods:

| Method | How it works |
|---|---|
| `linear` | Linear regression slope over last N bars of `w_avre` |
| `quadratic` | Polynomial regression — catches curves, not just straight lines |
| `candle` | Pattern recognition (Doji, Engulfing, Hammer, Morning Star, etc.) |

`lookback=20` means it only examines the last 20 bars — keeps the signal local and recent.

---

### TradeMaker — trade signal

Takes the current price, the filtered levels, and the direction, then assigns:

- **TP** = the first level *above* current price (index `+1`)
- **SL** = the first level *below* current price (index `-1`)

Both long and short parameters are always generated regardless of direction — direction only determines which set is *active* for validation.

```python
{
    "open_price":  0.56190,
    "direction":   "UP",
    "long_tp":     0.57000,   # active TP when going long
    "long_sl":     0.55500,   # active SL when going long
    "short_tp":    0.55500,
    "short_sl":    0.57000,
    "all_levels":  [0.545, 0.555, 0.570, 0.580],
    "warnings":    []
}
```

Fallback multipliers kick in when there aren't enough levels on one side.

**Key settings (`trade_maker_settings.json`):**

```json
{
  "tp_level_index": 1,       // which level above price to use as TP
  "sl_level_index": -1,      // which level below price to use as SL
  "fallback_strategy": {
    "tp_multiplier": 1.5,    // fallback TP distance when no level available
    "sl_multiplier": 1.0
  }
}
```

---

### TradeFinalizer — validation

Walks forward through future bars and checks for TP/SL hits:

```
LONG trade:
  future_high >= long_tp   →  TAKE_PROFIT
  future_low  <= long_sl   →  STOP_LOSS

SHORT trade:
  future_low  <= short_tp  →  TAKE_PROFIT
  future_high >= short_sl  →  STOP_LOSS
```

If both hit in the **same bar**, it conservatively calls **STOP_LOSS**.

Possible outcomes: `TAKE_PROFIT` · `STOP_LOSS` · `OPEN` · `INVALID` · `NO_FUTURE_DATA`

---

### OneDayOutput — formatting

Formats the finalized trade into a flat record with 30+ fields ready for a database. Three output modes:

```python
output = OneDayOutput(finalized)

output.to_row()                            # dict
output.to_dataframe()                      # single-row DataFrame
output.to_sql_insert(table_name='trades')  # INSERT INTO trades ...
```

---

## Debugging

```python
# Quick summary after run_analysis()
print(processor.get_analysis_summary())
# {
#   'cutoff_datetime': ...,
#   'historical_rows': 500,
#   'future_rows': 312,
#   'levels_found': 6,
#   'direction': 'UP',
#   'trade_valid': True
# }
```

Common failure modes:

| Symptom | Likely cause | Fix |
|---|---|---|
| `levels_found: 0` | Too little data or wrong timeframe | Need ≥ 50 bars; check settings JSON |
| `direction: NEUTRAL` | No clear trend | Trade won't be generated — expected |
| `outcome: NO_FUTURE_DATA` | Cutoff too close to end of dataset | Move cutoff earlier |
| `outcome: INVALID` | Missing TP or SL level | Review `trade_maker_settings.json` |

---

## Project structure

```
one_day_proceeding/
├── one_day_proceeding.py      # Main orchestrator — start here
├── levels_finder/             # Detects raw S/R levels
├── levels_handler/            # Filters and manages levels
├── direction_guesser/         # Trend direction
├── trade_maker/               # TP/SL signal generation
├── trade_finalizer/           # Validates against future data
└── one_day_output/            # Formats for DB output

settings_jsons/
├── level_finder_settings.json
└── trade_maker_settings.json
```

---

## Requirements

```
pandas
numpy
```

---

