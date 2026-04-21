#one_day_proceeding\levels_finder\strong_level_points.py


#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.0
# Description: This module provides a function to identify strong level points in a DataFrame of candles by checking for pivot highs and lows based on specified window sizes n1 and n2.
#####################################################



import pandas as pd
import numpy as np
from enum import IntEnum

class PivotType(IntEnum):
    NONE = 0
    LOW = 1
    HIGH = 2

def strongLevelPoints(df: pd.DataFrame, n1: int, n2: int) -> pd.DataFrame:
    """
    Detect pivot highs/lows in df using asymmetric window n1 (left) / n2 (right).
    Returns df with column 'pivot':
        0 = none
        1 = pivot low
        2 = pivot high
    """
    df = df.copy()

    pivot_array = np.zeros(len(df), dtype=np.int32)

    highs = df['high'].values
    lows  = df['low'].values
    L = len(df)

    for i in range(n1, L - n2):
        left_highs  = highs[i - n1:i]
        right_highs = highs[i + 1:i + 1 + n2]
        if highs[i] > max(left_highs) and highs[i] > max(right_highs):
            pivot_array[i] = int(PivotType.HIGH)

        left_lows  = lows[i - n1:i]
        right_lows = lows[i + 1:i + 1 + n2]
        if lows[i] < min(left_lows) and lows[i] < min(right_lows):
            pivot_array[i] = max(pivot_array[i], int(PivotType.LOW))

    df['pivot'] = pivot_array
    return df
