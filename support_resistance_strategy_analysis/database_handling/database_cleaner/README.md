# DatabaseCleaner

Utility class for truncating, vacuuming, and verifying trade tables. Accepts a `TradingDatabase` instance and operates through its `db_manager`.

---

## Quick Start

```python
from database_handling.database_cleaner.database_cleaner import DatabaseCleaner

cleaner = DatabaseCleaner(db_interface=trading_db)

# Full cleanup of one table
cleaner.full_cleanup("trades_d1h1_l5_tp2_sl1_lin")

# Wipe all trades_ tables
cleaner.clean_all_trade_tables()
```

---

## Constructor

```python
DatabaseCleaner(db_interface)
```

`db_interface` must have a `db_manager` attribute — raises `ValueError` otherwise.

---

## Methods

### `full_cleanup(table_name)`

Runs all four steps in order and returns `True` only if all succeed.

```
1. truncate_table()     — remove all rows, restart identity
2. vacuum_analyze()     — reclaim storage, update planner stats
3. clear_python_cache() — gc.collect()
4. verify_empty()       — assert 0 rows remain
```

---

### Individual Steps

| Method | Description | Returns |
|--------|-------------|---------|
| `truncate_table(table_name)` | `TRUNCATE ... RESTART IDENTITY CASCADE` | `bool` |
| `clean_all_trade_tables()` | Truncates every `trades_*` table | `{table: "SUCCESS"\|"FAILED"}` |
| `vacuum_analyze(table_name=None)` | `VACUUM ANALYZE` on one table or the whole DB | `bool` |
| `clear_python_cache()` | Runs `gc.collect()` | objects collected (`int`) |
| `verify_empty(table_name)` | Confirms row count is 0 | `bool` |

---

## Convenience Function

```python
from database_handling.database_cleaner.database_cleaner import clean_database

clean_database(trading_db, table_name="trades_d1h1_l5_tp2_sl1_lin")
```

Shorthand for `DatabaseCleaner(db).full_cleanup(table_name)`.