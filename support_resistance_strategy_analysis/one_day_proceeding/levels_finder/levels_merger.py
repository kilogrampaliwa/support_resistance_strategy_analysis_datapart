#one_day_proceeding\levels_finder\levels_merger.py


#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.0
# Description: This module provides two elements: a function to remove values that are near strong levels based on a specified margin, and a class to merge strong levels with simple levels while filtering out simple levels that are near strong levels.
#####################################################


import bisect

def remove_strong_zones(values, strong_levels, margin)->list:
    """
    Remove values that are within a specified margin of strong levels.
    Args:
        values (list): List of numerical values to be filtered.
        strong_levels (list): List of strong levels to compare against.
        margin (float): Margin within which values are considered near strong levels.
    """

    if not strong_levels or not values:
        return values

    sorted_levels = sorted(strong_levels)
    cleaned = []

    for v in values:
        pos = bisect.bisect_left(sorted_levels, v)
        is_near_strong = False
        if pos > 0 and abs(v - sorted_levels[pos - 1]) <= margin:
            is_near_strong = True
        if pos < len(sorted_levels) and abs(v - sorted_levels[pos]) <= margin:
            is_near_strong = True
        if not is_near_strong:
            cleaned.append(v)

    return cleaned


class LevelsMerger:
    """A class to merge strong levels with simple levels while removing simple levels that are near strong levels based on a specified margin."""

    def __init__(self, strong_levels, simple_levels, merge_margin):
        """
        Initialize the LevelsMerger with strong levels, simple levels, and a merge margin.
        Args:
            strong_levels (list): List of strong levels to be preserved.
            simple_levels (list): List of simple levels to be filtered and merged.
            merge_margin (float): Margin within which simple levels are considered near strong levels and removed.
        """
        self.strong_levels = strong_levels
        self.simple_levels = simple_levels
        self.merge_margin = merge_margin

        self.levels = self._merge()

    def _merge(self):
        """Merge strong levels with simple levels while removing simple levels that are near strong levels."""
        filtered_simple = [
            s for s in self.simple_levels
            if not any(abs(s - sl) <= self.merge_margin for sl in self.strong_levels)
        ]
        return sorted(set(self.strong_levels + filtered_simple))

    def __call__(self)->list:
        """Return the merged levels when the instance is called."""
        return self.levels
