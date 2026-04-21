# TradeMaker

Takes a current price, a list of support/resistance levels, and a market direction — returns a complete set of **TP/SL parameters** for both long and short positions, with full transparency on how each level was resolved.

---

## Quick Start

```python
from one_day_proceeding.trade_maker.trade_maker import tradeMaker

result = tradeMaker(
    price=50000.0,
    levels=[48000, 49000, 49500, 50500, 51000, 52000],
    direction="UP",         # "UP", "DOWN", or "NEUTRAL"
    timestamp="2026-03-05 12:00:00",
    settings_path="settings_jsons/trade_maker_settings.json"
)
```

### Example output

```python
{
    "open_price": 50000.0,
    "direction": "UP",
    "open_datetime": "2026-03-05 12:00:00",
    "long_tp": 50490.0,     # level above, with padding applied
    "long_sl": 48980.0,     # level below, with padding applied
    "short_tp": 49490.0,    # mirrored, stored for reference
    "short_sl": 51010.0,    # mirrored, stored for reference
    "levels_map": {1: 50500, 2: 51000, 3: 52000, -1: 49500, -2: 49000, -3: 48000},
    "levels_used": {
        "tp_index": 1,
        "sl_index": -1,
        "tp_level": 50490.0,
        "sl_level": 48980.0,
        "tp_source": "level",   # "level" | "nearest" | "percent" | "error"
        "sl_source": "level"
    },
    "warnings": []
}
```

---

## JSON Settings File

```json
{
  "trade_maker": {
    "tp_level_index": 1,
    "sl_level_index": -1,
    "fallback_when_missing": "nearest",
    "fallback_percent": 0.01,
    "level_padding_pct": 0.002
  },
  "levels_handler": {
    "levels_count": 5
  }
}
```

| Key | Description |
|---|---|
| `tp_level_index` | Index of the level to use as TP. `1` = first level above price, `2` = second, etc. |
| `sl_level_index` | Index of the level to use as SL. `-1` = first level below price, `-2` = second, etc. |
| `fallback_when_missing` | What to do if the required index has no level: `"nearest"`, `"percent"`, or `"error"`. |
| `fallback_percent` | Step size per index used by the `"percent"` fallback (e.g. `0.01` = 1% per index). |
| `level_padding_pct` | Nudges TP/SL slightly away from the exact level price (e.g. `0.002` = 0.2% inward). |
| `levels_count` | Passed from `levels_handler` — caps how many levels per side are indexed. |

---

## How It Works

### Level indexing

Levels are split around the current price and indexed by distance:

```
... -3: 48000 | -2: 49000 | -1: 49500 | price: 50000 | +1: 50500 | +2: 51000 | +3: 52000 ...
```

`tp_level_index` and `sl_level_index` in the JSON are just numbers that address this map directly.

### Direction logic

| Direction | Active TP/SL | Mirrored (stored, not used) |
|---|---|---|
| `UP` | `long_tp`, `long_sl` | `short_tp`, `short_sl` |
| `DOWN` | `short_tp`, `short_sl` | `long_tp`, `long_sl` |
| `NEUTRAL` | none | none — only `levels_map` is returned |

Both sides are always populated in the result dict for convenience, but only the active side is used for decision-making.

### Fallback chain

If the requested index has no level, three strategies are available (set via `fallback_when_missing`):

1. **`"nearest"`** — uses the closest available level in the same direction.
2. **`"percent"`** — generates a synthetic level at `price × (1 ± fallback_percent × |index|)`.
3. **`"error"`** — sets the level to `None` and appends a warning to `result["warnings"]`.

### Padding

`level_padding_pct` nudges TP/SL inward from the exact level price by a small fraction of the distance between price and level. This avoids placing orders exactly on round-number levels.

### Source tracking

Every TP and SL records how it was resolved in `levels_used.tp_source` / `sl_source`:

| Source | Meaning |
|---|---|
| `"level"` | Exact level found at the requested index |
| `"nearest"` | Fell back to nearest available level in that direction |
| `"percent"` | Synthetically generated via percentage step |
| `"error"` | Could not resolve — value is `None` |

---

## Relationship to LevelHandler

`TradeMaker` is the final consumer of the levels pipeline. It does not find levels — it receives them as a plain list and converts them into actionable trade parameters.

```
LevelHandler → sorted level list
                    │
                    ▼
              tradeMaker()  →  TP / SL for long & short
```