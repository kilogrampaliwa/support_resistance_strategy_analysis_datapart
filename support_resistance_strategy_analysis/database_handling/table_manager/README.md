# TableManager

Generates PostgreSQL table names from the current JSON configuration and manages per-configuration trade tables. Each unique parameter combination gets its own table.

---

## Quick Start

```python
from database_handling.table_manager.table_manager import (
    generate_table_name_from_config,
    create_table_if_not_exists,
    get_table_info,
    list_all_trade_tables,
    drop_table
)

# Generate name from current config
table_name = generate_table_name_from_config()
# → "trades_d1h1_l5_tp2_sl1_lin"

# Create table if it doesn't exist
create_table_if_not_exists(conn, table_name)

# Inspect
info = get_table_info(conn, table_name)
all_tables = list_all_trade_tables(conn)
```

---

## Table Naming

Table names are generated from three JSON settings files:

```
trades_{timeframes}_l{levels}_tp{tp}_sl{sl}_{method}
```

| Segment | Source | Example |
|---------|--------|---------|
| `timeframes` | Keys from `level_finder_settings.json` (sorted) | `d1h1` |
| `l{levels}` | `levels_handler.levels_count` in `trade_maker_settings.json` | `l5` |
| `tp{tp}` | `trade_maker.tp_level_index` | `tp2` |
| `sl{sl}` | `abs(trade_maker.sl_level_index)` | `sl1` |
| `{method}` | `direction.method` in `direction_config.json` (first 3 chars) | `lin` |

**Full example:** `trades_d1h1_l5_tp2_sl1_lin`

---

## Functions

### `generate_table_name_from_config(...)`

Reads the three config files and returns a PostgreSQL-safe table name.

```python
table_name = generate_table_name_from_config(
    level_finder_path="settings_jsons/level_finder_settings.json",
    trade_maker_path="settings_jsons/trade_maker_settings.json",
    direction_config_path="settings_jsons/direction_config.json"
)
```

---

### `create_table_if_not_exists(conn, table_name)`

Creates the trade table and all performance indices. Safe to call repeatedly — does nothing if the table already exists.

```python
create_table_if_not_exists(conn, table_name)
```

Indices are created automatically on: `pair`, `timeframe`, `outcome`, `direction`, `open_datetime`, `win`, `tp_source`, `sl_source`.

---

### `get_table_info(conn, table_name)`

Returns row counts and outcome breakdown for a table.

```python
info = get_table_info(conn, table_name)
```

### Example output

```python
{
    "table_name": "trades_d1h1_l5_tp2_sl1_lin",
    "total_rows": 48200,
    "unique_pairs": 7,
    "unique_timeframes": 2,
    "first_trade": datetime(2001, 1, 31),
    "last_trade": datetime(2024, 12, 31),
    "tp_count": 21430,
    "sl_count": 18970,
    "open_count": 6200,
    "invalid_count": 1600
}
```

---

### `list_all_trade_tables(conn)`

Returns all tables in the `public` schema with a `trades_` prefix.

```python
tables = list_all_trade_tables(conn)
# → ["trades_d1_l5_tp2_sl1_lin", "trades_h1_l3_tp1_sl1_atr", ...]
```

---

### `drop_table(conn, table_name)`

Drops a table with `CASCADE`. Irreversible — use with caution.

```python
drop_table(conn, "trades_d1h1_l5_tp2_sl1_lin")
```