#one_day_proceeding\direction_guesser\linear_trend\linear_trend.py


#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.0
# Description: This module implements the LinearTrend class, which detects the trend of a given dataset using linear regression. The class provides methods to calculate the slope of the regression line and determine whether the trend is upward, downward, or neutral based on a specified threshold. Additionally, it stores the equation of the fitted line for reference.
######################################################


import numpy as np

class LinearTrend:
    """Detects the trend of a dataset using linear regression."""

    def __init__(self, lookback=20, neutral_threshold=0.0001):
        """
        Initializes the LinearTrend with specified lookback period and neutral threshold.
        Args:
            lookback (int): The number of recent data points to consider for trend detection.
            neutral_threshold (float): The slope threshold below which the trend is considered neutral.
        """
        self.lookback = lookback
        self.neutral_threshold = neutral_threshold
        self.equation = None   # nowy atrybut


    def _regression_slope(self, y):
        """
        Calculates the slope and intercept of the linear regression line for the given y values.
        Args:
            y (array-like): The dependent variable values for regression.
        """
        x = np.arange(len(y))
        slope, intercept = np.polyfit(x, y, 1)
        return slope, intercept

    def detect_trend(self, df):
        """Detects the trend based on the slope of the linear regression line fitted to the last 'lookback' values of the 'w_avre' column in the DataFrame.
        Args:
            df (pd.DataFrame): The input DataFrame containing the 'w_avre' column.
        """
        values = df["w_avre"].tail(self.lookback).values

        if len(values) < 2:
            self.equation = None
            return "NEUTRAL"

        slope, intercept = self._regression_slope(values)

        self.equation = f"y = {slope:.6f} * x + {intercept:.6f}"

        if slope > self.neutral_threshold:
            return "UP"
        elif slope < -self.neutral_threshold:
            return "DOWN"
        else:
            return "NEUTRAL"
