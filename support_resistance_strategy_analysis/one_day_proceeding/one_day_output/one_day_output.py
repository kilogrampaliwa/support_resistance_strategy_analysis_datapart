# one_day_proceeding/one_day_output/one_day_output.py


#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.2
# Description: Converts finalized trade data into database-ready row format.
#              v1.1: Added from_all_methods() classmethod for 3-method combined row.
#              v1.2: from_all_methods() reads max_duration_seconds from results dict.
#####################################################


import pandas as pd
from typing import Dict, Any, Optional, List
import json


class OneDayOutput:
    """
    Converts finalized trade data into database-ready row format.
    Combines information from TradeMaker (E) and TradeFinalizer (F).
    
    NEW: Tracks source of TP/SL levels (level/nearest/percent) for analysis.
    NEW v1.1: from_all_methods() classmethod flattens 3-method results into one DB row.
    NEW v1.2: from_all_methods() reads max_duration_seconds internally from results dict.
    """
    
    def __init__(self, finalized_data: Dict[str, Any]):
        """
        Args:
            finalized_data: Complete trade data after finalization (from step F)
                           MUST contain 'pair' field for unique trade_id generation
        """
        self.data = finalized_data
        self.row = None
        
    def to_row(self) -> Dict[str, Any]:
        """
        Converts trade data into single database row.
        Returns dict with all relevant fields for SQL/React storage.
        
        NEW FIELDS: tp_source, sl_source
        """
        self.row = {
            # Trade identification
            "trade_id": self._generate_trade_id(),
            "timeframe": self.data.get("timeframe", "UNKNOWN"),
            
            # Entry information
            "open_datetime": self.data.get("open_datetime"),
            "open_price": self.data.get("open_price"),
            "direction": self.data.get("direction"),
            
            # Trade parameters - LONG
            "long_tp": self.data.get("long_tp"),
            "long_sl": self.data.get("long_sl"),
            
            # Trade parameters - SHORT
            "short_tp": self.data.get("short_tp"),
            "short_sl": self.data.get("short_sl"),
            
            # Levels information
            "tp_level_index": self.data.get("levels_used", {}).get("tp_index"),
            "sl_level_index": self.data.get("levels_used", {}).get("sl_index"),
            "tp_level_value": self.data.get("levels_used", {}).get("tp_level"),
            "sl_level_value": self.data.get("levels_used", {}).get("sl_level"),
            "tp_source": self.data.get("levels_used", {}).get("tp_source"),  # NEW
            "sl_source": self.data.get("levels_used", {}).get("sl_source"),  # NEW
            "levels_count": self.data.get("levels_count", 0),
            "all_levels": self._serialize_levels(),
            "levels_map": self._serialize_levels_map(),
            
            # Trade outcome
            "outcome": self.data.get("outcome", "UNKNOWN"),
            "close_datetime": self.data.get("close_datetime"),
            "close_price": self.data.get("close_price"),
            "bars_to_close": self.data.get("bars_to_close"),
            
            # Timing information
            "tp_hit_datetime": self.data.get("tp_datetime"),
            "sl_hit_datetime": self.data.get("sl_datetime"),
            
            # Performance metrics
            "profit_loss_pct": self._calculate_pl_percentage(),
            "profit_loss_points": self._calculate_pl_points(),
            "win": self._is_winning_trade(),
            
            # Additional context
            "warnings": self._serialize_warnings(),
            "future_bars_scanned": self.data.get("future_bars_scanned", 0),
            "cutoff_datetime": self.data.get("cutoff_datetime"),
            
            # Metadata
            "created_at": pd.Timestamp.now().isoformat()
        }
        
        return self.row

    @classmethod
    def from_all_methods(
        cls,
        results: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Flattens finalized results from all 3 direction methods into one DB row.

        Args:
            results: Dict with keys 'linear', 'quadratic', 'candle' — each a
                     finalized trade dict (output of TradeFinalizer.finalize()).
                     max_duration_seconds is read from results['linear'] if stored there.

        Returns:
            Flat dict ready for a single database row.

        Per-method fields are prefixed:
            lin_  — linear regression method
            quad_ — quadratic regression method
            cnd_  — candle pattern method

        Prefixed fields per method:
            {prefix}tp_long, {prefix}sl_long,
            {prefix}tp_short, {prefix}sl_short,
            {prefix}close_date, {prefix}outcome, {prefix}bars_to_close

        Shared fields (taken from 'linear' result):
            open_price, open_datetime, direction,
            timeframe, levels_count
        """
        # Method → column prefix mapping
        prefix_map = {
            "linear":    "lin_",
            "quadratic": "quad_",
            "candle":    "cnd_",
        }

        # Shared fields come from the linear result (all methods share same entry point)
        base = results.get("linear", {})

        # Read max_duration_seconds from the linear result dict; None if not stored
        max_duration_seconds = base.get("max_duration_seconds", None)
        # Ensure it is stored as integer seconds if present
        if max_duration_seconds is not None:
            max_duration_seconds = int(max_duration_seconds)

        row: Dict[str, Any] = {
            # --- Shared entry fields ---
            "open_price":           base.get("open_price"),
            "open_datetime":        base.get("open_datetime"),
            "direction":            base.get("direction"),
            "timeframe":            base.get("timeframe", "UNKNOWN"),
            "levels_count":         base.get("levels_count", 0),

            # --- Configuration (integer seconds or None) ---
            "max_duration_seconds": max_duration_seconds,

            # --- Metadata ---
            "created_at": pd.Timestamp.now().isoformat(),
        }

        # Inject per-method prefixed fields
        for method, prefix in prefix_map.items():
            result = results.get(method, {})
            row[f"{prefix}tp_long"]       = result.get("long_tp")
            row[f"{prefix}sl_long"]       = result.get("long_sl")
            row[f"{prefix}tp_short"]      = result.get("short_tp")
            row[f"{prefix}sl_short"]      = result.get("short_sl")
            row[f"{prefix}close_date"]    = result.get("close_datetime")
            row[f"{prefix}outcome"]       = result.get("outcome", "UNKNOWN")
            row[f"{prefix}bars_to_close"] = result.get("bars_to_close")

        return row
    
    @classmethod
    def to_new_schema_row(
        cls,
        result: Dict[str, Any],
        ticker: str,
        timeframe: str,
    ) -> Dict[str, Any]:
        """
        Converts run_new_schema() output into a flat DB row for the new schema tables.

        New schema tables are named {ticker_lower}_{timeframe_lower}
        (e.g. eurusd_1h) and hold one row per analysed candle.

        Args:
            result:    dict returned by OneDayProceeding.run_new_schema()
            ticker:    currency pair string,  e.g. "EURUSD"
            timeframe: display timeframe string, e.g. "1H"

        Returns:
            Flat dict ready for direct psycopg2 insertion.
            Returns None when result contains an "error" key.
        """
        if "error" in result:
            return None

        end_up   = result.get("end_up",   {}) or {}
        end_down = result.get("end_down", {}) or {}

        return {
            "ticker":                  ticker.upper(),
            "timeframe":               timeframe.upper(),
            "full_date_open":          result.get("open_datetime"),
            # direction signals
            "linear_direction":        result.get("linear_direction"),
            "logarithmic_direction":   result.get("logarithmic_direction"),
            "candle_direction":        result.get("candle_direction"),
            # level-derived TP/SL (same for all direction methods)
            "long_tp":                 result.get("long_tp"),
            "long_sl":                 result.get("long_sl"),
            "short_tp":                result.get("short_tp"),
            "short_sl":                result.get("short_sl"),
            # UP trade (LONG)
            "end_up_reason":           end_up.get("outcome"),
            "end_up_close_price":      end_up.get("close_price"),
            "end_up_close_date":       end_up.get("close_datetime"),
            # DOWN trade (SHORT)
            "end_down_reason":         end_down.get("outcome"),
            "end_down_close_price":    end_down.get("close_price"),
            "end_down_close_date":     end_down.get("close_datetime"),
        }

    def _generate_trade_id(self) -> str:
        """
        Creates unique trade identifier INCLUDING PAIR for uniqueness.
        Format: {pair}_{open_datetime}_{direction}_{timeframe}
        """
        pair = self.data.get("pair", "UNKNOWN")
        open_dt = self.data.get("open_datetime", "UNKNOWN")
        direction = self.data.get("direction", "NEUTRAL")
        timeframe = self.data.get("timeframe", "UNKNOWN")
        return f"{pair}_{open_dt}_{direction}_{timeframe}"
    
    def _serialize_levels(self) -> Optional[str]:
        """Serializes all_levels list to JSON string for database storage."""
        levels = self.data.get("all_levels", [])
        if not levels:
            return None
        return json.dumps(levels)
    
    def _serialize_levels_map(self) -> Optional[str]:
        """Serializes levels_map dict to JSON string."""
        levels_map = self.data.get("levels_map", {})
        if not levels_map:
            return None
        serializable_map = {str(k): v for k, v in levels_map.items()}
        return json.dumps(serializable_map)
    
    def _serialize_warnings(self) -> Optional[str]:
        """Serializes warnings list to JSON string."""
        warnings = self.data.get("warnings", [])
        if not warnings:
            return None
        return json.dumps(warnings)
    
    def _calculate_pl_percentage(self) -> Optional[float]:
        """Calculates profit/loss percentage based on outcome."""
        outcome = self.data.get("outcome")
        if outcome not in ["TAKE_PROFIT", "STOP_LOSS"]:
            return None
        
        open_price = self.data.get("open_price")
        close_price = self.data.get("close_price")
        direction = self.data.get("direction", "").upper()
        
        if not all([open_price, close_price, direction]):
            return None
        
        if direction == "UP":
            pl_pct = ((close_price - open_price) / open_price) * 100
        elif direction == "DOWN":
            pl_pct = ((open_price - close_price) / open_price) * 100
        else:
            return None
        
        return round(pl_pct, 4)
    
    def _calculate_pl_points(self) -> Optional[float]:
        """Calculates profit/loss in price points."""
        outcome = self.data.get("outcome")
        if outcome not in ["TAKE_PROFIT", "STOP_LOSS"]:
            return None
        
        open_price = self.data.get("open_price")
        close_price = self.data.get("close_price")
        direction = self.data.get("direction", "").upper()
        
        if not all([open_price, close_price, direction]):
            return None
        
        if direction == "UP":
            pl_points = close_price - open_price
        elif direction == "DOWN":
            pl_points = open_price - close_price
        else:
            return None
        
        return round(pl_points, 6)
    
    def _is_winning_trade(self) -> Optional[bool]:
        """Determines if trade was a win (TP hit) or loss (SL hit)."""
        outcome = self.data.get("outcome")
        if outcome == "TAKE_PROFIT":
            return True
        elif outcome == "STOP_LOSS":
            return False
        else:
            return None
    
    def to_dataframe(self) -> pd.DataFrame:
        """Converts row to single-row DataFrame for easy CSV/SQL export."""
        if self.row is None:
            self.to_row()
        return pd.DataFrame([self.row])
    
    def to_sql_insert(self, table_name: str = "trades") -> str:
        """Generates SQL INSERT statement for the trade."""
        if self.row is None:
            self.to_row()
        
        columns = ", ".join(self.row.keys())
        placeholders = ", ".join(["%s"] * len(self.row))
        
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders});"
        return sql
    
    def get_summary(self) -> Dict[str, Any]:
        """Returns human-readable summary of the trade."""
        if self.row is None:
            self.to_row()
        
        return {
            "Trade ID": self.row["trade_id"],
            "Direction": self.row["direction"],
            "Entry": f"{self.row['open_price']} @ {self.row['open_datetime']}",
            "TP": f"{self.row.get('tp_level_value')} ({self.row.get('tp_source')})",
            "SL": f"{self.row.get('sl_level_value')} ({self.row.get('sl_source')})",
            "Outcome": self.row["outcome"],
            "Close": f"{self.row['close_price']} @ {self.row['close_datetime']}" if self.row['close_price'] else "OPEN",
            "P/L %": self.row["profit_loss_pct"],
            "Win": self.row["win"]
        }