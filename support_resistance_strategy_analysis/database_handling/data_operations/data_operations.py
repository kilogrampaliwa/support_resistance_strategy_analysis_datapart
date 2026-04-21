# database_handling/data_operations/data_operations.py

#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 13.03.2026
# Version: 1.0
# Description: Database cleaning utilities for TradingDatabase compatibility
#####################################################

"""
Data Operations Module

Handles inserting, querying, updating, and deleting trade analysis data.
Integrates with pandas for efficient bulk operations.
"""

import psycopg2
from psycopg2 import extras
import pandas as pd
from typing import List, Dict, Any, Optional, Union
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DataOperations:
    """
    Handles data operations for trade analysis results.
    
    Works with DatabaseManager to perform CRUD operations
    and integrates seamlessly with pandas DataFrames.
    """
    
    def __init__(self, db_manager):
        """
        Initialize with a DatabaseManager instance.
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager
    
    def insert_trade(
        self,
        pair: str,
        timeframe: str,
        trade_data: Dict[str, Any],
        ensure_table: bool = True,
        # --- per-method linear fields ---
        lin_tp_long: Optional[float] = None,
        lin_sl_long: Optional[float] = None,
        lin_tp_short: Optional[float] = None,
        lin_sl_short: Optional[float] = None,
        lin_close_date: Optional[Any] = None,
        # --- per-method quadratic fields ---
        quad_tp_long: Optional[float] = None,
        quad_sl_long: Optional[float] = None,
        quad_tp_short: Optional[float] = None,
        quad_sl_short: Optional[float] = None,
        quad_close_date: Optional[Any] = None,
        # --- per-method candle fields ---
        cnd_tp_long: Optional[float] = None,
        cnd_sl_long: Optional[float] = None,
        cnd_tp_short: Optional[float] = None,
        cnd_sl_short: Optional[float] = None,
        cnd_close_date: Optional[Any] = None,
        # --- global duration cap ---
        max_duration: Optional[int] = None,
    ) -> bool:
        """
        Insert single trade analysis result.

        New per-method kwargs map to SQL columns with the same name:
            lin_tp_long, lin_sl_long, lin_tp_short, lin_sl_short, lin_close_date
            quad_tp_long, quad_sl_long, quad_tp_short, quad_sl_short, quad_close_date
            cnd_tp_long, cnd_sl_long, cnd_tp_short, cnd_sl_short, cnd_close_date
            max_duration  (INTEGER seconds)

        All new kwargs default to None so existing call sites are unaffected.

        Args:
            pair: Currency pair
            timeframe: Timeframe
            trade_data: Trade data dictionary (from OneDayOutput.to_row())
            ensure_table: Create table if doesn't exist
            lin_*: Linear-method TP/SL/close columns
            quad_*: Quadratic-method TP/SL/close columns
            cnd_*: Candle-method TP/SL/close columns
            max_duration: Maximum trade duration in seconds

        Returns:
            True if inserted, False if failed
        """
        if ensure_table:
            self.db.ensure_table_exists(pair, timeframe)
        
        table_name = self.db.get_table_name(pair, timeframe)
        
        # Merge per-method fields into trade_data copy (only non-None values)
        extra_fields = {
            'lin_tp_long':    lin_tp_long,
            'lin_sl_long':    lin_sl_long,
            'lin_tp_short':   lin_tp_short,
            'lin_sl_short':   lin_sl_short,
            'lin_close_date': lin_close_date,
            'quad_tp_long':   quad_tp_long,
            'quad_sl_long':   quad_sl_long,
            'quad_tp_short':  quad_tp_short,
            'quad_sl_short':  quad_sl_short,
            'quad_close_date': quad_close_date,
            'cnd_tp_long':    cnd_tp_long,
            'cnd_sl_long':    cnd_sl_long,
            'cnd_tp_short':   cnd_tp_short,
            'cnd_sl_short':   cnd_sl_short,
            'cnd_close_date': cnd_close_date,
            'max_duration':   max_duration,
        }

        # Start from a copy so we don't mutate the caller's dict
        merged = dict(trade_data)
        for col, val in extra_fields.items():
            if val is not None:
                merged[col] = val

        # Serialize JSON fields
        merged = self._serialize_json_fields(merged)
        
        # Build INSERT query dynamically from merged keys
        columns = list(merged.keys())
        placeholders = ["%s"] * len(columns)
        
        query = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            ON CONFLICT (trade_id) DO NOTHING;
        """
        
        values = [merged[col] for col in columns]
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, values)
                cursor.close()
            
            logger.info(f"Inserted trade {merged.get('trade_id')} into {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert trade: {e}")
            return False

    def insert_trades_bulk(
        self,
        pair: str,
        timeframe: str,
        trades: Union[List[Dict[str, Any]], pd.DataFrame],
        ensure_table: bool = True,
        overwrite: bool = True
    ) -> int:
        """
        Insert multiple trades efficiently using bulk insert.
        If overwrite=True, delete all existing trades before inserting.
    
        Args:
            pair: Currency pair
            timeframe: Timeframe
            trades: List of trade dicts or DataFrame
            ensure_table: Create table if doesn't exist
            overwrite: If True, remove all existing trades before insert
    
        Returns:
            Number of trades inserted
        """
        if ensure_table:
            self.db.ensure_table_exists(pair, timeframe)
    
        table_name = self.db.get_table_name(pair, timeframe)
    
        # Remove all existing records when overwriting
        if overwrite:
            self.delete_trades(pair, timeframe, filters={})
            logger.info(f"All existing trades in {table_name} deleted before insert.")
    
        # Convert DataFrame to list of dicts if needed
        if isinstance(trades, pd.DataFrame):
            trades = trades.to_dict('records')
    
        if not trades:
            logger.warning("No trades to insert")
            return 0
    
        # Serialize JSON fields for every row
        trades = [self._serialize_json_fields(trade) for trade in trades]
    
        columns = list(trades[0].keys())
        query = f"""
            INSERT INTO {table_name} ({', '.join(columns)})
            VALUES %s
            ON CONFLICT (trade_id) DO NOTHING;
        """
    
        values = [[trade[col] for col in columns] for trade in trades]
    
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                extras.execute_values(cursor, query, values)
                inserted = cursor.rowcount
                cursor.close()
    
            logger.info(f"Inserted {inserted} trades into {table_name}")
            return inserted
    
        except Exception as e:
            logger.error(f"Failed to bulk insert trades: {e}")
            return 0
    
    def trade_exists(self, pair: str, timeframe: str, trade_id: str) -> bool:
        """
        Check if trade with given ID exists.
        
        Args:
            pair: Currency pair
            timeframe: Timeframe
            trade_id: Trade ID to check
        
        Returns:
            True if exists, False otherwise
        """
        if not self.db.table_exists(pair, timeframe):
            return False
        
        table_name = self.db.get_table_name(pair, timeframe)
        
        query = f"SELECT EXISTS(SELECT 1 FROM {table_name} WHERE trade_id = %s);"
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (trade_id,))
            exists = cursor.fetchone()[0]
            cursor.close()
        
        return exists
    
    def get_trade(self, pair: str, timeframe: str, trade_id: str) -> Optional[Dict[str, Any]]:
        """
        Get single trade by ID.
        
        Args:
            pair: Currency pair
            timeframe: Timeframe
            trade_id: Trade ID
        
        Returns:
            Trade data dict or None if not found
        """
        if not self.db.table_exists(pair, timeframe):
            return None
        
        table_name = self.db.get_table_name(pair, timeframe)
        
        query = f"SELECT * FROM {table_name} WHERE trade_id = %s;"
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=extras.RealDictCursor)
            cursor.execute(query, (trade_id,))
            result = cursor.fetchone()
            cursor.close()
        
        if result:
            return self._deserialize_json_fields(dict(result))
        return None
    
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
        """
        Get trades with optional filtering and sorting.
        
        Args:
            pair: Currency pair
            timeframe: Timeframe
            filters: Dictionary of column:value filters
            order_by: Column to sort by
            ascending: Sort order (True = ASC, False = DESC)
            limit: Maximum number of rows
            offset: Number of rows to skip
        
        Returns:
            DataFrame with trade data
        
        Example:
            # Get winning trades
            df = ops.get_trades("EURUSD", "H1", filters={"win": True})
            
            # Get recent trades
            df = ops.get_trades("EURUSD", "H1", order_by="open_datetime", 
                               ascending=False, limit=100)
        """
        if not self.db.table_exists(pair, timeframe):
            return pd.DataFrame()
        
        table_name = self.db.get_table_name(pair, timeframe)
        
        # Build query
        query = f"SELECT * FROM {table_name}"
        params = []
        
        # Add filters
        if filters:
            conditions = []
            for col, value in filters.items():
                conditions.append(f"{col} = %s")
                params.append(value)
            query += " WHERE " + " AND ".join(conditions)
        
        # Add sorting
        order = "ASC" if ascending else "DESC"
        query += f" ORDER BY {order_by} {order}"
        
        # Add pagination
        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"
        
        query += ";"
        
        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params if params else None)
        
        # Deserialize JSON fields
        for col in ['all_levels', 'levels_map', 'warnings']:
            if col in df.columns:
                df[col] = df[col].apply(self._deserialize_json_value)
        
        return df
    
    def get_trades_by_date_range(
        self,
        pair: str,
        timeframe: str,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        **kwargs
    ) -> pd.DataFrame:
        """
        Get trades within date range.
        
        Args:
            pair: Currency pair
            timeframe: Timeframe
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            **kwargs: Additional arguments for get_trades()
        
        Returns:
            DataFrame with trades in date range
        """
        if not self.db.table_exists(pair, timeframe):
            return pd.DataFrame()
        
        table_name = self.db.get_table_name(pair, timeframe)
        
        query = f"""
            SELECT * FROM {table_name}
            WHERE open_datetime BETWEEN %s AND %s
            ORDER BY open_datetime;
        """
        
        with self.db.get_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        
        # Deserialize JSON fields
        for col in ['all_levels', 'levels_map', 'warnings']:
            if col in df.columns:
                df[col] = df[col].apply(self._deserialize_json_value)
        
        return df
    
    def delete_trade(self, pair: str, timeframe: str, trade_id: str) -> bool:
        """
        Delete single trade.
        
        Args:
            pair: Currency pair
            timeframe: Timeframe
            trade_id: Trade ID to delete
        
        Returns:
            True if deleted, False if not found
        """
        if not self.db.table_exists(pair, timeframe):
            return False
        
        table_name = self.db.get_table_name(pair, timeframe)
        
        query = f"DELETE FROM {table_name} WHERE trade_id = %s;"
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (trade_id,))
            deleted = cursor.rowcount
            cursor.close()
        
        return deleted > 0
    
    def delete_trades(
        self,
        pair: str,
        timeframe: str,
        filters: Dict[str, Any]
    ) -> int:
        """
        Delete multiple trades matching filters.
        Passing an empty filters={} removes all rows in the table.
        
        Args:
            pair: Currency pair
            timeframe: Timeframe
            filters: Dictionary of column:value filters
        
        Returns:
            Number of trades deleted
        """
        if not self.db.table_exists(pair, timeframe):
            return 0
        
        table_name = self.db.get_table_name(pair, timeframe)
        
        # Build WHERE clause; empty filters → delete all rows
        conditions = []
        params = []
        for col, value in filters.items():
            conditions.append(f"{col} = %s")
            params.append(value)
        
        if conditions:
            query = f"DELETE FROM {table_name} WHERE " + " AND ".join(conditions) + ";"
        else:
            query = f"DELETE FROM {table_name};"
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            deleted = cursor.rowcount
            cursor.close()
        
        logger.info(f"Deleted {deleted} trades from {table_name}")
        return deleted
    
    def update_trade(
        self,
        pair: str,
        timeframe: str,
        trade_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update trade fields.
        
        Args:
            pair: Currency pair
            timeframe: Timeframe
            trade_id: Trade ID
            updates: Dictionary of column:value updates
        
        Returns:
            True if updated, False if not found
        """
        if not self.db.table_exists(pair, timeframe):
            return False
        
        table_name = self.db.get_table_name(pair, timeframe)
        
        # Serialize JSON fields
        updates = self._serialize_json_fields(updates)
        
        # Build SET clause
        set_clauses = []
        params = []
        for col, value in updates.items():
            set_clauses.append(f"{col} = %s")
            params.append(value)
        
        params.append(trade_id)
        
        query = f"UPDATE {table_name} SET " + ", ".join(set_clauses) + " WHERE trade_id = %s;"
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            updated = cursor.rowcount
            cursor.close()
        
        return updated > 0
    
    # ------------------------------------------------------------------ #
    # Helper methods
    # ------------------------------------------------------------------ #

    def _serialize_json_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert list/dict fields to JSON strings."""
        json_fields = ['all_levels', 'levels_map', 'warnings']
        result = data.copy()
        
        for field in json_fields:
            if field in result and result[field] is not None:
                if isinstance(result[field], (list, dict)):
                    result[field] = json.dumps(result[field])
        
        return result
    
    def _deserialize_json_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert JSON strings back to list/dict."""
        json_fields = ['all_levels', 'levels_map', 'warnings']
        result = data.copy()
        
        for field in json_fields:
            if field in result and result[field] is not None:
                if isinstance(result[field], str):
                    try:
                        result[field] = json.loads(result[field])
                    except json.JSONDecodeError:
                        pass
        
        return result
    
    def _deserialize_json_value(self, value):
        """Deserialize single JSON value (for pandas apply)."""
        if value is None or not isinstance(value, str):
            return value
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value