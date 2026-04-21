# database_handling/database_interface.py

#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 13.03.2026
# Version: 1.0
# Description: Database cleaning utilities for TradingDatabase compatibility
#####################################################

"""
Main Database Interface

High-level interface that combines DatabaseManager, DataOperations,
and QueryBuilder into a single, easy-to-use API.
"""

from dotenv import load_dotenv
import os
import logging
from typing import Optional, List, Dict, Any, Union

import pandas as pd

from database_handling.database_manager.database_manager import DatabaseManager
from database_handling.data_operations.data_operations import DataOperations
from database_handling.query_builder.query_builder import QueryBuilder


# ------------------------------------------------------------------
# Load environment variables from .env (ONCE, at module import)
# ------------------------------------------------------------------
load_dotenv()


# ------------------------------------------------------------------
# Logging configuration
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class TradingDatabase:
    """
    Complete database interface for trading analysis.

    Combines all database operations into a single, unified API.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize database connection.

        Values are taken in the following order:
        1. Explicit arguments
        2. Environment variables (.env)
        3. Hardcoded defaults
        """
        host = host or os.getenv("POSTGRES_HOST", "localhost")
        port = int(port or os.getenv("POSTGRES_PORT", 5432))
        database = database or os.getenv("POSTGRES_DB", "trading_analysis")
        user = user or os.getenv("POSTGRES_USER", "postgres")
        password = password or os.getenv("POSTGRES_PASSWORD", "")

        logger.info(
            "Initializing database connection "
            f"(host={host}, port={port}, database={database}, user={user})"
        )

        # Initialize modules
        self.db_manager = DatabaseManager(host, port, database, user, password)
        self.data_ops = DataOperations(self.db_manager)
        self.query_builder = QueryBuilder(self.db_manager, self.data_ops)

        logger.info(f"Connected to database: {database}")

    # ==========================================
    # Table Management
    # ==========================================

    def table_exists(self, pair: str, timeframe: str) -> bool:
        """Check if table exists for pair/timeframe."""
        return self.db_manager.table_exists(pair, timeframe)

    def create_table(self, pair: str, timeframe: str) -> bool:
        """Create table for pair/timeframe."""
        return self.db_manager.create_table(pair, timeframe)

    def drop_table(self, pair: str, timeframe: str) -> bool:
        """Drop table for pair/timeframe."""
        return self.db_manager.drop_table(pair, timeframe)

    def list_all_tables(self) -> List[Dict[str, str]]:
        """List all trading tables in database."""
        return self.db_manager.list_all_tables()

    def get_table_info(self, pair: str, timeframe: str) -> Dict[str, Any]:
        """Get information about table."""
        return self.db_manager.get_table_info(pair, timeframe)

    # ==========================================
    # Data Operations
    # ==========================================

    def insert_trade(
        self,
        pair: str,
        timeframe: str,
        trade_data: Dict[str, Any]
    ) -> bool:
        """Insert single trade."""
        return self.data_ops.insert_trade(pair, timeframe, trade_data)

    def insert_trades_bulk(
        self,
        pair: str,
        timeframe: str,
        trades: Union[List[Dict[str, Any]], pd.DataFrame]
    ) -> int:
        """Insert multiple trades."""
        return self.data_ops.insert_trades_bulk(pair, timeframe, trades)

    def trade_exists(self, pair: str, timeframe: str, trade_id: str) -> bool:
        """Check if trade exists."""
        return self.data_ops.trade_exists(pair, timeframe, trade_id)

    def get_trade(
        self,
        pair: str,
        timeframe: str,
        trade_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get single trade by ID."""
        return self.data_ops.get_trade(pair, timeframe, trade_id)

    def get_trades(
        self,
        pair: str,
        timeframe: str,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "open_datetime",
        ascending: bool = True,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> pd.DataFrame:
        """Get trades with optional filtering and sorting."""
        return self.data_ops.get_trades(
            pair, timeframe, filters, order_by, ascending, limit, offset
        )

    def get_trades_by_date_range(
        self,
        pair: str,
        timeframe: str,
        start_date,
        end_date
    ) -> pd.DataFrame:
        """Get trades within date range."""
        return self.data_ops.get_trades_by_date_range(
            pair, timeframe, start_date, end_date
        )

    def delete_trade(self, pair: str, timeframe: str, trade_id: str) -> bool:
        """Delete single trade."""
        return self.data_ops.delete_trade(pair, timeframe, trade_id)

    def delete_trades(
        self,
        pair: str,
        timeframe: str,
        filters: Dict[str, Any]
    ) -> int:
        """Delete multiple trades."""
        return self.data_ops.delete_trades(pair, timeframe, filters)

    def update_trade(
        self,
        pair: str,
        timeframe: str,
        trade_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update trade."""
        return self.data_ops.update_trade(pair, timeframe, trade_id, updates)

    # ==========================================
    # Query Builder Methods
    # ==========================================

    def get_winning_trades(
        self,
        pair: str,
        timeframe: str,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """Get winning trades."""
        return self.query_builder.get_winning_trades(pair, timeframe, limit)

    def get_losing_trades(
        self,
        pair: str,
        timeframe: str,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """Get losing trades."""
        return self.query_builder.get_losing_trades(pair, timeframe, limit)

    def get_trades_by_direction(
        self,
        pair: str,
        timeframe: str,
        direction: str
    ) -> pd.DataFrame:
        """Get trades by direction (UP/DOWN/NEUTRAL)."""
        return self.query_builder.get_trades_by_direction(pair, timeframe, direction)

    def get_trades_by_outcome(
        self,
        pair: str,
        timeframe: str,
        outcome: str
    ) -> pd.DataFrame:
        """Get trades by outcome."""
        return self.query_builder.get_trades_by_outcome(pair, timeframe, outcome)

    def get_best_trades(
        self,
        pair: str,
        timeframe: str,
        limit: int = 10
    ) -> pd.DataFrame:
        """Get top N most profitable trades."""
        return self.query_builder.get_best_trades(pair, timeframe, limit)

    def get_worst_trades(
        self,
        pair: str,
        timeframe: str,
        limit: int = 10
    ) -> pd.DataFrame:
        """Get top N worst trades."""
        return self.query_builder.get_worst_trades(pair, timeframe, limit)

    def get_recent_trades(
        self,
        pair: str,
        timeframe: str,
        limit: int = 100
    ) -> pd.DataFrame:
        """Get most recent trades."""
        return self.query_builder.get_recent_trades(pair, timeframe, limit)

    # ==========================================
    # Analytics
    # ==========================================

    def get_performance_stats(
        self,
        pair: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        return self.query_builder.get_performance_stats(pair, timeframe)

    def get_monthly_performance(
        self,
        pair: str,
        timeframe: str
    ) -> pd.DataFrame:
        """Get monthly performance breakdown."""
        return self.query_builder.get_monthly_performance(pair, timeframe)

    def get_direction_performance(
        self,
        pair: str,
        timeframe: str
    ) -> pd.DataFrame:
        """Compare UP vs DOWN performance."""
        return self.query_builder.get_direction_performance(pair, timeframe)

    def get_outcome_distribution(
        self,
        pair: str,
        timeframe: str
    ) -> pd.DataFrame:
        """Get outcome distribution."""
        return self.query_builder.get_outcome_distribution(pair, timeframe)

    # ==========================================
    # Utility Methods
    # ==========================================

    def export_to_csv(
        self,
        pair: str,
        timeframe: str,
        filepath: str,
        **kwargs
    ):
        df = self.get_trades(pair, timeframe, **kwargs)
        df.to_csv(filepath, index=False)
        logger.info(f"Exported {len(df)} trades to {filepath}")

    def import_from_csv(
        self,
        pair: str,
        timeframe: str,
        filepath: str
    ) -> int:
        df = pd.read_csv(filepath)
        return self.insert_trades_bulk(pair, timeframe, df)

    def get_summary(self) -> pd.DataFrame:
        tables = self.list_all_tables()
        if not tables:
            return pd.DataFrame()
        summaries = [self.get_table_info(t['pair'], t['timeframe']) for t in tables]
        return pd.DataFrame(summaries)

    def close(self):
        """Close database connection (if needed for cleanup)."""
        logger.info("Database interface closed")


# Convenience function for quick setup
def connect_to_database(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None
) -> TradingDatabase:
    return TradingDatabase(host, port, database, user, password)
