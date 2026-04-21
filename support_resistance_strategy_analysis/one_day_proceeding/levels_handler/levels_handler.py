# one_day_proceeding/levels_handler/levels_handler.py


#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.0
# Description: This module implements the LevelHandler class, which is responsible for detecting and managing price levels based on historical data. It uses parameters defined in a JSON file to find levels across different time windows, merges close levels, and ensures a balanced number of levels above and below the current price. The module also includes error handling for missing parameters and edge cases.
#####################################################


import pandas as pd
import json
import os
from typing import List, Dict, Optional, Any
from one_day_proceeding.levels_finder.levels_finder import LevelsFinder


JSON_PARAMS_PATH = "settings_json/level_finder_settings.json"


class LevelHandler:
    """
    Advanced price level detection and selection.
    """
    # Keys in JSON that should be scaled by last close price
    SCALED_KEYS = ["strong_freq_bin", "simple_freq_bin", "merge_margin"]

    def __init__(
        self,
        json_params_path=JSON_PARAMS_PATH,
        levels_count: int = 5,
        levels_diff_treshold: float = 0.01
    ):
        """Initializes the LevelHandler with parameters from a JSON file and settings for level count and difference threshold.
        Args:
            json_params_path (str): Path to the JSON file containing parameters for level finding.
            levels_count (int): Desired number of levels above and below the current price.
            levels_diff_treshold (float): Minimum percentage difference between levels to consider them distinct.
        """

        self.all_params = self._load_params_from_json(json_params_path)
        self.levels_count = levels_count
        self.levels_diff_treshold = levels_diff_treshold


    def _load_params_from_json(self, path: str) -> Dict[str, Any]:
        """Loads parameters from a JSON file. Returns an empty dictionary if the file is missing or cannot be loaded.
        Args:            path (str): Path to the JSON file.
        """

        if not os.path.exists(path):
            print(f"[ERROR] Parameters file not found: {path}")
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Error loading JSON: {e}")
            return {}


    def _get_scaled_params(self, last_close_price: float, timeframe: str) -> Optional[Dict[str, Any]]:
        """Retrieves parameters for the given timeframe and scales certain parameters by the last close price. Returns None if parameters for the timeframe are missing.
        Args:
            last_close_price (float): The last close price used for scaling parameters.
            timeframe (str): The timeframe for which to retrieve parameters.
        """

        if timeframe not in self.all_params:
            return None

        params = self.all_params[timeframe].copy()

        for key in self.SCALED_KEYS:
            if key in params and isinstance(params[key], (int, float)):
                params[key] *= last_close_price

        return params


    def _mirror_levels(self, levels: List[float], current_price: float, needed_count: int, direction: str) -> List[float]:
        """
        Creates mirror reflections until required level count is reached.
        direction: 'up' or 'down'
        """

        mirrored = []
        sorted_levels = sorted(levels)

        if not sorted_levels:
            return []

        base_lvls = sorted_levels[-5:]

        max_iterations = 100
        iterations = 0

        while len(mirrored) < needed_count and iterations < max_iterations:
            iterations += 1
            prev_len = len(mirrored)

            for lvl in base_lvls:
                diff = abs(lvl - current_price)
                up = current_price + diff
                down = current_price - diff

                if direction == "up" and up not in mirrored and up > max(sorted_levels):
                    mirrored.append(up)

                if direction == "down" and down not in mirrored and down < min(sorted_levels):
                    mirrored.append(down)

                if len(mirrored) >= needed_count:
                    break

            if len(mirrored) == prev_len:
                break

        return sorted(list(set(mirrored)))


    def _filter_by_percentage(self, levels: List[float]) -> List[float]:
        """
        Percentage filter - removes levels too close to each other (difference < X%).
        """
        if not levels:
            return []

        levels = sorted(levels)
        filtered = [levels[0]]

        for lvl in levels[1:]:
            last = filtered[-1]
            if abs(lvl - last) / last >= self.levels_diff_treshold:
                filtered.append(lvl)

        return filtered


    def _enforce_levels_count(self, levels: List[float], price: float) -> List[float]:
        """
        Ensures we have levels_count below price and levels_count above price.
        Adds mirrors if levels are missing.
        If mirroring fails, generates levels using fixed percentage steps.
        """
        levels = sorted(levels)

        below = [lvl for lvl in levels if lvl < price]
        above = [lvl for lvl in levels if lvl > price]

        # 1. Fill below
        if len(below) < self.levels_count:
            needed = self.levels_count - len(below)
            mirrored = self._mirror_levels(levels, price, needed, direction="down")
            below.extend(mirrored)

            # Fallback: if still missing, generate using percentage steps
            if len(below) < self.levels_count:
                missing = self.levels_count - len(below)
                step_pct = self.levels_diff_treshold  # Use diff threshold as step

                # Start from lowest existing level or price
                start = min(below) if below else price

                for i in range(missing):
                    new_level = start * (1 - step_pct * (i + 1))
                    below.append(new_level)

        # 2. Fill above
        if len(above) < self.levels_count:
            needed = self.levels_count - len(above)
            mirrored = self._mirror_levels(levels, price, needed, direction="up")
            above.extend(mirrored)

            # Fallback: if still missing, generate using percentage steps
            if len(above) < self.levels_count:
                missing = self.levels_count - len(above)
                step_pct = self.levels_diff_treshold

                # Start from highest existing level or price
                start = max(above) if above else price

                for i in range(missing):
                    new_level = start * (1 + step_pct * (i + 1))
                    above.append(new_level)

        # Take nearest levels_count
        below = sorted(below, reverse=True)[:self.levels_count]
        above = sorted(above)[:self.levels_count]

        combined = below[::-1] + above
        return sorted(set(combined))


    def find_and_handle_levels(
        self,
        df: pd.DataFrame,
        timeframe: str,
        previous_levels: List[float]
    ) -> List[float]:

        if df.empty or len(df) < 50:
            return []

        last_close = df["close"].iloc[-1]
        last_high = df["high"].iloc[-1]
        last_low = df["low"].iloc[-1]

        params = self._get_scaled_params(last_close, timeframe)
        if not params:
            return []

        merge_margin = params.get("merge_margin")
        if merge_margin is None:
            print("[ERROR] Missing merge_margin parameter")
            return []

        # -------------------------------
        # 1. Collect levels from different windows
        # -------------------------------
        windows = [50, 100, 200, len(df)]
        collected = []

        for w in windows:
            start = max(len(df) - w, 0)
            sub = df[start:].copy()

            finder = LevelsFinder(
                df=sub,
                point_now=sub.index[-1],
                **params
            )
            found = finder.run()
            collected.extend(found)

        # -------------------------------
        # 2. Merge levels at the end
        # -------------------------------
        collected = sorted(collected)
        merged = [collected[0]] if collected else []

        for lvl in collected[1:]:
            if abs(lvl - merged[-1]) > merge_margin:
                merged.append(lvl)

        if not merged:
            merged = []

        # -------------------------------
        # 3. Add previous levels (if any)
        # -------------------------------
        # previous_levels can be empty - that's OK (Option C)
        all_levels = sorted(set(merged + previous_levels))

        # -------------------------------
        # 4. Percentage filter
        # -------------------------------
        all_levels = self._filter_by_percentage(all_levels)

        # -------------------------------
        # 5. Enforce level count in both directions + mirrors
        # -------------------------------
        final_levels = self._enforce_levels_count(all_levels, last_close)

        return sorted(final_levels)
