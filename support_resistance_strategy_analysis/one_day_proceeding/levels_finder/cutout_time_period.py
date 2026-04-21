#one_day_proceeding\levels_finder\cutout_time_period.py


#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.0
# Description: This module provides a function to cut out a specific time period from a DataFrame based on a given point in time and a back window size.
#####################################################


import pandas as pd

def cutoutTimePeriod(df: pd.DataFrame, point_now: float, back_window_size: int) -> pd.DataFrame:
    """
    Cut out a specific time period from the DataFrame based on the given point in time and back window size.
    Args:
        df (pd.DataFrame): The input DataFrame containing the data.
        point_now (float): The reference point in time (e.g., current price or timestamp).
        back_window_size (int): The size of the back window to cut out (e.g., number of rows or time duration).
    If the back_window_size is larger than the available data, it returns all data up to point_now.
    """
    df_cut = df.loc[:point_now]

    if df_cut.empty:
        return df_cut

    if isinstance(back_window_size, (int, float)):
        x = int(back_window_size)
        if x > len(df_cut):
            return df_cut
        else:
            return df_cut.iloc[-x:]

    raise ValueError(f"Unsupported back_window_size format: {back_window_size}. Expected int or float.")



