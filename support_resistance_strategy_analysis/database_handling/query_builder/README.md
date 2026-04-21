# QueryBuilder

High-level query interface for trade analysis. Wraps `DatabaseManager` and `DataOperations` with pre-built filtering, sorting, aggregation, and custom query methods.

---

## Quick Start

```python
from database_handling.query_builder.query_builder import QueryBuilder

qb = QueryBuilder(db_manager=db, data_ops=ops)

# Filtering
winners = qb.get_winning_trades("EURUSD", "H1")
longs   = qb.get_trades_by_direction("EURUSD", "H1", "UP")

# Stats
stats   = qb.get_performance_stats("EURUSD", "H1")
monthly = qb.get_monthly_performance("EURUSD", "H1")
```

---

## Constructor

```python
QueryBuilder(db_manager, data_ops)
```

| Parameter | Description |
|-----------|-------------|
| `db_manager` | `DatabaseManager` instance |
| `data_ops` | `DataOperations` instance |

---

## Filtering

| Method | Returns |
|--------|---------|
| `get_winning_trades(pair, timeframe, limit=None)` | Trades where `win = True`, sorted by P/L desc |
| `get_losing_trades(pair, timeframe, limit=None)` | Trades where `win = False`, sorted by P/L asc |
| `get_trades_by_direction(pair, timeframe, direction)` | `"UP"`, `"DOWN"`, or `"NEUTRAL"` |
| `get_trades_by_outcome(pair, timeframe, outcome)` | `"TAKE_PROFIT"`, `"STOP_LOSS"`, `"OPEN"`, `"INVALID"`, `"NO_FUTURE_DATA"` |

---

## Sorting

| Method | Returns |
|--------|---------|
| `get_best_trades(pair, timeframe, limit=10)` | Top N most profitable wins |
| `get_worst_trades(pair, timeframe, limit=10)` | Top N worst losses |
| `get_recent_trades(pair, timeframe, limit=100)` | Most recent by `open_datetime` |
| `get_longest_trades(pair, timeframe, limit=10)` | Most bars to close |
| `get_quickest_trades(pair, timeframe, limit=10)` | Fewest bars to close (excludes unclosed) |

---

## Statistical Analysis

### `get_performance_stats(pair, timeframe)`

Returns a flat dictionary of aggregate metrics. Excludes `INVALID` outcomes.

```python
stats = qb.get_performance_stats("EURUSD", "H1")
```

Key fields: `total_trades`, `wins`, `losses`, `win_rate_pct`, `avg_win_pct`, `avg_loss_pct`, `avg_profit_loss_pct`, `stddev_profit_pct`, `avg_bars_to_close`, `first_trade`, `last_trade`, `up_trades`, `down_trades`.

---

### `get_monthly_performance(pair, timeframe)`

Returns a DataFrame grouped by month.

Columns: `month`, `trades`, `wins`, `losses`, `win_rate`, `avg_pnl`, `total_pnl`.

---

### `get_direction_performance(pair, timeframe)`

Compares UP vs DOWN performance in a single DataFrame.

Columns: `direction`, `trades`, `wins`, `losses`, `win_rate`, `avg_pnl`, `total_pnl`.

---

### `get_outcome_distribution(pair, timeframe)`

Returns outcome counts with percentage share.

Columns: `outcome`, `count`, `percentage`.

---

## Custom Queries

### `execute_custom_query(pair, timeframe, query, params=None)`

Run arbitrary SQL — use `{table}` as the table name placeholder.

```python
df = qb.execute_custom_query(
    "EURUSD", "H1",
    query="SELECT * FROM {table} WHERE profit_loss_pct > %s",
    params=(2.0,)
)
```

---

### `get_trades_with_complex_filter(pair, timeframe, sql_filter, ...)`

Pre-built `SELECT * FROM {table} WHERE ...` with ordering and limit support.

```python
df = qb.get_trades_with_complex_filter(
    "EURUSD", "H1",
    sql_filter="direction = 'UP' AND win = TRUE AND open_datetime > %s",
    params=(datetime.now() - timedelta(days=30),),
    order_by="profit_loss_pct",
    ascending=False,
    limit=50
)
```

JSON fields (`all_levels`, `levels_map`, `warnings`) are deserialized automatically.