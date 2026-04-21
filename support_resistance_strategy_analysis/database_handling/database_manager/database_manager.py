# database_handling/database_manager/database_manager.py

#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 13.03.2026
# Version: 1.0
# Description: PostgreSQL Database Manager for Trading Analysis. Manages database connections, table creation, and basic operations for storing trade analysis results organized by currency pair and timeframe.
#####################################################

"""
PostgreSQL Database Manager for Trading Analysis

Manages database connections, table creation, and basic operations
for storing trade analysis results organized by currency pair and timeframe.
"""

import psycopg2
from psycopg2 import extras
from typing import List, Dict, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Main database manager for trading analysis results.

    Database structure:
    - One database for all trading data
    - Separate table for each currency pair + timeframe combination
    - Table naming: {pair}_{timeframe} (e.g., eurusd_h1, gbpusd_d1)
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "trading_analysis",
        user: str = "postgres",
        password: str = ""
    ):
        """
        Initialize database connection parameters.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
        """
        self.connection_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password
        }
        self._test_connection()

    def _test_connection(self):
        """Test database connection on initialization."""
        try:
            with self.get_connection() as conn:
                logger.info(f"Successfully connected to database: {self.connection_params['database']}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.

        Usage:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(...)
        """
        conn = psycopg2.connect(**self.connection_params)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction failed: {e}")
            raise
        finally:
            conn.close()

    def get_table_name(self, pair: str, timeframe: str) -> str:
        """
        Generate table name from currency pair and timeframe.

        Args:
            pair: Currency pair (e.g., "EURUSD", "GBPUSD")
            timeframe: Timeframe (e.g., "H1", "D1")

        Returns:
            Table name (e.g., "eurusd_h1")
        """
        # Normalize to lowercase and remove special characters
        pair_clean = pair.lower().replace("/", "").replace("-", "")
        timeframe_clean = timeframe.lower()
        return f"{pair_clean}_{timeframe_clean}"

    def table_exists(self, pair: str, timeframe: str) -> bool:
        """
        Check if table for given pair and timeframe exists.

        Args:
            pair: Currency pair
            timeframe: Timeframe

        Returns:
            True if table exists, False otherwise
        """
        table_name = self.get_table_name(pair, timeframe)

        query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            );
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (table_name,))
            exists = cursor.fetchone()[0]
            cursor.close()

        return exists

    def create_table(self, pair: str, timeframe: str, if_not_exists: bool = True) -> bool:
        """
        Create table for storing trade analysis results.

        Args:
            pair: Currency pair
            timeframe: Timeframe
            if_not_exists: Only create if doesn't exist

        Returns:
            True if table created, False if already existed
        """
        table_name = self.get_table_name(pair, timeframe)

        if if_not_exists and self.table_exists(pair, timeframe):
            logger.info(f"Table {table_name} already exists")
            return False

        # SQL schema matching OneDayOutput structure
        create_query = f"""
            CREATE TABLE {table_name} (
                -- Identification
                trade_id VARCHAR(100) PRIMARY KEY,
                timeframe VARCHAR(10),

                -- Entry information
                open_datetime TIMESTAMP,
                open_price DECIMAL(12, 6),
                direction VARCHAR(10),

                -- TP/SL parameters
                long_tp DECIMAL(12, 6),
                long_sl DECIMAL(12, 6),
                short_tp DECIMAL(12, 6),
                short_sl DECIMAL(12, 6),

                -- Level information
                tp_level_index INTEGER,
                sl_level_index INTEGER,
                all_levels TEXT,
                levels_map TEXT,

                -- Trade outcome
                outcome VARCHAR(20),
                close_datetime TIMESTAMP,
                close_price DECIMAL(12, 6),
                bars_to_close INTEGER,

                -- Performance metrics
                profit_loss_pct DECIMAL(10, 4),
                profit_loss_points DECIMAL(12, 6),
                win BOOLEAN,

                -- Additional data
                tp_datetime TIMESTAMP,
                sl_datetime TIMESTAMP,
                future_bars_scanned INTEGER,
                warnings TEXT,

                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Indexes for common queries
                INDEX idx_open_datetime (open_datetime),
                INDEX idx_outcome (outcome),
                INDEX idx_direction (direction),
                INDEX idx_win (win)
            );
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(create_query)
            cursor.close()

        logger.info(f"Created table: {table_name}")
        return True

    def drop_table(self, pair: str, timeframe: str, if_exists: bool = True) -> bool:
        """
        Drop table for given pair and timeframe.

        Args:
            pair: Currency pair
            timeframe: Timeframe
            if_exists: Only drop if exists

        Returns:
            True if dropped, False if didn't exist
        """
        table_name = self.get_table_name(pair, timeframe)

        if if_exists and not self.table_exists(pair, timeframe):
            logger.info(f"Table {table_name} doesn't exist")
            return False

        drop_query = f"DROP TABLE {table_name};"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(drop_query)
            cursor.close()

        logger.info(f"Dropped table: {table_name}")
        return True

    def list_all_tables(self) -> List[Dict[str, str]]:
        """
        List all trading analysis tables in database.

        Returns:
            List of dicts with 'pair' and 'timeframe' keys
        """
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            tables = [row[0] for row in cursor.fetchall()]
            cursor.close()

        # Parse table names back to pair/timeframe
        result = []
        for table in tables:
            parts = table.rsplit('_', 1)
            if len(parts) == 2:
                result.append({
                    'pair': parts[0].upper(),
                    'timeframe': parts[1].upper(),
                    'table_name': table
                })

        return result

    def get_table_info(self, pair: str, timeframe: str) -> Dict[str, Any]:
        """
        Get information about table (row count, date range, etc).

        Args:
            pair: Currency pair
            timeframe: Timeframe

        Returns:
            Dictionary with table statistics
        """
        if not self.table_exists(pair, timeframe):
            return {"exists": False}

        table_name = self.get_table_name(pair, timeframe)

        query = f"""
            SELECT
                COUNT(*) as total_rows,
                COUNT(CASE WHEN win = TRUE THEN 1 END) as wins,
                COUNT(CASE WHEN win = FALSE THEN 1 END) as losses,
                MIN(open_datetime) as earliest_trade,
                MAX(open_datetime) as latest_trade,
                AVG(profit_loss_pct) as avg_profit_loss_pct
            FROM {table_name};
        """

        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute(query)
            stats = cursor.fetchone()
            cursor.close()

        return {
            "exists": True,
            "table_name": table_name,
            "pair": pair,
            "timeframe": timeframe,
            **dict(stats)
        }

    def ensure_table_exists(self, pair: str, timeframe: str) -> str:
        """
        Ensure table exists, create if it doesn't.

        Args:
            pair: Currency pair
            timeframe: Timeframe

        Returns:
            Table name
        """
        if not self.table_exists(pair, timeframe):
            self.create_table(pair, timeframe)

        return self.get_table_name(pair, timeframe)
