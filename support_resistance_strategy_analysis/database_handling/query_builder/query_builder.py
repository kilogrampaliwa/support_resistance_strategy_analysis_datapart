# database_handling/query_builder/query_builder.py

#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 13.03.2026
# Version: 1.0
# Description: Query builder for advanced trade analysis. Provides high-level methods for common queries and performance statistics.
#####################################################


"""
Query Builder Module

Advanced query construction with sorting, filtering, aggregation,
and performance analysis capabilities.
"""

import pandas as pd
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class QueryBuilder:
    """
    Advanced query builder for trade analysis.

    Provides high-level methods for common queries and analysis tasks.
    """

    def __init__(self, db_manager, data_ops):
        """
        Initialize with DatabaseManager and DataOperations.

        Args:
            db_manager: DatabaseManager instance
            data_ops: DataOperations instance
        """
        self.db = db_manager
        self.ops = data_ops

    # ==========================================
    # Filtering Methods
    # ==========================================

    def get_winning_trades(
        self,
        pair: str,
        timeframe: str,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """Get only winning trades."""
        return self.ops.get_trades(
            pair, timeframe,
            filters={"win": True},
            order_by="profit_loss_pct",
            ascending=False,
            limit=limit
        )

    def get_losing_trades(
        self,
        pair: str,
        timeframe: str,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """Get only losing trades."""
        return self.ops.get_trades(
            pair, timeframe,
            filters={"win": False},
            order_by="profit_loss_pct",
            ascending=True,
            limit=limit
        )

    def get_trades_by_direction(
        self,
        pair: str,
        timeframe: str,
        direction: str
    ) -> pd.DataFrame:
        """
        Get trades by direction (UP/DOWN/NEUTRAL).

        Args:
            pair: Currency pair
            timeframe: Timeframe
            direction: "UP", "DOWN", or "NEUTRAL"
        """
        return self.ops.get_trades(
            pair, timeframe,
            filters={"direction": direction.upper()}
        )

    def get_trades_by_outcome(
        self,
        pair: str,
        timeframe: str,
        outcome: str
    ) -> pd.DataFrame:
        """
        Get trades by outcome.

        Args:
            pair: Currency pair
            timeframe: Timeframe
            outcome: "TAKE_PROFIT", "STOP_LOSS", "OPEN", "INVALID", "NO_FUTURE_DATA"
        """
        return self.ops.get_trades(
            pair, timeframe,
            filters={"outcome": outcome.upper()}
        )

    # ==========================================
    # Sorting Methods
    # ==========================================

    def get_best_trades(
        self,
        pair: str,
        timeframe: str,
        limit: int = 10
    ) -> pd.DataFrame:
        """Get top N most profitable trades."""
        return self.ops.get_trades(
            pair, timeframe,
            filters={"win": True},
            order_by="profit_loss_pct",
            ascending=False,
            limit=limit
        )

    def get_worst_trades(
        self,
        pair: str,
        timeframe: str,
        limit: int = 10
    ) -> pd.DataFrame:
        """Get top N worst trades."""
        return self.ops.get_trades(
            pair, timeframe,
            filters={"win": False},
            order_by="profit_loss_pct",
            ascending=True,
            limit=limit
        )

    def get_recent_trades(
        self,
        pair: str,
        timeframe: str,
        limit: int = 100
    ) -> pd.DataFrame:
        """Get most recent trades."""
        return self.ops.get_trades(
            pair, timeframe,
            order_by="open_datetime",
            ascending=False,
            limit=limit
        )

    def get_longest_trades(
        self,
        pair: str,
        timeframe: str,
        limit: int = 10
    ) -> pd.DataFrame:
        """Get trades with most bars to close."""
        return self.ops.get_trades(
            pair, timeframe,
            order_by="bars_to_close",
            ascending=False,
            limit=limit
        )

    def get_quickest_trades(
        self,
        pair: str,
        timeframe: str,
        limit: int = 10
    ) -> pd.DataFrame:
        """Get trades with fewest bars to close."""
        df = self.ops.get_trades(pair, timeframe)
        # Filter out trades that didn't close
        df = df[df['bars_to_close'].notna()]
        return df.sort_values('bars_to_close').head(limit)

    # ==========================================
    # Statistical Analysis
    # ==========================================

    def get_performance_stats(
        self,
        pair: str,
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive performance statistics.

        Returns:
            Dictionary with performance metrics
        """
        if not self.db.table_exists(pair, timeframe):
            return {"error": "Table doesn't exist"}

        table_name = self.db.get_table_name(pair, timeframe)

        query = f"""
            SELECT
                COUNT(*) as total_trades,
                COUNT(CASE WHEN win = TRUE THEN 1 END) as wins,
                COUNT(CASE WHEN win = FALSE THEN 1 END) as losses,
                COUNT(CASE WHEN outcome = 'OPEN' THEN 1 END) as open_trades,

                -- Win rate
                ROUND(100.0 * COUNT(CASE WHEN win = TRUE THEN 1 END) /
                      NULLIF(COUNT(CASE WHEN win IS NOT NULL THEN 1 END), 0), 2) as win_rate_pct,

                -- Direction breakdown
                COUNT(CASE WHEN direction = 'UP' THEN 1 END) as up_trades,
                COUNT(CASE WHEN direction = 'DOWN' THEN 1 END) as down_trades,
                COUNT(CASE WHEN direction = 'NEUTRAL' THEN 1 END) as neutral_trades,

                -- P/L stats
                AVG(profit_loss_pct) as avg_profit_loss_pct,
                MAX(profit_loss_pct) as max_profit_pct,
                MIN(profit_loss_pct) as min_profit_pct,
                STDDEV(profit_loss_pct) as stddev_profit_pct,

                -- Winning trades stats
                AVG(CASE WHEN win = TRUE THEN profit_loss_pct END) as avg_win_pct,
                AVG(CASE WHEN win = FALSE THEN profit_loss_pct END) as avg_loss_pct,

                -- Timing stats
                AVG(bars_to_close) as avg_bars_to_close,
                MAX(bars_to_close) as max_bars_to_close,
                MIN(bars_to_close) as min_bars_to_close,

                -- Date range
                MIN(open_datetime) as first_trade,
                MAX(open_datetime) as last_trade

            FROM {table_name}
            WHERE outcome != 'INVALID';
        """

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()
            cursor.close()

        # Column names
        columns = [
            'total_trades', 'wins', 'losses', 'open_trades',
            'win_rate_pct', 'up_trades', 'down_trades', 'neutral_trades',
            'avg_profit_loss_pct', 'max_profit_pct', 'min_profit_pct', 'stddev_profit_pct',
            'avg_win_pct', 'avg_loss_pct',
            'avg_bars_to_close', 'max_bars_to_close', 'min_bars_to_close',
            'first_trade', 'last_trade'
        ]

        stats = dict(zip(columns, row))
        stats['pair'] = pair
        stats['timeframe'] = timeframe

        return stats

    def get_monthly_performance(
        self,
        pair: str,
        timeframe: str
    ) -> pd.DataFrame:
        """
        Get performance grouped by month.

        Returns:
            DataFrame with monthly statistics
        """
        if not self.db.table_exists(pair, timeframe):
            return pd.DataFrame()

        table_name = self.db.get_table_name(pair, timeframe)

        query = f"""
            SELECT
                DATE_TRUNC('month', open_datetime) as month,
                COUNT(*) as trades,
                COUNT(CASE WHEN win = TRUE THEN 1 END) as wins,
                COUNT(CASE WHEN win = FALSE THEN 1 END) as losses,
                ROUND(100.0 * COUNT(CASE WHEN win = TRUE THEN 1 END) /
                      NULLIF(COUNT(*), 0), 2) as win_rate,
                ROUND(AVG(profit_loss_pct)::numeric, 2) as avg_pnl,
                ROUND(SUM(profit_loss_pct)::numeric, 2) as total_pnl
            FROM {table_name}
            WHERE win IS NOT NULL
            GROUP BY month
            ORDER BY month;
        """

        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn)

        return df

    def get_direction_performance(
        self,
        pair: str,
        timeframe: str
    ) -> pd.DataFrame:
        """
        Compare performance by trade direction.

        Returns:
            DataFrame with UP vs DOWN performance
        """
        if not self.db.table_exists(pair, timeframe):
            return pd.DataFrame()

        table_name = self.db.get_table_name(pair, timeframe)

        query = f"""
            SELECT
                direction,
                COUNT(*) as trades,
                COUNT(CASE WHEN win = TRUE THEN 1 END) as wins,
                COUNT(CASE WHEN win = FALSE THEN 1 END) as losses,
                ROUND(100.0 * COUNT(CASE WHEN win = TRUE THEN 1 END) /
                      NULLIF(COUNT(*), 0), 2) as win_rate,
                ROUND(AVG(profit_loss_pct)::numeric, 2) as avg_pnl,
                ROUND(SUM(profit_loss_pct)::numeric, 2) as total_pnl
            FROM {table_name}
            WHERE win IS NOT NULL
            GROUP BY direction
            ORDER BY direction;
        """

        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn)

        return df

    def get_outcome_distribution(
        self,
        pair: str,
        timeframe: str
    ) -> pd.DataFrame:
        """
        Get distribution of trade outcomes.

        Returns:
            DataFrame with outcome counts
        """
        if not self.db.table_exists(pair, timeframe):
            return pd.DataFrame()

        table_name = self.db.get_table_name(pair, timeframe)

        query = f"""
            SELECT
                outcome,
                COUNT(*) as count,
                ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
            FROM {table_name}
            GROUP BY outcome
            ORDER BY count DESC;
        """

        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn)

        return df

    # ==========================================
    # Custom Queries
    # ==========================================

    def execute_custom_query(
        self,
        pair: str,
        timeframe: str,
        query: str,
        params: Optional[Tuple] = None
    ) -> pd.DataFrame:
        """
        Execute custom SQL query.

        Args:
            pair: Currency pair
            timeframe: Timeframe
            query: SQL query (use {table} placeholder for table name)
            params: Query parameters

        Returns:
            DataFrame with results

        Example:
            query = "SELECT * FROM {table} WHERE profit_loss_pct > %s"
            df = qb.execute_custom_query("EURUSD", "H1", query, (2.0,))
        """
        if not self.db.table_exists(pair, timeframe):
            return pd.DataFrame()

        table_name = self.db.get_table_name(pair, timeframe)
        query = query.replace("{table}", table_name)

        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        return df

    def get_trades_with_complex_filter(
        self,
        pair: str,
        timeframe: str,
        sql_filter: str,
        params: Optional[Tuple] = None,
        order_by: str = "open_datetime",
        ascending: bool = True,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get trades with complex SQL WHERE clause.

        Args:
            pair: Currency pair
            timeframe: Timeframe
            sql_filter: SQL WHERE clause (without WHERE keyword)
            params: Parameters for filter
            order_by: Sort column
            ascending: Sort order
            limit: Row limit

        Returns:
            DataFrame with filtered trades

        Example:
            # Get profitable long trades from last month
            filter_sql = "direction = 'UP' AND win = TRUE AND open_datetime > %s"
            params = (datetime.now() - timedelta(days=30),)
            df = qb.get_trades_with_complex_filter("EURUSD", "H1", filter_sql, params)
        """
        if not self.db.table_exists(pair, timeframe):
            return pd.DataFrame()

        table_name = self.db.get_table_name(pair, timeframe)

        order = "ASC" if ascending else "DESC"
        query = f"SELECT * FROM {table_name} WHERE {sql_filter} ORDER BY {order_by} {order}"

        if limit:
            query += f" LIMIT {limit}"

        query += ";"

        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)

        # Deserialize JSON fields
        for col in ['all_levels', 'levels_map', 'warnings']:
            if col in df.columns:
                df[col] = df[col].apply(self.ops._deserialize_json_value)

        return df
