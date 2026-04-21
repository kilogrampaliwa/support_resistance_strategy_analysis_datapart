# database_handling/table_manager/table_manager.py

#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 13.03.2026
# Version: 1.0
# Description: Dynamic table manager for multi-configuration storage. Each parameter combination gets its own table.
#####################################################


"""
Dynamic table manager for multi-configuration storage.
Each parameter combination gets its own table.
"""

import json
from pathlib import Path
from typing import Dict, Any
import psycopg2


def generate_table_name_from_config(
    level_finder_path: str = "settings_jsons/level_finder_settings.json",
    trade_maker_path: str = "settings_jsons/trade_maker_settings.json",
    direction_config_path: str = "settings_jsons/direction_config.json"  # ✅ ADDED
) -> str:
    """
    Generates table name from current configuration.

    Format: trades_{timeframes}_l{levels}_tp{tp}_sl{sl}_{method}
    Example: trades_h1d1_l5_tp2_sl2_lin

    Args:
        level_finder_path: Path to level finder settings JSON
        trade_maker_path: Path to trade maker settings JSON
        direction_config_path: Path to direction config JSON (FIXED)

    Returns:
        Table name (lowercase, PostgreSQL-safe)
    """
    # Load configurations
    with open(trade_maker_path, 'r', encoding='utf-8') as f:
        trade_config = json.load(f)

    with open(level_finder_path, 'r', encoding='utf-8') as f:
        level_config = json.load(f)

    # ✅ FIXED - Load direction config separately
    with open(direction_config_path, 'r', encoding='utf-8') as f:
        direction_config = json.load(f)

    # Extract timeframes (sorted for consistency)
    timeframes = sorted(level_config.keys())
    tf_str = ''.join(timeframes).lower()

    # Extract parameters
    levels_count = trade_config.get('levels_handler', {}).get('levels_count', 5)
    tp_idx = trade_config.get('trade_maker', {}).get('tp_level_index', 2)
    sl_idx = abs(trade_config.get('trade_maker', {}).get('sl_level_index', -1))

    # ✅ FIXED - Read method from direction_config.json (not trade_maker_settings.json)
    method = direction_config.get('direction', {}).get('method', 'linear')[:3]

    # Build table name
    table_name = f"trades_{tf_str}_l{levels_count}_tp{tp_idx}_sl{sl_idx}_{method}"

    # Sanitize (ensure PostgreSQL-safe)
    table_name = table_name.lower().replace('-', '_')

    return table_name


def create_table_if_not_exists(conn, table_name: str) -> None:
    """
    Creates trades table with given name if it doesn't exist.

    Schema includes all 3 method columns (lin_, quad_, cnd_) and max_duration.

    Args:
        conn: PostgreSQL connection
        table_name: Name of table to create
    """
    create_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        -- Identification
        trade_id VARCHAR(255) PRIMARY KEY,
        timeframe VARCHAR(10),
        pair VARCHAR(20),
        symbol VARCHAR(20),
        dataset VARCHAR(100),

        -- Entry information
        open_datetime TIMESTAMP,
        open_price DOUBLE PRECISION,
        direction VARCHAR(10),

        -- Trade parameters - LONG (legacy / primary method)
        long_tp DOUBLE PRECISION,
        long_sl DOUBLE PRECISION,

        -- Trade parameters - SHORT (legacy / primary method)
        short_tp DOUBLE PRECISION,
        short_sl DOUBLE PRECISION,

        -- Levels information
        tp_level_index INTEGER,
        sl_level_index INTEGER,
        tp_level_value DOUBLE PRECISION,
        sl_level_value DOUBLE PRECISION,
        tp_source VARCHAR(20),
        sl_source VARCHAR(20),
        levels_count INTEGER,
        all_levels TEXT,
        levels_map TEXT,

        -- Trade outcome
        outcome VARCHAR(50),
        close_datetime TIMESTAMP,
        close_price DOUBLE PRECISION,
        bars_to_close INTEGER,

        -- Timing information
        tp_hit_datetime TIMESTAMP,
        sl_hit_datetime TIMESTAMP,

        -- Performance metrics
        profit_loss_pct DOUBLE PRECISION,
        profit_loss_points DOUBLE PRECISION,
        win BOOLEAN,

        -- Additional context
        warnings TEXT,
        future_bars_scanned INTEGER,
        cutoff_datetime TIMESTAMP,

        -- Max duration setting (seconds)
        max_duration INTEGER,

        -- Per-method columns: linear (lin_)
        lin_tp_long NUMERIC,
        lin_sl_long NUMERIC,
        lin_tp_short NUMERIC,
        lin_sl_short NUMERIC,
        lin_close_date TIMESTAMP,

        -- Per-method columns: quadratic (quad_)
        quad_tp_long NUMERIC,
        quad_sl_long NUMERIC,
        quad_tp_short NUMERIC,
        quad_sl_short NUMERIC,
        quad_close_date TIMESTAMP,

        -- Per-method columns: candle (cnd_)
        cnd_tp_long NUMERIC,
        cnd_sl_long NUMERIC,
        cnd_tp_short NUMERIC,
        cnd_sl_short NUMERIC,
        cnd_close_date TIMESTAMP,

        -- Metadata
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    with conn.cursor() as cursor:
        cursor.execute(create_query)
        conn.commit()

    # Create indices for performance
    create_indices(conn, table_name)


