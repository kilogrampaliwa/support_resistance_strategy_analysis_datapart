# DatabaseManager

Manages PostgreSQL connections and trade result tables. Each currency pair + timeframe combination gets its own table (e.g., `eurusd_h1`, `gbpusd_d1`).

---

## Quick Start

```python
from database_handling.database_manager.database_manager import DatabaseManager

db = DatabaseManager(
    host="localhost",
    port=5432,
    database="trading_analysis",
    user="postgres",
    password="secret"
)

db.ensure_table_exists("EURUSD", "H1")
info = db.get_table_info("EURUSD", "H1")
```

---

## Constructor

```python
DatabaseManager(host="localhost", port=5432, database="trading_analysis", user="postgres", password="")
```

Connection is tested immediately on init — raises an exception if unreachable.

---

## Table Naming

```python
db.get_table_name("EURUSD", "H1")  # → "eurusd_h1"
db.get_table_name("GBP/USD", "D1") # → "gbpusd_d1"
```

Pair and timeframe are lowercased; `/` and `-` are stripped.

---

## Methods

### Connection

```python
with db.get_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT ...")
```

Context manager — commits on success, rolls back on error, always closes.

---

### Table Management

| Method | Description |
|--------|-------------|
| `table_exists(pair, timeframe)` | Returns `True` if the table is present |
| `ensure_table_exists(pair, timeframe)` | Creates table if missing, returns table name |
| `create_table(pair, timeframe, if_not_exists=True)` | Creates table; returns `False` if already existed |
| `drop_table(pair, timeframe, if_exists=True)` | Drops table; returns `False` if didn't exist |
| `list_all_tables()` | Lists all tables as `[{'pair', 'timeframe', 'table_name'}, ...]` |

---

### `get_table_info(pair, timeframe)`

Returns basic statistics for a table without running a custom query.

```python
info = db.get_table_info("EURUSD", "H1")
```

### Example output

```python
{
    "exists": True,
    "table_name": "eurusd_h1",
    "pair": "EURUSD",
    "timeframe": "H1",
    "total_rows": 48200,
    "wins": 24100,
    "losses": 18600,
    "earliest_trade": datetime(2001, 1, 31),
    "latest_trade": datetime(2024, 12, 31),
    "avg_profit_loss_pct": 0.38
}
```

Returns `{"exists": False}` if the table doesn't exist.