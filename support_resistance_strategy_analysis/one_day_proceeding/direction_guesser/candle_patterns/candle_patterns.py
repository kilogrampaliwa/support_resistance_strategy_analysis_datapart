# one_day_proceeding/direction_guesser/candle_patterns/candle_patterns.py


#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.0
# Description: This module implements the TrendPattern class, which analyzes candlestick patterns to predict market trends. The class includes methods to identify various popular candlestick patterns, such as hammers, engulfing patterns, and morning stars. The main function, predict_trend, evaluates the presence of these patterns in a given DataFrame and assigns a score to determine whether the overall trend is upward, downward, or neutral.
######################################################


class TrendPattern:
    """Analyzes candlestick patterns to predict market trends."""

    def __init__(self, lookback=10):
        """Initializes the TrendPattern with a specified lookback period for analyzing recent candlestick patterns.
        Args:
            lookback (int): The number of recent candlesticks to analyze for pattern recognition.
        """

        self.lookback = lookback

    # -------------------------
    #  Helper – parts of candle
    # -------------------------
    def _parts(self, row):
        body = abs(row["close"] - row["open"])
        upper = row["high"] - max(row["open"], row["close"])
        lower = min(row["open"], row["close"]) - row["low"]
        return body, upper, lower

    # -------------------------
    #  POPULAR PATTERNS
    # -------------------------

    # 1-CANDLE
    def is_hammer(self, row):
        body, upper, lower = self._parts(row)
        return lower >= 2 * body and upper <= body * 0.3 and row["close"] > row["open"]

    def is_inverted_hammer(self, row):
        body, upper, lower = self._parts(row)
        return upper >= 2 * body and lower <= body * 0.3 and row["close"] > row["open"]

    def is_hanging_man(self, row):
        body, upper, lower = self._parts(row)
        return lower >= 2 * body and upper <= body * 0.3 and row["close"] < row["open"]

    def is_shooting_star(self, row):
        body, upper, lower = self._parts(row)
        return upper >= 2 * body and lower <= body * 0.3 and row["close"] < row["open"]

    def is_doji(self, row, threshold=0.1):
        body = abs(row["close"] - row["open"])
        rng = row["high"] - row["low"]
        return body <= rng * threshold

    def is_spinning_top(self, row):
        body, upper, lower = self._parts(row)
        total = upper + lower
        return (body < total * 0.5) and (upper > body * 0.3) and (lower > body * 0.3)

    # 2-CANDLE
    def is_bullish_engulfing(self, prev, curr):
        return prev["close"] < prev["open"] and \
               curr["close"] > curr["open"] and \
               curr["close"] > prev["open"] and \
               curr["open"] < prev["close"]

    def is_bearish_engulfing(self, prev, curr):
        return prev["close"] > prev["open"] and \
               curr["close"] < curr["open"] and \
               curr["open"] > prev["close"] and \
               curr["close"] < prev["open"]

    def is_piercing_line(self, prev, curr):
        midpoint = (prev["open"] + prev["close"]) / 2
        return (prev["close"] < prev["open"] and
                curr["open"] < prev["low"] and
                curr["close"] > midpoint)

    def is_dark_cloud_cover(self, prev, curr):
        midpoint = (prev["open"] + prev["close"]) / 2
        return (prev["close"] > prev["open"] and
                curr["open"] > prev["high"] and
                curr["close"] < midpoint)

    def is_harami_bullish(self, prev, curr):
        return prev["close"] < prev["open"] and \
               curr["open"] > prev["close"] and \
               curr["close"] < prev["open"]

    def is_harami_bearish(self, prev, curr):
        return prev["close"] > prev["open"] and \
               curr["open"] < prev["close"] and \
               curr["close"] > prev["open"]

    def is_tweezer_bottom(self, prev, curr):
        return prev["low"] == curr["low"] and \
               prev["close"] < prev["open"] and curr["close"] > curr["open"]

    def is_tweezer_top(self, prev, curr):
        return prev["high"] == curr["high"] and \
               prev["close"] > prev["open"] and curr["close"] < curr["open"]

    # 3-CANDLE
    def is_morning_star(self, rows):
        # Convert DataFrame slice to list of Series
        if len(rows) < 3:
            return False
        
        row_list = [rows.iloc[i] for i in range(len(rows))]
        a, b, c = row_list[0], row_list[1], row_list[2]
        
        return (a["close"] < a["open"] and
                abs(b["close"] - b["open"]) < abs(a["close"] - a["open"]) * 0.4 and
                c["close"] > c["open"] and
                c["close"] > (a["open"] + a["close"]) / 2)

    def is_evening_star(self, rows):
        # Convert DataFrame slice to list of Series
        if len(rows) < 3:
            return False
            
        row_list = [rows.iloc[i] for i in range(len(rows))]
        a, b, c = row_list[0], row_list[1], row_list[2]
        
        return (a["close"] > a["open"] and
                abs(b["close"] - b["open"]) < abs(a["close"] - a["open"]) * 0.4 and
                c["close"] < c["open"] and
                c["close"] < (a["open"] + a["close"]) / 2)

    def is_three_white_soldiers(self, rows):
        # Convert DataFrame slice to list of Series
        if len(rows) < 3:
            return False
            
        row_list = [rows.iloc[i] for i in range(len(rows))]
        a, b, c = row_list[0], row_list[1], row_list[2]
        
        return (a["close"] > a["open"] and
                b["close"] > b["open"] and
                c["close"] > c["open"] and
                a["close"] < b["close"] < c["close"])

    def is_three_black_crows(self, rows):
        # Convert DataFrame slice to list of Series
        if len(rows) < 3:
            return False
            
        row_list = [rows.iloc[i] for i in range(len(rows))]
        a, b, c = row_list[0], row_list[1], row_list[2]
        
        return (a["close"] < a["open"] and
                b["close"] < b["open"] and
                c["close"] < c["open"] and
                a["close"] > b["close"] > c["close"])

    # ---------------------------------------
    #   MAIN FUNCTION – trend prediction
    # ---------------------------------------
    def predict_trend(self, df):
        df = df.copy().tail(self.lookback)
        rows = df.reset_index(drop=True)
        score = 0

        for i in range(len(rows)):
            row = rows.loc[i]

            # 1-candle
            if self.is_hammer(row): score += 2
            if self.is_inverted_hammer(row): score += 1
            if self.is_hanging_man(row): score -= 2
            if self.is_shooting_star(row): score -= 2
            if self.is_spinning_top(row): score += 0  # neutral
            if self.is_doji(row): score += 0  # neutral

            # 2-candle
            if i > 0:
                prev = rows.loc[i - 1]
                if self.is_bullish_engulfing(prev, row): score += 3
                if self.is_bearish_engulfing(prev, row): score -= 3
                if self.is_piercing_line(prev, row): score += 3
                if self.is_dark_cloud_cover(prev, row): score -= 3
                if self.is_harami_bullish(prev, row): score += 2
                if self.is_harami_bearish(prev, row): score -= 2
                if self.is_tweezer_bottom(prev, row): score += 2
                if self.is_tweezer_top(prev, row): score -= 2

            # 3-candle
            if i >= 2:
                triple = rows.loc[i - 2:i]
                if self.is_morning_star(triple): score += 4
                if self.is_evening_star(triple): score -= 4
                if self.is_three_white_soldiers(triple): score += 4
                if self.is_three_black_crows(triple): score -= 4

        # ------------------------
        #  FINAL DECISION
        # ------------------------
        if score > 1:
            return "UP"
        elif score < -1:
            return "DOWN"
        return "NEUTRAL"
