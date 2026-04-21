# DataOperations

Handles all CRUD operations for trade data. Works on top of `DatabaseManager` and returns results as pandas DataFrames. JSON fields (`all_levels`, `levels_map`, `warnings`) are serialized/deserialized automatically.

---

## Quick Start

```python
from database_handling.data_operations.data_operations import DataOperations

ops = DataOperations(db_manager=db)

# Insert
ops.insert_trade("EURUSD", "H1", trade_data)
ops.insert_trades_bulk("EURUSD", "H1", trades_list)

# Query
df = ops.get_trades("EURUSD", "H1", filters={"win": True})
df = ops.get_trades_by_date_range("EURUSD", "H1", "2023-01-01", "2023-12-31")
```

---

## Constructor

```python
DataOperations(db_manager)
```

| Parameter | Description |
|-----------|-------------|
| `db_manager` | `DatabaseManager` instance |

---

## Insert

### `insert_trade(pair, timeframe, trade_data, ensure_table=True)`

Inserts a single trade dict (from `OneDayOutput.to_row()`). Silently skips on `trade_id` conflict.

```python
ops.insert_trade("EURUSD", "H1", trade_data)
```

---

### `insert_trades_bulk(pair, timeframe, trades, ensure_table=True, overwrite=True)`

Bulk insert from a list of dicts or a DataFrame.

```python
ops.insert_trades_bulk("EURUSD", "H1", df, overwrite=True)
```

When `overwrite=True`, all existing rows are deleted before inserting. Returns number of rows inserted.

---

## Query

### `get_trades(pair, timeframe, filters=None, order_by="open_datetime", ascending=True, limit=None, offset=0)`

Main query method — returns a DataFrame with optional filtering, sorting, and pagination.

```python
# Winning trades sorted by P/L
df = ops.get_trades("EURUSD", "H1", filters={"win": True}, order_by="profit_loss_pct", ascending=False)

# Last 100 trades
df = ops.get_trades("EURUSD", "H1", order_by="open_datetime", ascending=False, limit=100)
```

`filters` accepts any column as a key — multiple keys are combined with `AND`.

---

### `get_trades_by_date_range(pair, timeframe, start_date, end_date)`

Returns trades where `open_datetime BETWEEN start AND end`. Accepts strings or `datetime` objects.

```python
df = ops.get_trades_by_date_range("EURUSD", "H1", "2023-01-01", "2023-12-31")
```

---

### `get_trade(pair, timeframe, trade_id)`

Returns a single trade as a dict, or `None` if not found.

---

### `trade_exists(pair, timeframe, trade_id)`

Returns `True` if a trade with the given ID exists.

---

## Delete

| Method | Description | Returns |
|--------|-------------|---------|
| `delete_trade(pair, timeframe, trade_id)` | Delete by ID | `bool` |
| `delete_trades(pair, timeframe, filters)` | Delete all rows matching filters dict | rows deleted (`int`) |

Passing an empty `filters={}` to `delete_trades` removes all rows in the table.

---

## Update

### `update_trade(pair, timeframe, trade_id, updates)`

Updates specific fields on a single trade. Returns `True` if the trade was found and updated.

```python
ops.update_trade("EURUSD", "H1", "trade_001", {"outcome": "TAKE_PROFIT", "win": True})
```