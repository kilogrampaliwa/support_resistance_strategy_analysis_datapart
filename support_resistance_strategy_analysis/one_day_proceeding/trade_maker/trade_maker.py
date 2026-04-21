# one_day_proceeding/trade_maker/trade_maker.py


#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.0
# Description: This module provides the tradeMaker function, which generates trade parameters (TP/SL levels) based on the current price, detected levels, and market direction. It includes advanced handling for missing levels with configurable fallback strategies and tracks the source of each TP/SL level for better transparency in trade decision-making.
#####################################################


import json
from typing import List, Optional, Dict, Any, Tuple
import math
import os

JSON_PARAMS_PATH = "settings_json/trade_maker_settings.json"


def load_settings(path: str = JSON_PARAMS_PATH) -> Dict[str, Any]:
    """
    Loads trade maker settings from a JSON file.
    Args:
        path (str): The file path to the JSON settings.
    """

    if not os.path.exists(path):
        raise FileNotFoundError(f"Settings file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _levels_map_from_list(price: float, levels: List[float], max_count: int = 5) -> Dict[int, float]:
    """
    Creates a mapping of level indices to their values based on the current price.
    Positive indices are above the price, negative indices are below. Levels are sorted by distance from the price.
    Args:
        price (float): The current price.
        levels (List[float]): A list of detected levels.
        max_count (int): Maximum number of levels to include in each direction.
    """

    unique = sorted(set(levels))
    above = [lv for lv in unique if lv > price]
    below = [lv for lv in unique if lv < price]

    above_sorted = sorted(above)
    below_sorted = sorted(below, reverse=True)

    mapping: Dict[int, float] = {}
    for i in range(1, max_count + 1):
        if i <= len(above_sorted):
            mapping[i] = above_sorted[i - 1]
        if i <= len(below_sorted):
            mapping[-i] = below_sorted[i - 1]
    return mapping


def _get_index_level(index: int, levels_map: Dict[int, float]) -> Optional[float]:
    """
    Returns the level value for the given index from the levels_map, or None if not found.
    Args:
        index (int): The level index to retrieve.
        levels_map (Dict[int, float]): The mapping of level indices to their values.
    """
    return levels_map.get(index, None)


def _find_nearest_in_direction(index: int, levels_map: Dict[int, float]) -> Optional[float]:
    """
    Finds the nearest level in the specified direction if the exact index is not available.
    Args:
        index (int): The desired level index (positive for above, negative for below).
        levels_map (Dict[int, float]): The mapping of level indices to their values.
    """
    if index == 0:
        return None
    sign = 1 if index > 0 else -1
    candidate_indices = sorted([i for i in levels_map.keys() if (i * sign) > 0], key=lambda x: abs(x))
    return levels_map[candidate_indices[0]] if candidate_indices else None


def _percent_fallback(price: float, index: int, pct: float) -> float:
    mult = pct * abs(index)
    if index > 0:
        return price * (1.0 + mult)
    else:
        return price * (1.0 - mult)


def tradeMaker(price: float, levels: List[float], direction: str, timestamp=None, settings_path: str = JSON_PARAMS_PATH) -> Dict[str, Any]:
    """
    TradeMaker with source tracking for TP/SL levels.
    NEW: Tracks whether TP/SL came from:
    - "level": exact level from levels_map
    - "nearest": nearest available level (fallback)
    - "percent": percentage-based fallback
    - "error": level not found and no fallback
    """
    settings = load_settings(settings_path)
    tm = settings.get("trade_maker", {})
    tp_index_cfg = tm.get("tp_level_index", 1)
    sl_index_cfg = tm.get("sl_level_index", -1)
    fallback_when_missing = tm.get("fallback_when_missing", "error")
    fallback_percent = tm.get("fallback_percent", 0.01)
    max_levels_count = settings.get("levels_handler", {}).get("levels_count", 5)
    level_padding_pct = tm.get("level_padding_pct", 0.0)

    result: Dict[str, Any] = {
        "open_price": float(price),
        "direction": direction.upper(),
        "open_datetime": str(timestamp),
        "long_tp": None,
        "long_sl": None,
        "short_tp": None,
        "short_sl": None,
        "levels_map": {},
        "levels_used": {
            "tp_index": tp_index_cfg,
            "sl_index": sl_index_cfg,
            "tp_level": None,
            "sl_level": None,
            "tp_source": None,  # NEW
            "sl_source": None   # NEW
        },
        "warnings": []
    }

    if direction.upper() == "NEUTRAL":
        result["warnings"].append("Direction is NEUTRAL — no TP/SL suggested.")
        result["levels_map"] = _levels_map_from_list(price, levels, max_count=max_levels_count)
        return result

    levels_map = _levels_map_from_list(price, levels, max_count=max_levels_count)
    result["levels_map"] = levels_map

    def resolve_level_for_index(index: int) -> Tuple[Optional[float], str]:
        """
        Resolves the level for a given index with fallback handling.
        Args:
            index (int): The desired level index.
        """

        lvl = _get_index_level(index, levels_map)
        if lvl is not None:
            return (float(lvl), "level")
        if fallback_when_missing == "nearest":
            nearest = _find_nearest_in_direction(index, levels_map)
            if nearest is not None:
                return (float(nearest), "nearest")
            else:
                result["warnings"].append(f"No nearest level available for index {index}.")
                return (None, "error")
        elif fallback_when_missing == "percent":
            return (float(_percent_fallback(price, index, fallback_percent)), "percent")
        else:
            result["warnings"].append(f"Required level index {index} not found and fallback_when_missing='error'.")
            return (None, "error")

    dir_up = (direction.upper() == "UP")

    # Resolve TP and SL with sources
    if dir_up:
        tp_level, tp_source = resolve_level_for_index(tp_index_cfg)
        sl_level, sl_source = resolve_level_for_index(sl_index_cfg)
    else:
        tp_level, tp_source = resolve_level_for_index(tp_index_cfg)
        sl_level, sl_source = resolve_level_for_index(sl_index_cfg)

    def apply_padding(level_val: Optional[float], index: int) -> Optional[float]:
        if level_val is None or level_padding_pct == 0.0:
            return level_val
        diff = level_val - price
        if diff == 0:
            return float(level_val)
        move = -math.copysign(abs(diff) * level_padding_pct, diff)
        return float(level_val + move)

    tp_level_padded = apply_padding(tp_level, tp_index_cfg)
    sl_level_padded = apply_padding(sl_level, sl_index_cfg)

    if direction.upper() == "UP":
        result["long_tp"] = tp_level_padded
        result["long_sl"] = sl_level_padded

        # Mirror levels for SHORT (not used in validation, just stored)
        short_tp_index = -abs(tp_index_cfg)
        short_sl_index = abs(sl_index_cfg)
        short_tp, _ = resolve_level_for_index(short_tp_index)
        short_sl, _ = resolve_level_for_index(short_sl_index)
        result["short_tp"] = apply_padding(short_tp, short_tp_index) if short_tp is not None else None
        result["short_sl"] = apply_padding(short_sl, short_sl_index) if short_sl is not None else None
        
        # Store used levels and sources
        result["levels_used"]["tp_level"] = result["long_tp"]
        result["levels_used"]["sl_level"] = result["long_sl"]
        result["levels_used"]["tp_source"] = tp_source
        result["levels_used"]["sl_source"] = sl_source

    elif direction.upper() == "DOWN":
        result["short_tp"] = tp_level_padded
        result["short_sl"] = sl_level_padded

        # Mirror levels for LONG (not used in validation, just stored)
        long_tp_index = abs(tp_index_cfg)
        long_sl_index = -abs(sl_index_cfg)
        long_tp, _ = resolve_level_for_index(long_tp_index)
        long_sl, _ = resolve_level_for_index(long_sl_index)
        result["long_tp"] = apply_padding(long_tp, long_tp_index) if long_tp is not None else None
        result["long_sl"] = apply_padding(long_sl, long_sl_index) if long_sl is not None else None
        
        # Store used levels and sources
        result["levels_used"]["tp_level"] = result["short_tp"]
        result["levels_used"]["sl_level"] = result["short_sl"]
        result["levels_used"]["tp_source"] = tp_source
        result["levels_used"]["sl_source"] = sl_source

    return result
