# OneDayOutput

Takes the finalized trade dict (output of `TradeFinalizer`) and converts it into a **flat, database-ready row**. Also provides convenience exporters for DataFrame, SQL INSERT, and a human-readable summary.

---

## Quick Start

```python
from one_day_proceeding.one_day_output.one_day_output import OneDayOutput

output = OneDayOutput(finalized_data=finalized_data)  # dict from TradeFinalizer

row     = output.to_row()           # dict  — all fields flat
df      = output.to_dataframe()     # single-row DataFrame
sql     = output.to_sql_insert()    # SQL INSERT string
summary = output.get_summary()      # human-readable dict
```

> `finalized_data` must contain a `"pair"` field — it is used to build the unique `trade_id`.

---

## Output Fields

### Identification
| Field | Description |
|---|---|
| `trade_id` | `{pair}_{open_datetime}_{direction}_{timeframe}` |
| `timeframe` | Timeframe string passed in trade data |

### Entry
| Field | Description |
|---|---|
| `open_datetime` | Bar timestamp when trade opened |
| `open_price` | Entry price |
| `direction` | `"UP"`, `"DOWN"`, or `"NEUTRAL"` |

### TP/SL Parameters
| Field | Description |
|---|---|
| `long_tp`, `long_sl` | Levels for long position |
| `short_tp`, `short_sl` | Levels for short position |
| `tp_level_index` | Index used to pick TP from levels map |
| `sl_level_index` | Index used to pick SL from levels map |
| `tp_level_value`, `sl_level_value` | Resolved level prices (before padding) |
| `tp_source`, `sl_source` | How the level was resolved: `"level"` / `"nearest"` / `"percent"` / `"error"` |
| `levels_count` | Number of levels available at trade time |
| `all_levels` | JSON-serialized full level list |
| `levels_map` | JSON-serialized index→price map |

### Outcome
| Field | Description |
|---|---|
| `outcome` | `"TAKE_PROFIT"` / `"STOP_LOSS"` / `"OPEN"` / `"INVALID"` / `"NO_FUTURE_DATA"` |
| `close_datetime` | Timestamp when TP or SL was hit |
| `close_price` | Price at close |
| `bars_to_close` | Bars elapsed until close |
| `tp_hit_datetime`, `sl_hit_datetime` | Individual hit timestamps |
| `future_bars_scanned` | Total bars checked by TradeFinalizer |

### Performance
| Field | Description |
|---|---|
| `profit_loss_pct` | P/L as percentage of entry price (directional) |
| `profit_loss_points` | P/L in raw price points (directional) |
| `win` | `True` = TP hit, `False` = SL hit, `None` = not closed |

### Metadata
| Field | Description |
|---|---|
| `warnings` | JSON-serialized warning list from TradeMaker |
| `cutoff_datetime` | Datetime used as trade open boundary |
| `created_at` | Row generation timestamp |

---

## Export Methods

```python
output.to_row()                          # plain dict
output.to_dataframe()                    # pd.DataFrame, one row
output.to_sql_insert(table_name="trades") # INSERT INTO trades (...) VALUES (%s, ...);
output.get_summary()                     # compact human-readable dict
```

`to_sql_insert()` returns a parameterized statement (placeholders only, no values injected) — pass `list(row.values())` separately to your DB driver.

---

## Relationship to the Pipeline

`OneDayOutput` is the final step. It does no calculation beyond P/L — everything else is just reshaping and serializing data already produced upstream.

```
LevelHandler  →  levels list
                    │
              tradeMaker()  →  trade_data
                                    │
                          TradeFinalizer()  →  finalized_data
                                                    │
                                           OneDayOutput()  →  DB row
```