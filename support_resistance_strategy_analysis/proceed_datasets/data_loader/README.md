# DatasetLoader

Loads `.txt` and `.csv` OHLC files from the `input_data` directory — auto-detects separators, headers, datetime formats, and column layouts. Returns a validated DataFrame with a `DatetimeIndex`.

---

## Quick Start

```python
from proceed_datasets.data_loader.dataset_loader import DatasetLoader

loader = DatasetLoader(input_data_dir="input_data")

# List available files
files = loader.list_available_files()

# Load a single file
df = loader.load_file(files[0])

# Quick file info without full load
info = loader.get_file_info(files[0])
```

---

## Constructor

```python
DatasetLoader(input_data_dir="input_data")
```

| Parameter | Description |
|-----------|-------------|
| `input_data_dir` | Path to the input data directory (created automatically if missing) |

---

## Methods

### `list_available_files()`

Returns all `.txt` and `.csv` files in the input directory, sorted alphabetically.

```python
files = loader.list_available_files()
# → [PosixPath('input_data/EURUSD_H1.csv'), ...]
```

---

### `load_file(filepath, parse_dates=True, validate=True)`

Loads a single file into a DataFrame. Handles headers, separators, and datetime parsing automatically.

```python
df = loader.load_file(filepath)
df = loader.load_file(filepath, parse_dates=False, validate=False)
```

| Parameter | Description |
|-----------|-------------|
| `filepath` | `Path` to the file |
| `parse_dates` | Parse datetime column and set as `DatetimeIndex` (default: `True`) |
| `validate` | Check for required OHLC columns and numeric types (default: `True`) |

Returns a `DataFrame`, or `None` if loading or validation fails.

#### Supported separators

Tab (`\t`), comma (`,`), semicolon (`;`) — auto-detected from the first line.

#### Supported column layouts (headerless files)

| Columns | Assigned names |
|---------|---------------|
| 7 | `date, time, open, high, low, close, w_avre` |
| 6 | `datetime, open, high, low, close, w_avre` or `date, time, open, high, low, close` |
| 5 | `datetime, open, high, low, close` |

Files with headers have their column names lowercased and stripped automatically.

#### Supported datetime formats

| Format | Example |
|--------|---------|
| `YYYYMMDDHHMMSS` | `20240101120000` |
| `YYYYMMDD` | `20240101` |
| Standard string | `2024-01-01 12:00:00` |

---

### `get_file_info(filepath)`

Returns metadata about a file without loading the full dataset.

```python
info = loader.get_file_info(filepath)
```

### Example output

```python
{
    "filename": "EURUSD_H1.csv",
    "path": "input_data/EURUSD_H1.csv",
    "exists": True,
    "size_mb": 2.34,
    "columns": ["datetime", "open", "high", "low", "close"],
    "has_ohlc": True,
    "rows": 87600
}
```

---

## Validation

When `validate=True`, `load_file` checks:

- All four OHLC columns (`open`, `high`, `low`, `close`) are present
- All OHLC columns are numeric
- Warns on any `NaN` values found
- Warns if index is not a `DatetimeIndex`

Returns `None` if any required column is missing or non-numeric.