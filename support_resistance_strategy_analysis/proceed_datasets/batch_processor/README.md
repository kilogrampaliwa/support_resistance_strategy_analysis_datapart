# BatchProcessor

Iterates through an OHLC DataFrame and runs the full trading analysis pipeline at regular intervals — analysis, trade finalization, output formatting, and optional database save.

---

## Quick Start

```python
from proceed_datasets.batch_processor.batch_processor import BatchProcessor

processor = BatchProcessor(
    database=db,        # TradingDatabase instance, optional
    step_size=100,
    min_history=200,
    future_bars=100
)

# Single dataset
result = processor.process_dataset(df, pair="EURUSD", timeframe="H1")

# Multiple datasets
results = processor.process_multiple_datasets([
    {'df': df1, 'pair': 'EURUSD', 'timeframe': 'H1'},
    {'df': df2, 'pair': 'GBPUSD', 'timeframe': 'H1'},
])
```

---

## Constructor

```python
BatchProcessor(database=None, step_size=100, min_history=200, future_bars=100)
```

| Parameter | Description |
|-----------|-------------|
| `database` | `TradingDatabase` instance for saving results (optional) |
| `step_size` | Bars between each analysis point (default: `100`) |
| `min_history` | Bars required before the first analysis (default: `200`) |
| `future_bars` | Bars reserved after the cutoff for trade validation (default: `100`) |

The usable iteration range is `[min_history : len(df) - future_bars]`.

---

## Methods

### `process_dataset(df, pair, timeframe, ...)`

Runs the pipeline across a single DataFrame and returns a results summary.

```python
result = processor.process_dataset(
    df=df,
    pair="EURUSD",
    timeframe="H1",
    save_to_db=True,
    direction_method="linear",  # passed to OneDayProceeding
    callback=my_callback        # optional: fn(current, total, trade_data)
)
```

| Parameter | Description |
|-----------|-------------|
| `df` | OHLC DataFrame with `DatetimeIndex` |
| `pair` | Currency pair string (e.g., `"EURUSD"`) |
| `timeframe` | Timeframe string (e.g., `"H1"`) |
| `save_to_db` | Save each trade to the database (default: `True`) |
| `direction_method` | Direction detection method passed to `OneDayProceeding` (default: `"linear"`) |
| `callback` | Optional progress function called after each iteration |

### Example output

```python
{
    "pair": "EURUSD",
    "timeframe": "H1",
    "total_rows": 50000,
    "trades_generated": 492,
    "trades_saved": 490,
    "trades_failed": 8,
    "success_rate": 98.4,
    "duration_seconds": 134.7,
    "start_time": datetime(...),
    "end_time": datetime(...),
    "trades": [...]              # list of trade row dicts
}
```

---

### `process_multiple_datasets(datasets, save_to_db=True, callback=None)`

Runs `process_dataset` over a list of datasets and returns all result dicts.

```python
datasets = [
    {'df': df1, 'pair': 'EURUSD', 'timeframe': 'H1'},
    {'df': df2, 'pair': 'GBPUSD', 'timeframe': 'H1', 'direction_method': 'atr'},
]

results = processor.process_multiple_datasets(datasets)
```

Each entry requires `df`, `pair`, and `timeframe`. `direction_method` is optional (defaults to `"linear"`).

Returns a list of result dicts — one per dataset, in the same format as `process_dataset`.

---

## Pipeline

Each iteration point runs three steps internally:

```
OneDayProceeding.run_analysis()   →   trade_data
        +  get_future_data()
                │
                ▼
     TradeFinalizer.finalize()    →   finalized trade
                │
                ▼
      OneDayOutput.to_row()       →   trade row dict  →  database.insert_trade()
```

If `run_analysis()` returns an `"error"` key, the iteration is skipped and counted as failed.