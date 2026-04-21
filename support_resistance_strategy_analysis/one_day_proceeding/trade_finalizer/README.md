# TradeFinalizer

Takes a trade produced by `TradeMaker` and scans **future price data** to determine whether TP or SL was hit — and when. Returns the original trade dict enriched with outcome fields.

---

## Quick Start

```python
from one_day_proceeding.trade_finalizer.trade_finalizer import TradeFinalizer

finalizer = TradeFinalizer(
    trade_data=trade_data,   # dict returned by tradeMaker()
    future_df=future_df      # OHLC DataFrame starting after the trade open bar
)

result = finalizer.finalize()
```

### Example output

```python
{
    # ... all original trade_data fields preserved ...

    "outcome": "TAKE_PROFIT",       # "TAKE_PROFIT" | "STOP_LOSS" | "OPEN" | "INVALID" | "NO_FUTURE_DATA"
    "tp_datetime": "2026-03-05 14:00:00",
    "sl_datetime": None,
    "close_datetime": "2026-03-05 14:00:00",
    "close_price": 50490.0,
    "bars_to_close": 7,
    "future_bars_scanned": 50
}
```

---

## How It Works

`future_df` is scanned bar by bar. Each bar is checked against TP and SL using the candle's `high` and `low`:

| Position | TP hit condition | SL hit condition |
|---|---|---|
| `LONG` | `high >= tp` | `low <= sl` |
| `SHORT` | `low <= tp` | `high >= sl` |

The scan stops at the first bar where either condition is met. If both are triggered on the same bar, **SL is assumed to have hit first** (conservative, worst-case assumption).

If the scan completes without a hit, the outcome is `"OPEN"`.

---

## Outcome Values

| Outcome | Meaning |
|---|---|
| `"TAKE_PROFIT"` | TP level was reached first |
| `"STOP_LOSS"` | SL level was reached first (or same bar as TP) |
| `"OPEN"` | Neither hit within the provided future data |
| `"INVALID"` | Trade direction was `NEUTRAL`, had an error, or TP/SL were `None` |
| `"NO_FUTURE_DATA"` | `future_df` was empty |

---

## Output Fields

| Field | Description |
|---|---|
| `outcome` | One of the outcome values above |
| `tp_datetime` | Timestamp of the bar where TP was hit, or `None` |
| `sl_datetime` | Timestamp of the bar where SL was hit, or `None` |
| `close_datetime` | Timestamp of trade close (same as tp/sl datetime of the winner) |
| `close_price` | The TP or SL price at close |
| `bars_to_close` | Number of bars scanned until close (or total bars if `"OPEN"`) |
| `future_bars_scanned` | Total bars in `future_df` |

---

## Relationship to TradeMaker

`TradeFinalizer` is the last step in the pipeline. It only reads `trade_data` — it never modifies levels or recalculates anything. Its sole job is outcome validation against real price movement.

```
tradeMaker()  →  trade_data dict
                      │
                      ▼
              TradeFinalizer(trade_data, future_df)
                      │
                      ▼
              result dict  (trade_data + outcome fields)
```