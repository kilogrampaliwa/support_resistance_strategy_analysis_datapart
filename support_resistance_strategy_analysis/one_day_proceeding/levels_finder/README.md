# LevelsFinder

Identifies **support/resistance levels** from OHLC candle data by combining pivot-based "strong" levels with frequency-based "simple" levels.

---

## Quick Start

```python
from one_day_proceeding.levels_finder.levels_finder import LevelsFinder

finder = LevelsFinder(
    df=df,                      # DataFrame with columns: open, high, low, close
    point_now=1000,             # last index to consider (cuts the lookback window)
    back_window_size=300,       # how many candles to look back
    pivot_window=(5, 5),        # (left bars, right bars) for pivot detection
    strong_freq_bin=10,         # bin size when histogramming pivot closes
    strong_freq_threshold=3,    # min hits in a bin to count as a strong level
    simple_freq_bin=5,          # bin size when histogramming all closes
    simple_freq_threshold=5,    # min hits in a bin to count as a simple level
    merge_margin=8.0            # simple levels within this distance of a strong level are dropped
)

levels = finder.run()           # returns sorted list of price levels
```

You can also run the pipeline step by step:

```python
finder.cutout()          # step 0 — slice the DataFrame
finder.detect_pivots()   # step 1 — find pivot highs/lows
finder.strong_levels()   # step 2 — histogram pivot closes → strong levels
finder.simple_levels()   # step 3 — histogram all closes (excluding strong zones) → simple levels
levels = finder.final_levels()  # step 4 — merge both lists
```

---

## Parameters

| Parameter | Type | Description |
|---|---|---|
| `df` | `pd.DataFrame` | OHLC data. Must contain `open`, `high`, `low`, `close` columns. |
| `point_now` | `float` | Upper bound index — data beyond this point is ignored. |
| `back_window_size` | `int` | Number of rows to look back from `point_now`. |
| `pivot_window` | `int \| tuple` | Window for pivot detection. Tuple `(n1, n2)` sets left/right bars independently. |
| `strong_freq_bin` | `int` | Histogram bin size for pivot close prices. |
| `strong_freq_threshold` | `int` | Minimum frequency to qualify as a strong level. |
| `simple_freq_bin` | `int` | Histogram bin size for all close prices. |
| `simple_freq_threshold` | `int` | Minimum frequency to qualify as a simple level. |
| `merge_margin` | `float` | Distance within which a simple level is suppressed by a nearby strong level. |

---

## How It Works

### The big picture

The pipeline separates levels into two tiers — **strong** and **simple** — then merges them, with strong levels taking priority.

```
Raw OHLC DataFrame
       │
       ▼
  [0] cutout          — slice last N candles up to point_now
       │
       ▼
  [1] detect_pivots   — mark each bar as pivot high, pivot low, or none
       │
       ▼
  [2] strong_levels   — histogram close prices at pivot bars → keep frequent bins
       │
       ▼
  [3] simple_levels   — histogram ALL close prices, skip zones near strong levels → keep frequent bins
       │
       ▼
  [4] final_levels    — merge both lists, drop simple levels too close to strong ones
```

### Strong levels

A bar is a **pivot high** if its `high` is greater than the `n1` bars before it and the `n2` bars after it. Same logic applies to pivot lows using `low`. These are structurally significant turning points.

Close prices at all pivot bars are collected, then dropped into a histogram with bin size `strong_freq_bin`. Any bin hit at least `strong_freq_threshold` times becomes a strong level.

### Simple levels

All close prices in the window are histogrammed with `simple_freq_bin`. Before histogramming, prices that fall within `merge_margin` of any strong level are removed — this prevents double-counting the same zone. Bins meeting `simple_freq_threshold` become simple levels.

### Merging

Strong levels are always kept. Simple levels that land within `merge_margin` of any strong level are dropped. The rest are merged into one sorted list.

---

## Module Map

```
levels_finder/
├── levels_finder.py            # LevelsFinder — main pipeline class
├── cutout_time_period.py       # cutoutTimePeriod() — slices the DataFrame
├── strong_level_points.py      # strongLevelPoints() — pivot high/low detection
├── strong_level_frequencies.py # StrongLevelFrequencies — histograms pivot closes
├── simple_frequencies.py       # SimpleFrequencies — histograms any value list
├── histo_mapping.py            # histoMapping() — core binning utility
└── levels_merger.py            # LevelsMerger + remove_strong_zones()
```