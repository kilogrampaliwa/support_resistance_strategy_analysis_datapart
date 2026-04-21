# one_day_proceeding/trade_finalizer/trade_finalizer.py


#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.1
# Description: This module provides the TradeFinalizer class, which validates trade outcomes by checking if TP or SL was hit in future data. It tracks the exact datetime when TP/SL occurred and handles various edge cases such as missing future data or invalid trade parameters. Supports max_duration_seconds to cap how far into the future the scan runs.
#####################################################


import pandas as pd
from typing import Dict, Any, Optional, Tuple


class TradeFinalizer:
    """
    Validates trade outcomes by checking if TP or SL was hit in future data.
    Tracks the exact datetime when TP/SL occurred.
    Optionally limits the scan window via max_duration_seconds.
    """
    
    def __init__(
        self,
        trade_data: Dict[str, Any],
        future_df: pd.DataFrame,
        max_duration_seconds: Optional[int] = None
    ):
        """
        Args:
            trade_data: Output from TradeMaker (step E)
            future_df: Price data after cutoff_datetime
            max_duration_seconds: If set, scan is limited to this many seconds
                                  after the trade open_datetime. None = no limit.
        """
        self.trade_data = trade_data.copy()
        self.future_df = future_df.copy()
        self.max_duration_seconds = max_duration_seconds
        self.result = None
        
    def finalize(self) -> Dict[str, Any]:
        """
        Main method: checks trade outcome and adds finalization data.
        Returns enriched trade_data with outcome information.
        """
        if self.future_df.empty:
            return self._no_future_data()
        
        if "error" in self.trade_data or self.trade_data.get("direction") == "NEUTRAL":
            return self._invalid_trade()
        
        direction = self.trade_data["direction"].upper()
        
        if direction == "UP":
            self.result = self._check_long_trade()
        elif direction == "DOWN":
            self.result = self._check_short_trade()
        else:
            return self._invalid_trade()
        
        # Merge result with original trade_data
        finalized = self.trade_data.copy()
        finalized.update(self.result)
        
        return finalized
    
    def _get_clipped_future_df(self) -> pd.DataFrame:
        """
        Returns future_df clipped to max_duration_seconds after open_datetime.
        If max_duration_seconds is None, returns future_df unchanged.
        """
        if self.max_duration_seconds is None:
            return self.future_df
        
        open_dt_str = self.trade_data.get("open_datetime", "")
        open_dt = pd.to_datetime(open_dt_str, format='%Y%m%d_%H%M%S')
        deadline = open_dt + pd.Timedelta(seconds=self.max_duration_seconds)
        
        clipped = self.future_df[self.future_df.index <= deadline]
        return clipped

    def _check_long_trade(self) -> Dict[str, Any]:
        """
        Checks LONG position: TP is above entry, SL is below entry.
        """
        tp = self.trade_data.get("long_tp")
        sl = self.trade_data.get("long_sl")
        entry = self.trade_data.get("open_price")
        
        if tp is None or sl is None:
            return {
                "outcome": "INVALID",
                "reason": "Missing TP or SL for LONG",
                "tp_datetime": None,
                "sl_datetime": None,
                "close_datetime": None,
                "close_price": None,
                "bars_to_close": None
            }
        
        return self._scan_future_data(entry, tp, sl, "LONG")
    
    def _check_short_trade(self) -> Dict[str, Any]:
        """
        Checks SHORT position: TP is below entry, SL is above entry.
        """
        tp = self.trade_data.get("short_tp")
        sl = self.trade_data.get("short_sl")
        entry = self.trade_data.get("open_price")
        
        if tp is None or sl is None:
            return {
                "outcome": "INVALID",
                "reason": "Missing TP or SL for SHORT",
                "tp_datetime": None,
                "sl_datetime": None,
                "close_datetime": None,
                "close_price": None,
                "bars_to_close": None
            }
        
        return self._scan_future_data(entry, tp, sl, "SHORT")
    
    def _scan_future_data(
        self, 
        entry: float, 
        tp: float, 
        sl: float, 
        position_type: str
    ) -> Dict[str, Any]:
        """
        Scans future candles to find first TP or SL hit.
        If max_duration_seconds is set, the scan is limited to that window.
        If the window expires without a hit, outcome is MAX_DURATION.

        For LONG: TP hit when high >= tp, SL hit when low <= sl
        For SHORT: TP hit when low <= tp, SL hit when high >= sl
        """
        # Clip future data to duration limit if configured
        scan_df = self._get_clipped_future_df()
        duration_limited = (self.max_duration_seconds is not None)

        tp_hit_datetime = None
        sl_hit_datetime = None
        outcome = "OPEN"  # Default if neither hit
        close_datetime = None
        close_price = None
        bars_to_close = None
        
        for idx, (timestamp, row) in enumerate(scan_df.iterrows(), start=1):
            high = row['high']
            low = row['low']
            close = row['close']
            
            if position_type == "LONG":
                # Check if TP hit first (high reached TP level)
                tp_reached = high >= tp
                # Check if SL hit first (low reached SL level)
                sl_reached = low <= sl
                
            else:  # SHORT
                # Check if TP hit first (low reached TP level)
                tp_reached = low <= tp
                # Check if SL hit first (high reached SL level)
                sl_reached = high >= sl
            
            # Determine which was hit first (if both in same candle, prioritize SL)
            if sl_reached and tp_reached:
                # Both hit in same bar — conservative: assume SL hit first (worst case)
                outcome = "STOP_LOSS"
                sl_hit_datetime = timestamp
                close_datetime = timestamp
                close_price = sl
                bars_to_close = idx
                break
                
            elif tp_reached:
                outcome = "TAKE_PROFIT"
                tp_hit_datetime = timestamp
                close_datetime = timestamp
                close_price = tp
                bars_to_close = idx
                break
                
            elif sl_reached:
                outcome = "STOP_LOSS"
                sl_hit_datetime = timestamp
                close_datetime = timestamp
                close_price = sl
                bars_to_close = idx
                break
        
        # Loop completed without a TP/SL hit
        if outcome == "OPEN":
            if duration_limited and not scan_df.empty:
                # Trade ran out of allowed time — close at last bar in window
                last_timestamp = scan_df.index[-1]
                last_close = scan_df.iloc[-1]['close']
                outcome = "MAX_DURATION"
                close_datetime = last_timestamp
                close_price = float(last_close)
                bars_to_close = len(scan_df)
            else:
                # No duration limit: trade remains open
                bars_to_close = len(self.future_df)
                close_datetime = None
                close_price = None
        
        return {
            "outcome": outcome,
            "tp_datetime": str(tp_hit_datetime) if tp_hit_datetime else None,
            "sl_datetime": str(sl_hit_datetime) if sl_hit_datetime else None,
            "close_datetime": str(close_datetime) if close_datetime else None,
            "close_price": float(close_price) if close_price is not None else None,
            "bars_to_close": bars_to_close,
            "future_bars_scanned": len(self.future_df)
        }
    
    def finalize_both(self) -> Dict[str, Dict[str, Any]]:
        """
        Always finalizes BOTH LONG and SHORT directions, regardless of trade direction field.
        Used by the new schema pipeline where both sides are always evaluated.

        Returns:
            {"long": long_result_dict, "short": short_result_dict}
            Each result contains: outcome, close_price, close_datetime, bars_to_close,
            tp_datetime, sl_datetime, future_bars_scanned.
        """
        _empty = {
            "outcome": "NO_FUTURE_DATA",
            "tp_datetime": None,
            "sl_datetime": None,
            "close_datetime": None,
            "close_price": None,
            "bars_to_close": None,
            "future_bars_scanned": 0,
        }
        if self.future_df.empty:
            return {"long": _empty.copy(), "short": _empty.copy()}

        if "error" in self.trade_data:
            _inv = {**_empty, "outcome": "INVALID"}
            return {"long": _inv.copy(), "short": _inv.copy()}

        return {
            "long":  self._check_long_trade(),
            "short": self._check_short_trade(),
        }

    def _no_future_data(self) -> Dict[str, Any]:
        """
        Returns result when no future data is available.
        """
        result = self.trade_data.copy()
        result.update({
            "outcome": "NO_FUTURE_DATA",
            "tp_datetime": None,
            "sl_datetime": None,
            "close_datetime": None,
            "close_price": None,
            "bars_to_close": None,
            "future_bars_scanned": 0
        })
        return result
    
    def _invalid_trade(self) -> Dict[str, Any]:
        """
        Returns result for invalid trades (errors, NEUTRAL direction, etc).
        """
        result = self.trade_data.copy()
        result.update({
            "outcome": "INVALID",
            "tp_datetime": None,
            "sl_datetime": None,
            "close_datetime": None,
            "close_price": None,
            "bars_to_close": None,
            "future_bars_scanned": 0
        })
        return result


