#one_day_proceeding\levels_finder\strong_level_frequencies.py


#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.0
# Description: This module provides a class to calculate strong level frequencies from a DataFrame of candles with pivots, using a specified column for the values, bin size for histogramming, and a frequency threshold for filtering levels.
#####################################################


from one_day_proceeding.levels_finder.simple_frequencies import SimpleFrequencies
import pandas as pd

class StrongLevelFrequencies:
    """A class to calculate strong level frequencies from a DataFrame of candles with pivots, using a specified column for the values, bin size for histogramming, and a frequency threshold for filtering levels."""

    def __init__(self, df_candles_with_pivots: pd.DataFrame, bin_size: int, threshold: int, column='close'):
        """Initialize the StrongLevelFrequencies with a DataFrame of candles with pivots, bin size for histogramming, frequency threshold for filtering levels, and the column to be used for values.
        Args:
            df_candles_with_pivots (pd.DataFrame): DataFrame containing candle data with pivot points.
            bin_size (int): Size of the bins for histogramming the values.
            threshold (int): Frequency threshold for filtering levels from the histogram.
            column (str): The column in the DataFrame to be used for calculating frequencies (default is 'close').
        """

        self.values = df_candles_with_pivots[df_candles_with_pivots['pivot'] > 0][column].tolist()
        self.bin_size = bin_size
        self.threshold = threshold
        self.column = column
        self.levels = self._make_frequencies()

    def _make_frequencies(self)->list:
        """Calculate strong level frequencies by creating a histogram of the values and filtering levels based on the specified frequency threshold.
        Returns:
            list: A list of strong levels that meet the frequency threshold.
        """

        histo = SimpleFrequencies(
            values=self.values,
            bin_size=self.bin_size,
            threshold=self.threshold
        )
        return histo()

    def __call__(self)->list:
        return self.levels
