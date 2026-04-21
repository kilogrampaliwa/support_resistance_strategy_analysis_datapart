#one_day_proceeding\levels_finder\levels_finder.py


#-------------------------------------------------------
# MAIN MODULE FOR LEVELS FINDER PIPELINE
#-------------------------------------------------------

#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.0
# Description: This module provides a LevelsFinder class that implements a pipeline to identify strong and simple levels from a DataFrame of candles. The pipeline includes cutting out a specific time period, detecting pivot highs and lows, calculating frequencies of pivot closes for strong levels, calculating frequencies of remaining closes for simple levels, and merging strong and simple levels while filtering out simple levels that are near strong levels based on a specified margin.
#####################################################


import pandas as pd
from one_day_proceeding.levels_finder.cutout_time_period import cutoutTimePeriod
from one_day_proceeding.levels_finder.strong_level_points import strongLevelPoints
from one_day_proceeding.levels_finder.strong_level_frequencies import StrongLevelFrequencies
from one_day_proceeding.levels_finder.simple_frequencies import SimpleFrequencies
from one_day_proceeding.levels_finder.levels_merger import LevelsMerger, remove_strong_zones

class LevelsFinder:

    def __init__(
        self,
        df                      : pd.DataFrame,
        point_now               : float,
        back_window_size        : int|str,
        pivot_window            : int|tuple,
        strong_freq_bin         : int,
        strong_freq_threshold   : int,
        simple_freq_bin         : int,
        simple_freq_threshold   : int,
        merge_margin            : float
    ):
        """Initialize the LevelsFinder with the necessary parameters for the levels finding pipeline.
        Args:
            df (pd.DataFrame):              The input DataFrame containing the candle data.
            point_now (float):              The reference point in time (e.g., current price or timestamp) for cutting out the time period.
            back_window_size (int|str):     The size of the back window to cut out (e.g., number of rows or time duration).
            pivot_window (int|tuple):       The window size(s) for detecting pivot highs and lows. Can be a single integer or a tuple of two integers (n1, n2).
            strong_freq_bin (int):          The bin size for histogramming the values of pivot closes to identify strong levels.
            strong_freq_threshold (int):    The frequency threshold for filtering strong levels from the histogram.
            simple_freq_bin (int):          The bin size for histogramming the values of remaining closes to identify simple levels.
            simple_freq_threshold (int):    The frequency threshold for filtering simple levels from the histogram.
            merge_margin (float):           The margin within which simple levels are considered near strong levels and removed during the merging process."""

        required_cols = ['open', 'high', 'low', 'close']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"DataFrame must contain columns: {required_cols}")

        self.df_original = df
        self.point_now = point_now
        self.back_window_size = back_window_size
        self.pivot_window = pivot_window
        self.strong_freq_bin = strong_freq_bin
        self.strong_freq_threshold = strong_freq_threshold
        self.simple_freq_bin = simple_freq_bin
        self.simple_freq_threshold = simple_freq_threshold
        self.merge_margin = merge_margin
        self.df = None
        self._strong_points = None
        self._strong_levels = None
        self._simple_levels = None
        self._final_levels = None


    # ------------------------------------------------------
    # 0: Cut out time window
    # ------------------------------------------------------

    def cutout(self)->pd.DataFrame:
        """Cut out a specific time period from the original DataFrame based on the given point in time and back window size, and store the result in self.df."""

        self.df = cutoutTimePeriod(
            df=self.df_original,
            point_now=self.point_now,
            back_window_size=self.back_window_size
        )
        return self.df


    # ------------------------------------------------------
    # 1: Detect pivot highs and lows
    # ------------------------------------------------------

    def detect_pivots(self)->pd.DataFrame:
        """Detect pivot highs and lows in the DataFrame using the specified pivot window sizes n1 and n2, and return a DataFrame with an additional 'pivot' column indicating the type of pivot (0 = none, 1 = pivot low, 2 = pivot high)."""

        if self.df is None or self.df.empty:
            self.cutout()
        if self.df is None or self.df.empty:
            # no data, set empty result
            self._strong_points = pd.DataFrame()
            return self._strong_points

        if isinstance(self.pivot_window, tuple) and len(self.pivot_window) == 2:
            n1, n2 = self.pivot_window
        else:
            n1, n2 = self.pivot_window, self.pivot_window

        pivots = strongLevelPoints(self.df.copy(), n1, n2)
        self._strong_points = pivots
        return pivots


    # ------------------------------------------------------
    # 2: Frequencies of pivot closes -> strong levels
    # ------------------------------------------------------

    def strong_levels(self)->list:
        """Calculate strong levels by identifying pivot points in the DataFrame and then calculating frequencies of the close values at those pivot points to identify strong levels based on the specified frequency threshold."""

        if self._strong_points is None:
            self.detect_pivots()

        # If _strong_points is empty or doesn't have pivot column or sum == 0 -> no strong levels
        if self._strong_points is None or self._strong_points.empty or 'pivot' not in self._strong_points.columns:
            self._strong_levels = []
            return self._strong_levels

        if self._strong_points['pivot'].sum() == 0:
             self._strong_levels = []
             return self._strong_levels

        freq = StrongLevelFrequencies(
            df_candles_with_pivots=self._strong_points,
            bin_size=self.strong_freq_bin,
            threshold=self.strong_freq_threshold,
            column="close"
        )()
        self._strong_levels = sorted(freq)
        return self._strong_levels


    # ------------------------------------------------------
    # 3: Frequencies of remaining closes -> simple levels
    # ------------------------------------------------------

    def simple_levels(self)->list:
        """Calculate simple levels by filtering out values that are near strong levels based on the specified merge margin, and then calculating frequencies of the remaining values to identify simple levels."""

        if self._strong_levels is None:
            self.strong_levels()

        if 'close' not in self.df.columns:
             print("Warning: Cannot find 'close' column for simple levels.")
             return []

        values_list = self.df["close"].tolist()

        filtered_values = remove_strong_zones(
            values=values_list,
            strong_levels=self._strong_levels,
            margin=self.merge_margin
        )
        simple_freq = SimpleFrequencies(
            values=filtered_values,
            bin_size=self.simple_freq_bin,
            threshold=self.simple_freq_threshold
        )()
        self._simple_levels = sorted(simple_freq)
        return self._simple_levels


    # ------------------------------------------------------
    # 4: Merge strong + simple -> final levels
    # ------------------------------------------------------

    def final_levels(self)->list:
        """Merge strong levels with simple levels while removing simple levels that are near strong levels based on the specified merge margin, and return the final sorted list of levels."""

        if self._simple_levels is None:
            self.simple_levels()
        merged = LevelsMerger(
            strong_levels=self._strong_levels,
            simple_levels=self._simple_levels,
            merge_margin=self.merge_margin
        )()
        self._final_levels = sorted(merged)
        return self._final_levels


    # ------------------------------------------------------
    # Run pipeline
    # ------------------------------------------------------

    def run(self)->list:
        """Run the levels finding pipeline and return the final levels."""

        self.cutout()
        if self.df.empty:
            return []
        self.detect_pivots()
        self.strong_levels()
        self.simple_levels()
        return self.final_levels()