# Example usage:
if __name__ == "__main__":
    # Mock trade data from TradeMaker
    trade_data = {
        "open_price": 0.56190,
        "direction": "UP",
        "open_datetime": "20010103_000000",
        "long_tp": 0.57000,
        "long_sl": 0.55500,
        "short_tp": 0.55500,
        "short_sl": 0.57000,
        "levels_map": {1: 0.57000, -1: 0.55500},
        "cutoff_datetime": "2001-01-03 00:00:00"
    }
    
    # Mock future data
    future_data = pd.DataFrame({
        'open': [0.56200, 0.56500, 0.56800],
        'high': [0.56500, 0.56900, 0.57100],
        'low': [0.56100, 0.56400, 0.56700],
        'close': [0.56400, 0.56800, 0.57000],
        'w_avre': [0.56300, 0.56650, 0.56900]
    }, index=pd.date_range('2001-01-04', periods=3, freq='h'))
    
    # Finalize trade — no duration limit
    finalizer = TradeFinalizer(trade_data, future_data)
    result = finalizer.finalize()
    print("=== No duration limit ===")
    print("Trade outcome:", result['outcome'])
    print("Close datetime:", result['close_datetime'])
    print("Close price:", result['close_price'])
    print("Bars to close:", result['bars_to_close'])

    # Finalize trade — duration limit of 1 hour (3600 seconds), only first bar allowed
    finalizer_ltd = TradeFinalizer(trade_data, future_data, max_duration_seconds=3600)
    result_ltd = finalizer_ltd.finalize()
    print("\n=== 1-hour duration limit ===")
    print("Trade outcome:", result_ltd['outcome'])
    print("Close datetime:", result_ltd['close_datetime'])
    print("Close price:", result_ltd['close_price'])
    print("Bars to close:", result_ltd['bars_to_close'])