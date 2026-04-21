# LevelHandler

Builds on `LevelsFinder` to produce a **balanced, ready-to-use list of price levels** around the current price. Runs the finder across multiple lookback windows, merges duplicates, folds in previously known levels, and guarantees exactly N levels above and N levels below the current price.

---

## Quick Start

```python
from one_day_proceeding.levels_handler.levels_handler import LevelHandler

handler = LevelHandler(
    json_params_path="settings_jsons/level_finder_settings.json",
    levels_count=5,         # levels required on each side of current price
    levels_diff_treshold=0.01  # 1% minimum gap between any two levels
)

levels = handler.find_and_handle_levels(
    df=df,                  # OHLC DataFrame
    timeframe="1h",         # key used to look up params in the JSON
    previous_levels=[...]   # levels from a prior run (can be empty list)
)
# → sorted list of floats, guaranteed 5 below + 5 above current price
```

---

## JSON Settings File

Parameters for each timeframe live in a JSON file (`level_finder_settings.json`). Each key is a timeframe name; the value is a dict of `LevelsFinder` arguments.

```json
{
  "1h": {
    "back_window_size": 300,
    "pivot_window": [5, 5],
    "strong_freq_bin": 0.001,
    "strong_freq_threshold": 3,
    "simple_freq_bin": 0.0005,
    "simple_freq_threshold": 5,
    "merge_margin": 0.002
  },
  "4h": { ... }
}
```

> **Note:** `strong_freq_bin`, `simple_freq_bin`, and `merge_margin` are treated as **price fractions** — they are automatically multiplied by the last close price before being passed to `LevelsFinder`. Write them as percentages of price (e.g. `0.001` = 0.1% of price).

---

## Constructor Parameters

| Parameter | Type | Description |
|---|---|---|
| `json_params_path` | `str` | Path to the JSON settings file. |
| `levels_count` | `int` | Number of levels to guarantee on each side of current price. |
| `levels_diff_treshold` | `float` | Minimum fractional gap between levels (e.g. `0.01` = 1%). Also used as step size in the percentage-step fallback. |

---

## How It Works

### The big picture

```
OHLC DataFrame + timeframe
        │
        ▼
[1] Run LevelsFinder × 4 windows    — 50, 100, 200, full length
        │
        ▼
[2] Merge collected levels           — drop duplicates within merge_margin
        │
        ▼
[3] Fold in previous_levels          — continuity across calls
        │
        ▼
[4] Percentage filter                — remove levels closer than levels_diff_treshold
        │
        ▼
[5] Enforce count + mirror/fallback  — guarantee N above, N below
        │
        ▼
    Final sorted level list
```

### Step 1 — Multi-window scan

`LevelsFinder` is run four times on increasingly larger slices of the DataFrame (last 50, 100, 200 bars, and the full history). Using multiple windows captures both recent micro-levels and longer-term macro-levels in one pass.

### Step 2 — Merge

All collected levels are sorted and deduplicated: any two levels closer than `merge_margin` are collapsed into one.

### Step 3 — Previous levels

Levels from a prior call can be passed in. This keeps the level set stable between updates and avoids flicker when a level briefly disappears due to new data.

### Step 4 — Percentage filter

After merging, any pair of levels still closer than `levels_diff_treshold` (as a fraction of price) is reduced to one. This enforces a minimum readable gap between levels.

### Step 5 — Enforce count & fill gaps

The final list must have exactly `levels_count` levels on each side of the current price.

- If there are enough real levels → the nearest N are kept per side.
- If there are too few → **mirroring**: existing levels are reflected symmetrically around the current price to fill the gap.
- If mirroring still falls short → **percentage-step fallback**: synthetic levels are generated at fixed `levels_diff_treshold` steps from the outermost real level.

---

## Relationship to LevelsFinder

`LevelHandler` is a higher-order wrapper. It does not change how levels are detected — that is entirely delegated to `LevelsFinder`. Its job is **orchestration and post-processing**: multi-window aggregation, deduplication, continuity, and count enforcement.

```
LevelHandler
    └── LevelsFinder × 4   (one per lookback window)
            └── cutout → detect_pivots → strong_levels → simple_levels → final_levels
```