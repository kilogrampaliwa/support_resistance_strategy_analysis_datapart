# DatasetProcessor

Top-level orchestrator for the dataset processing pipeline. Combines `DatasetLoader`, `TimeframeDetector`, and `BatchProcessor` into a single high-level interface.

---

## Quick Start

```python
from proceed_datasets.dataset_processor import DatasetProcessor

processor = DatasetProcessor(database=db)

# Scan available files
datasets = processor.scan_datasets()

# Process one file
result = processor.process_dataset_by_name("EURUSD_H1.txt")

# Process all H1 files
results = processor.process_by_timeframe("H1")
```

---

## Constructor

```python
DatasetProcessor(
    input_dir="input_data",
    database=None,
    step_size=100,
    min_history=200,
    future_bars=100,
    default_timeframe="D1"
)
```

| Parameter | Description |
|-----------|-------------|
| `input_dir` | Input data directory |
| `database` | `TradingDatabase` instance (optional) |
| `step_size` | Bars between analyses — passed to `BatchProcessor` |
| `min_history` | Minimum history bars — passed to `BatchProcessor` |
| `future_bars` | Future bars for validation — passed to `BatchProcessor` |
| `default_timeframe` | Fallback timeframe if none detected (default: `"D1"`) |

---

## Methods

### `scan_datasets(detect_timeframe=False)`

Scans `input_data` and returns metadata for every file found.

```python
datasets = processor.scan_datasets(detect_timeframe=True)
```

When `detect_timeframe=False` (default), timeframe is read from the filename or falls back to `default_timeframe` — no data is loaded. When `True`, data is loaded and analyzed if the filename alone is inconclusive.

---

### `process_dataset_by_name(filename, save_to_db=True, direction_method="linear")`

Loads, analyzes, and processes a single file by name.

```python
result = processor.process_dataset_by_name("EURUSD_H1.txt")
```

Returns a `BatchProcessor` result dict, or `{'error': '...'}` if the file is missing or invalid.

---

### `process_by_timeframe(timeframe, save_to_db=True, direction_method="linear")`

Processes all files matching a given timeframe.

```python
results = processor.process_by_timeframe("H1")
```

Returns a list of result dicts — one per file.

---

### `list_available_datasets(group_by_timeframe=True)`

Returns a summary of all available files, optionally grouped by timeframe.

```python
summary = processor.list_available_datasets()
```

### Example output

```python
{
    "total_datasets": 8,
    "valid_datasets": 7,
    "by_timeframe": {"H1": 4, "D1": 3, "unknown": 1},
    "datasets_by_timeframe": { ... }
}
```

---

## Internal Pipeline

```
input_data/
      │
      ▼
 DatasetLoader          ← lists and loads files
      │
      ▼
 TimeframeDetector      ← detects H1 / D1 / etc.
      │
      ▼
 BatchProcessor         ← runs OneDayProceeding pipeline
      │
      ▼
 TradingDatabase        ← saves results (optional)
```