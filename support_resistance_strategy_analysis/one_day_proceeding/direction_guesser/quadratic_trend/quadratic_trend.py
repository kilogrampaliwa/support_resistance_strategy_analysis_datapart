#one_day_proceeding\direction_guesser\quadratic_trend\quadratic_trend.py



#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.0
# Description: This module implements the QuadraticTrend class, which detects trends in financial data by fitting a quadratic curve to a specified lookback period of the "w_avre" column. The class provides methods to determine the trend direction (UP, DOWN, NEUTRAL) based on the derivative of the fitted curve at the last point, as well as to retrieve the coefficients of the fitted parabola and its equation in a human-readable format.
#####################################################


import numpy as np

class QuadraticTrend:
    """Detects trend by fitting a quadratic curve to the "w_avre" column of the DataFrame."""

    def __init__(self, lookback=20, neutral_threshold=0.0001):
        """
        Initializes the QuadraticTrend with the specified lookback period and neutral threshold.
        Args:
            lookback (int): The number of recent data points to consider for fitting the quadratic curve.
            neutral_threshold (float): The threshold for determining if the trend is neutral based on the derivative at the last point.
        """
        self.lookback = lookback
        self.neutral_threshold = neutral_threshold
        self.equation = None

    def _fit_quadratic(self, y):
        """
        Fits a quadratic curve to the given values and returns the coefficients (a, b, c).
        y: array-like of values to fit
        """
        x = np.arange(len(y))
        coeffs = np.polyfit(x, y, 2)  # [a, b, c]
        return coeffs

    def detect_trend(self, df):
        """
        Detects the trend by fitting a quadratic curve to the "w_avre" column of the DataFrame.
        Returns "UP", "DOWN", or "NEUTRAL" based on the derivative at the last point.
        """
        values = df["w_avre"].tail(self.lookback).values

        if len(values) < 3:
            self.equation = None
            return "NEUTRAL"

        a, b, c = self._fit_quadratic(values)
        self.equation = f"y = {a:.6f} * x^2 + {b:.6f} * x + {c:.6f}"

        x_last = len(values) - 1
        derivative = 2 * a * x_last + b

        if derivative > self.neutral_threshold:
            return "UP"
        elif derivative < -self.neutral_threshold:
            return "DOWN"
        else:
            return "NEUTRAL"

    def get_coefficients(self, df):
        """Returns the coefficients (a, b, c) of the fitted quadratic curve."""
        values = df["w_avre"].tail(self.lookback).values
        return self._fit_quadratic(values)

    def get_derivative_at_end(self, df):
        """Returns the value of the derivative of the fitted quadratic curve at the last point."""
        a, b, c = self.get_coefficients(df)
        x_last = len(df["w_avre"].tail(self.lookback).values) - 1
        return 2 * a * x_last + b