def create_indices(conn, table_name: str) -> None:
    """
    Creates indices on commonly queried columns.

    Args:
        conn: PostgreSQL connection
        table_name: Name of table
    """
    indices = [
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_pair ON {table_name}(pair);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_timeframe ON {table_name}(timeframe);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_outcome ON {table_name}(outcome);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_direction ON {table_name}(direction);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_open_datetime ON {table_name}(open_datetime);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_win ON {table_name}(win);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_tp_source ON {table_name}(tp_source);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_sl_source ON {table_name}(sl_source);"
    ]

    with conn.cursor() as cursor:
        for idx_query in indices:
            cursor.execute(idx_query)
        conn.commit()


def create_new_schema_table(conn, table_name: str) -> None:
    """
    Creates the new-schema analysis table if it does not exist.

    One table per ticker+timeframe (e.g. eurusd_1h, gbpusd_1d).
    Each row represents one analysed candle with directions from all
    3 methods and outcomes for both LONG (end_up) and SHORT (end_down).

    Args:
        conn:       PostgreSQL connection (psycopg2)
        table_name: Target table name, e.g. "eurusd_1h"
    """
    create_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id                     SERIAL PRIMARY KEY,
        ticker                 VARCHAR(20)        NOT NULL,
        timeframe              VARCHAR(10)        NOT NULL,
        full_date_open         TIMESTAMP          NOT NULL,

        -- Direction signals (UP / DOWN / NEUTRAL)
        linear_direction       VARCHAR(10),
        logarithmic_direction  VARCHAR(10),
        candle_direction       VARCHAR(10),

        -- Level-derived TP/SL (direction-independent, same for all methods)
        long_tp                DOUBLE PRECISION,
        long_sl                DOUBLE PRECISION,
        short_tp               DOUBLE PRECISION,
        short_sl               DOUBLE PRECISION,

        -- UP trade outcome (LONG position)
        end_up_reason          VARCHAR(20),       -- TAKE_PROFIT | STOP_LOSS | MAX_DURATION | OPEN | INVALID | NO_FUTURE_DATA
        end_up_close_price     DOUBLE PRECISION,
        end_up_close_date      TIMESTAMP,

        -- DOWN trade outcome (SHORT position)
        end_down_reason        VARCHAR(20),
        end_down_close_price   DOUBLE PRECISION,
        end_down_close_date    TIMESTAMP,

        created_at             TIMESTAMP          DEFAULT CURRENT_TIMESTAMP,

        UNIQUE (ticker, timeframe, full_date_open)
    );
    """
    with conn.cursor() as cur:
        cur.execute(create_query)
    conn.commit()

    _create_new_schema_indices(conn, table_name)


def _create_new_schema_indices(conn, table_name: str) -> None:
    """Creates indices on the new-schema table for common query patterns."""
    indices = [
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_open ON {table_name}(full_date_open);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_lin  ON {table_name}(linear_direction);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_log  ON {table_name}(logarithmic_direction);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_cnd  ON {table_name}(candle_direction);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_up   ON {table_name}(end_up_reason);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_name}_down ON {table_name}(end_down_reason);",
    ]
    with conn.cursor() as cur:
        for stmt in indices:
            cur.execute(stmt)
    conn.commit()


def insert_new_schema_row(conn, table_name: str, row: Dict[str, Any]) -> bool:
    """
    Inserts one new-schema row.  Silently skips on UNIQUE conflict
    (ticker, timeframe, full_date_open).

    Args:
        conn:       PostgreSQL connection
        table_name: Target table, e.g. "eurusd_1h"
        row:        Dict from OneDayOutput.to_new_schema_row()

    Returns:
        True if inserted, False if skipped (conflict) or on error.
    """
    if not row:
        return False

    columns      = list(row.keys())
    placeholders = ["%s"] * len(columns)
    values       = [row[c] for c in columns]

    sql = (
        f"INSERT INTO {table_name} ({', '.join(columns)}) "
        f"VALUES ({', '.join(placeholders)}) "
        f"ON CONFLICT (ticker, timeframe, full_date_open) DO NOTHING;"
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql, values)
            inserted = cur.rowcount   # read before cursor closes
        conn.commit()
        return inserted > 0
    except Exception as exc:
        conn.rollback()
        print(f"[INSERT ERROR] {table_name}: {exc}")
        return False


def get_table_info(conn, table_name: str) -> Dict[str, Any]:
    """
    Gets information about a table.

    Args:
        conn: PostgreSQL connection
        table_name: Name of table

    Returns:
        Dictionary with table statistics
    """
    query = f"""
    SELECT
        COUNT(*) as total_rows,
        COUNT(DISTINCT pair) as unique_pairs,
        COUNT(DISTINCT timeframe) as unique_timeframes,
        MIN(open_datetime) as first_trade,
        MAX(open_datetime) as last_trade,
        SUM(CASE WHEN outcome = 'TAKE_PROFIT' THEN 1 ELSE 0 END) as tp_count,
        SUM(CASE WHEN outcome = 'STOP_LOSS' THEN 1 ELSE 0 END) as sl_count,
        SUM(CASE WHEN outcome = 'OPEN' THEN 1 ELSE 0 END) as open_count,
        SUM(CASE WHEN outcome = 'INVALID' THEN 1 ELSE 0 END) as invalid_count
    FROM {table_name}
    """

    with conn.cursor() as cursor:
        cursor.execute(query)
        result = cursor.fetchone()

        if result:
            return {
                'table_name': table_name,
                'total_rows': result[0],
                'unique_pairs': result[1],
                'unique_timeframes': result[2],
                'first_trade': result[3],
                'last_trade': result[4],
                'tp_count': result[5],
                'sl_count': result[6],
                'open_count': result[7],
                'invalid_count': result[8]
            }
        return {}


def list_all_trade_tables(conn) -> list:
    """
    Lists all tables starting with 'trades_'.

    Args:
        conn: PostgreSQL connection

    Returns:
        List of table names
    """
    query = """
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
      AND tablename LIKE 'trades_%'
    ORDER BY tablename;
    """

    with conn.cursor() as cursor:
        cursor.execute(query)
        return [row[0] for row in cursor.fetchall()]


def drop_table(conn, table_name: str) -> None:
    """
    Drops a table (use with caution!).

    Args:
        conn: PostgreSQL connection
        table_name: Name of table to drop
    """
    query = f"DROP TABLE IF EXISTS {table_name} CASCADE;"

    with conn.cursor() as cursor:
        cursor.execute(query)
        conn.commit()