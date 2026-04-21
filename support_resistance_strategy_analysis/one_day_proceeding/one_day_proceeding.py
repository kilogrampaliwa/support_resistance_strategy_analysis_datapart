# one_day_proceeding/one_day_proceeding.py

#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.0
# Description: Main orchestrator for single-point trading analysis. Processes data up to a cutoff point, generates trade signals, and passes both historical and future data for validation.
#####################################################


import json
import pandas as pd
from typing import Dict, Any, Optional
from one_day_proceeding.levels_handler.levels_handler import LevelHandler #LevelsFinder  is used inside LevelHandler, so we import only the handler here
from one_day_proceeding.direction_guesser.direction_guesser import DirectionGuesser
from one_day_proceeding.trade_maker.trade_maker import tradeMaker
from one_day_proceeding.trade_finalizer.trade_finalizer import TradeFinalizer


class OneDayProceeding:
    """
    Main orchestrator for single-point trading analysis.
    Processes data up to a cutoff point, generates trade signals,
    and passes both historical and future data for validation.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        cutoff_datetime,  # Last point to analyze (e.g., last hour/day)
        timeframe: str = "H1",
        direction_method: str = "linear",
        level_finder_settings_path: str = "settings_json/level_finder_settings.json",
        trade_maker_settings_path: str = "settings_json/trade_maker_settings.json"
    ):
        """
        Args:
            df: Full dataset with columns [date, hour, open, high, low, close, w_avre]
            cutoff_datetime: Point where analysis stops (timestamp or index)
            timeframe: "H1" or "D1"
            direction_method: "linear", "quadratic", or "candle"
        """
        self.df_full = df.copy()
        self.cutoff_datetime = cutoff_datetime
        self.timeframe = timeframe
        self.direction_method = direction_method
        self.level_finder_settings_path = level_finder_settings_path
        self.trade_maker_settings_path = trade_maker_settings_path

        # Split data at cutoff point
        self.df_historical = self._split_historical()
        self.df_future = self._split_future()

        # Results storage
        self.levels = []
        self.direction = None
        self.trade_data = None

    def _split_historical(self) -> pd.DataFrame:
        """Returns data UP TO and INCLUDING cutoff_datetime."""
        return self.df_full.loc[:self.cutoff_datetime].copy()

    def _split_future(self) -> pd.DataFrame:
        """Returns data AFTER cutoff_datetime."""
        try:
            cutoff_pos = self.df_full.index.get_loc(self.cutoff_datetime)
            return self.df_full.iloc[cutoff_pos + 1:].copy()
        except KeyError:
            return pd.DataFrame()

    def run_analysis(self) -> Dict[str, Any]:
        """
        Runs the full analysis pipeline on historical data.
        Returns trade data ready for finalization.
        """
        if self.df_historical.empty:
            return {
                "error": "No historical data available",
                "cutoff_datetime": self.cutoff_datetime
            }

        self.levels = self._find_levels()
        self.direction = self._guess_direction()
        self.trade_data = self._make_trade()

        return self.trade_data

    def _find_levels(self) -> list:
        """Finds and filters support/resistance levels using LevelHandler."""
        if len(self.df_historical) < 50:
            return []

        handler = LevelHandler(
            json_params_path=self.level_finder_settings_path,
            levels_count=5,
            levels_diff_treshold=0.01
        )

        levels = handler.find_and_handle_levels(
            df=self.df_historical,
            timeframe=self.timeframe,
            previous_levels=[]
        )

        return levels

    def _guess_direction(self) -> str:
        """Predicts trend direction. Requires 'w_avre' column."""
        if len(self.df_historical) < 20:
            return "NEUTRAL"

        guesser = DirectionGuesser(
            method=self.direction_method,
            lookback=20
        )

        return guesser.detect_trend(self.df_historical)

    def _make_trade(self) -> Dict[str, Any]:
        """Generates trade parameters (TP, SL) from levels and direction."""
        if not self.levels:
            return {
                "error": "No levels found",
                "direction": self.direction,
                "cutoff_datetime": self.cutoff_datetime
            }

        last_row = self.df_historical.iloc[-1]
        last_price = float(last_row['close'])

        # Build timestamp from date+hour columns if available
        if 'date' in last_row.index and 'hour' in last_row.index:
            timestamp = f"{int(last_row['date'])}_{int(last_row['hour']):06d}"
        else:
            timestamp = str(self.cutoff_datetime)

        trade = tradeMaker(
            price=last_price,
            levels=self.levels,
            direction=self.direction,
            timestamp=timestamp,
            settings_path=self.trade_maker_settings_path
        )

        # Add context needed by TradeFinalizer
        trade['cutoff_datetime'] = self.cutoff_datetime
        trade['timeframe'] = self.timeframe
        trade['levels_count'] = len(self.levels)
        trade['all_levels'] = self.levels

        return trade

    def get_future_data(self) -> pd.DataFrame:
        """Returns future data for TradeFinalizer."""
        return self.df_future

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Returns a summary dict useful for debugging and logging."""
        return {
            "cutoff_datetime": self.cutoff_datetime,
            "timeframe": self.timeframe,
            "historical_rows": len(self.df_historical),
            "future_rows": len(self.df_future),
            "levels_found": len(self.levels),
            "direction": self.direction,
            "trade_valid": self.trade_data is not None and "error" not in self.trade_data
        }

    def _read_max_duration_seconds(self) -> Optional[int]:
        """
        Reads trade_maker.max_duration from trade_maker_settings.json and converts to seconds.
        Returns None if the key is missing (backward compatible).
        """
        unit_to_seconds = {
            "minutes": 60,
            "hours":   3600,
            "days":    86400,
            "weeks":   604800,
            "months":  2592000,
        }

        try:
            with open(self.trade_maker_settings_path, 'r') as f:
                settings = json.load(f)

            max_duration = settings.get("trade_maker", {}).get("max_duration", None)

            if max_duration is None:
                return None

            # Expect format: {"value": 3, "unit": "days"}
            value = max_duration.get("value")
            unit  = max_duration.get("unit")

            if value is None or unit is None:
                return None

            multiplier = unit_to_seconds.get(unit)
            if multiplier is None:
                return None

            return int(value) * multiplier

        except (FileNotFoundError, json.JSONDecodeError, AttributeError):
            return None

    def run_new_schema(self) -> Dict[str, Any]:
        """
        New-schema pipeline: detects 3 directions independently, always finalizes
        both LONG and SHORT trades using the same level-derived TP/SL.

        tradeMaker is always called with direction='UP' so that long_tp/long_sl
        and the mirrored short_tp/short_sl are all geometrically correct
        (avoids the DOWN-branch assignment quirk in tradeMaker).

        Returns a flat dict with:
            open_price, open_datetime, cutoff_datetime, timeframe,
            levels_count, long_tp, long_sl, short_tp, short_sl,
            linear_direction, logarithmic_direction, candle_direction,
            end_up   -> {"outcome", "close_price", "close_datetime", ...}
            end_down -> {"outcome", "close_price", "close_datetime", ...}
            max_duration_seconds
        """
        if self.df_historical.empty or len(self.df_historical) < 50:
            return {"error": "Not enough historical data"}

        # --- levels (same for all direction methods) ---
        levels = self._find_levels()
        if not levels:
            return {"error": "No levels found"}

        # --- 3 direction predictions ---
        linear_dir = DirectionGuesser(method="linear",    lookback=20).detect_trend(self.df_historical)
        quad_dir   = DirectionGuesser(method="quadratic", lookback=20).detect_trend(self.df_historical)
        candle_dir = DirectionGuesser(method="candle",    lookback=10).detect_trend(self.df_historical)

        # --- trade levels: always use UP so all 4 TP/SL values are correct ---
        last_row  = self.df_historical.iloc[-1]
        price     = float(last_row["close"])
        if "date" in last_row.index and "hour" in last_row.index:
            timestamp = f"{int(last_row['date'])}_{int(last_row['hour']):06d}"
        else:
            timestamp = str(self.cutoff_datetime)

        trade_data = tradeMaker(
            price=price,
            levels=levels,
            direction="UP",
            timestamp=timestamp,
            settings_path=self.trade_maker_settings_path,
        )
        trade_data["cutoff_datetime"] = self.cutoff_datetime
        trade_data["timeframe"]       = self.timeframe
        trade_data["levels_count"]    = len(levels)
        trade_data["all_levels"]      = levels

        # --- finalize both sides ---
        max_dur = self._read_max_duration_seconds()
        both    = TradeFinalizer(trade_data, self.df_future, max_dur).finalize_both()

        return {
            "open_price":             price,
            "open_datetime":          timestamp,
            "cutoff_datetime":        self.cutoff_datetime,
            "timeframe":              self.timeframe,
            "levels_count":           len(levels),
            "long_tp":                trade_data.get("long_tp"),
            "long_sl":                trade_data.get("long_sl"),
            "short_tp":               trade_data.get("short_tp"),
            "short_sl":               trade_data.get("short_sl"),
            "linear_direction":       linear_dir,
            "logarithmic_direction":  quad_dir,
            "candle_direction":       candle_dir,
            "end_up":                 both["long"],
            "end_down":               both["short"],
            "max_duration_seconds":   max_dur,
        }

    def run_all_methods(self) -> Dict[str, Any]:
        """
        Runs the full analysis pipeline for all 3 direction methods and finalizes each.
        Reads max_duration from trade_maker_settings.json and converts to seconds.

        Returns:
            Dict with keys 'linear', 'quadratic', 'candle', each containing
            the finalized trade result from TradeFinalizer.
        """
        # Read max_duration once from settings, convert to seconds
        max_duration_seconds = self._read_max_duration_seconds()

        results = {}

        for method in ['linear', 'quadratic', 'candle']:
            self.direction_method = method
            trade_data = self.run_analysis()
            finalizer = TradeFinalizer(
                trade_data=trade_data,
                future_df=self.df_future,
                max_duration_seconds=max_duration_seconds
            )
            finalized = finalizer.finalize()
            finalized["max_duration_seconds"] = max_duration_seconds
            results[method] = finalized
        return results