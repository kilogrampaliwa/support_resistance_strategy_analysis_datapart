# TimeframeDetector

Analyzes OHLC data with a `DatetimeIndex` to detect its timeframe (H1, D1, M5, etc.) — either from the data itself or from the filename. Also provides consistency metrics for the detected intervals.

---

## Quick Start

```python
from proceed_datasets.timeframe_detector.timeframe_detector import TimeframeDetector

detector = TimeframeDetector(tolerance=0.1)

# Detect from DataFrame
timeframe = detector.detect_timeframe(df, sample_size=100)
# → "H1"

# Detect from filename
timeframe = detector.detect_from_filename("EURUSD_H1_2024.csv")
# → "H1"

# Get consistency report
report = detector.analyze_timeframe_consistency(df)
```

---

## Supported Timeframes

| Label | Interval |
|-------|----------|
| `M1`  | 1 minute |
| `M5`  | 5 minutes |
| `M15` | 15 minutes |
| `M30` | 30 minutes |
| `H1`  | 1 hour |
| `H4`  | 4 hours |
| `D1`  | 1 day |
| `W1`  | 1 week |

---

## Methods

### `detect_timeframe(df, sample_size=100)`

Detects timeframe by analyzing the **mode** of time differences between rows.

```python
timeframe = detector.detect_timeframe(df)
# → "D1" | "H1" | "M5" | ... | None
```

| Parameter | Description |
|-----------|-------------|
| `df` | DataFrame with `DatetimeIndex` |
| `sample_size` | Max rows sampled for analysis (default: `100`) |

Returns a timeframe string, or `None` if no match is found.

---

### `detect_from_filename(filename)`

Tries to infer the timeframe from the filename string — no data required.

```python
detector.detect_from_filename("EURUSD_H1_2024.txt")   # → "H1"
detector.detect_from_filename("gbpusd_1h.csv")         # → "H1"
detector.detect_from_filename("daily_data.csv")        # → "D1"
```

Supports both standard labels (`H1`, `D1`, `M5`, ...) and common alternatives:

| Filename pattern | Resolved as |
|-----------------|-------------|
| `1H`, `4H`      | `H1`, `H4`  |
| `1D`            | `D1`        |
| `5M`, `15M`, `30M` | `M5`, `M15`, `M30` |
| `HOURLY`        | `H1`        |
| `DAILY`         | `D1`        |

---

### `analyze_timeframe_consistency(df)`

Returns a dictionary with metrics describing how uniform the intervals are.

```python
report = detector.analyze_timeframe_consistency(df)
```

### Example output

```python
{
    "total_intervals": 1250,
    "most_common_diff_seconds": 3600.0,
    "most_common_count": 1198,
    "consistency_pct": 95.84,
    "top_5_diffs": [(3600.0, 1198), (7200.0, 30), ...],
    "mean_diff": 3612.5,
    "median_diff": 3600.0,
    "std_diff": 142.3,
    "has_gaps": False       # True if consistency_pct < 95%
}
```

| Key | Description |
|-----|-------------|
| `consistency_pct` | % of intervals matching the most common diff |
| `has_gaps` | `True` when consistency drops below 95% |
| `top_5_diffs` | Five most frequent intervals with their counts |

---

## Configuration

### `tolerance` (constructor)

Controls how much deviation from a known interval is allowed when matching.

```python
detector = TimeframeDetector(tolerance=0.1)  # ±10% deviation allowed
```

A `tolerance=0.1` on an H1 frame accepts diffs between **3240s – 3960s**.

---

## Detection Logic

```
DataFrame (DatetimeIndex)
        │
        ▼
 Compute time diffs between rows
        │
        ▼
 Take mode of sampled diffs
        │
        ▼
 Match against TIMEFRAME_PATTERNS with tolerance
        │
        ▼
   Timeframe string | None
```

If the mode diff falls within `±tolerance` of a known interval, that timeframe is returned. Otherwise `None`.