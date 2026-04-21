# DirectionGuesser

A unified interface for detecting market trend direction from OHLC candlestick data. Supports three detection strategies: **linear regression**, **quadratic regression**, and **candlestick pattern analysis**.

---

## Quick Start

```python
from one_day_proceeding.direction_guesser.direction_guesser import DirectionGuesser

guesser = DirectionGuesser(method="linear", lookback=20, neutral_threshold=0.0001)
trend = guesser.detect_trend(df)  # returns "UP", "DOWN", or "NEUTRAL"
```

The input `df` must be a pandas DataFrame with at least:
- `w_avre` column — used by `linear` and `quadratic` methods
- `open`, `high`, `low`, `close` columns — used by the `candle` method

---

## Methods

### `linear` — Linear Regression

```python
guesser = DirectionGuesser(method="linear", lookback=20, neutral_threshold=0.0001)
trend = guesser.detect_trend(df)
equation = guesser.get_equation()  # e.g. "y = 0.002341 * x + 1.045231"
```

Fits a straight line to the last `lookback` values of `w_avre`. The **slope** determines direction:
- slope > threshold → `"UP"`
- slope < -threshold → `"DOWN"`
- otherwise → `"NEUTRAL"`

---

### `quadratic` — Quadratic Regression

```python
guesser = DirectionGuesser(method="quadratic", lookback=20, neutral_threshold=0.0001)
trend = guesser.detect_trend(df)
equation = guesser.get_equation()  # e.g. "y = 0.000012 * x^2 + 0.002341 * x + 1.045231"
```

Fits a parabola (`y = ax² + bx + c`) to the last `lookback` values of `w_avre`. Direction is determined by the **derivative at the final point** (`2a·x_last + b`), which tells you which way the curve is heading at that moment:
- derivative > threshold → `"UP"`
- derivative < -threshold → `"DOWN"`
- otherwise → `"NEUTRAL"`

---

### `candle` — Candlestick Pattern Analysis

```python
guesser = DirectionGuesser(method="candle", lookback=10)
trend = guesser.detect_trend(df)
# get_equation() returns None for this method
```

Scans the last `lookback` candles for known bullish and bearish patterns, accumulating a **score**. Each recognized pattern adds or subtracts points:

| Pattern type | Examples | Score |
|---|---|---|
| 1-candle bullish | Hammer, Inverted Hammer | +1 to +2 |
| 1-candle bearish | Hanging Man, Shooting Star | -2 |
| 2-candle bullish | Bullish Engulfing, Piercing Line, Harami Bullish, Tweezer Bottom | +2 to +3 |
| 2-candle bearish | Bearish Engulfing, Dark Cloud Cover, Harami Bearish, Tweezer Top | -2 to -3 |
| 3-candle bullish | Morning Star, Three White Soldiers | +4 |
| 3-candle bearish | Evening Star, Three Black Crows | -4 |

Final decision:
- score > 1 → `"UP"`
- score < -1 → `"DOWN"`
- otherwise → `"NEUTRAL"`

---

## Parameters

| Parameter | Methods | Default | Description |
|---|---|---|---|
| `lookback` | all | `20` (`10` for candle) | Number of recent rows to analyze |
| `neutral_threshold` | linear, quadratic | `0.0001` | Minimum slope/derivative to avoid `"NEUTRAL"` |

---

## How They Interact

```
DirectionGuesser
│
├── method="linear"     → LinearTrend.detect_trend(df)     → slope of fitted line
├── method="quadratic"  → QuadraticTrend.detect_trend(df)  → derivative of fitted parabola
└── method="candle"     → TrendPattern.predict_trend(df)   → cumulative pattern score
```

`DirectionGuesser` is a thin wrapper — it instantiates the correct strategy class based on `method`, then routes all calls through a single `.detect_trend()` interface. The underlying classes are independent and can also be used directly if needed.

---

## Return Values

All methods return one of three strings:

| Value | Meaning |
|---|---|
| `"UP"` | Detected upward trend |
| `"DOWN"` | Detected downward trend |
| `"NEUTRAL"` | No clear direction |