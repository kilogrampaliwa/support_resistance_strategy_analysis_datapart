#one_day_proceeding\direction_guesser\direction_guesser.py


#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.0
# Description: This module provides the DirectionGuesser class, which serves as a unified interface for different trend detection methods, including linear regression, quadratic regression, and candlestick pattern analysis. The class allows users to easily switch between methods and obtain trend predictions based on the provided data.
#####################################################


from one_day_proceeding.direction_guesser.linear_trend.linear_trend import LinearTrend
from one_day_proceeding.direction_guesser.quadratic_trend.quadratic_trend import QuadraticTrend
from one_day_proceeding.direction_guesser.candle_patterns.candle_patterns import TrendPattern

class DirectionGuesser:
    def __init__(self, method="linear", **kwargs):
        """Initializes the DirectionGuesser with the specified method and parameters.
        Args:            method (str): The trend detection method to use ("linear", "quadratic", or "candle").
            **kwargs: Additional parameters specific to the chosen method.
        """
        self.method_name = method.lower()
        if self.method_name == "linear":
            self.method = LinearTrend(**kwargs)
        elif self.method_name == "quadratic":
            self.method = QuadraticTrend(**kwargs)
        elif self.method_name == "candle":
            self.method = TrendPattern(**kwargs)
        else:
            raise ValueError(f"Nieznana metoda: {method}")

    def detect_trend(self, df):
        """Detects the trend based on the provided DataFrame using the selected method.
        Args:            df (pd.DataFrame): The input data for trend detection."""
        if self.method_name in ["linear", "quadratic"]:

            return self.method.detect_trend(df)
        elif self.method_name == "candle":

            return self.method.predict_trend(df)

    def get_equation(self):
        """Returns the equation of the detected trend if applicable."""
        if self.method_name in ["linear", "quadratic"]:
            return self.method.equation
        return None
