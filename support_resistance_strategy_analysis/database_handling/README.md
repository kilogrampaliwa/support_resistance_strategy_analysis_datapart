# TradingDatabase

Top-level database interface. Combines `DatabaseManager`, `DataOperations`, and `QueryBuilder` into a single object. Connection parameters are resolved from arguments, `.env`, or defaults — in that order.

---

## Quick Start

```python
from database_handling.database_interface import TradingDatabase, connect_to_database

db = TradingDatabase()                     # uses .env or defaults
db = connect_to_database(password="secret") # convenience function

# All sub-module methods available directly
db.insert_trade("EURUSD", "H1", trade_data)
df  = db.get_trades("EURUSD", "H1", filters={"win": True})
stats = db.get_performance_stats("EURUSD", "H1")
```

---

## Constructor

```python
TradingDatabase(host=None, port=None, database=None, user=None, password=None)
```

Each parameter falls back to its `.env` equivalent, then to a hardcoded default:

| Parameter | Env variable | Default |
|-----------|-------------|---------|
| `host` | `POSTGRES_HOST` | `"localhost"` |
| `port` | `POSTGRES_PORT` | `5432` |
| `database` | `POSTGRES_DB` | `"trading_analysis"` |
| `user` | `POSTGRES_USER` | `"postgres"` |
| `password` | `POSTGRES_PASSWORD` | `""` |

---

## Available Methods

All methods delegate directly to the corresponding sub-module. Refer to each module's README for full parameter details.

**Table management** — via `DatabaseManager`
`table_exists`, `create_table`, `drop_table`, `list_all_tables`, `get_table_info`

**CRUD** — via `DataOperations`
`insert_trade`, `insert_trades_bulk`, `trade_exists`, `get_trade`, `get_trades`, `get_trades_by_date_range`, `delete_trade`, `delete_trades`, `update_trade`

**Filtering / Sorting** — via `QueryBuilder`
`get_winning_trades`, `get_losing_trades`, `get_trades_by_direction`, `get_trades_by_outcome`, `get_best_trades`, `get_worst_trades`, `get_recent_trades`

**Analytics** — via `QueryBuilder`
`get_performance_stats`, `get_monthly_performance`, `get_direction_performance`, `get_outcome_distribution`

---

## Utility Methods

| Method | Description |
|--------|-------------|
| `export_to_csv(pair, timeframe, filepath, **kwargs)` | Export trades to CSV |
| `import_from_csv(pair, timeframe, filepath)` | Bulk insert from CSV |
| `get_summary()` | DataFrame with stats for every table in the database |

---

## Internal Structure

```
TradingDatabase
      │
      ├── db_manager    → DatabaseManager
      ├── data_ops      → DataOperations
      └── query_builder → QueryBuilder
```