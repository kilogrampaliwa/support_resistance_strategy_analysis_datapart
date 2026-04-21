#one_day_proceeding\levels_finder\histo_mapping.py


#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.0
# Description: This module provides a function to map values into histogram bins.
#####################################################


def histoMapping(values_list: list, bin_size: float) -> dict:
    """
    Map values into histogram bins of a specified size.
    Args:
        values_list (list): List of numerical values to be binned.
        bin_size (float): Size of each histogram bin.
    """

    if not values_list:
        return {}

    min_value = min(values_list)
    max_value = max(values_list)

    bins = {}
    current_bin_start = min_value - (min_value % bin_size)
    while current_bin_start <= max_value:
        bins[round(current_bin_start, 10)] = 0
        current_bin_start += bin_size

    for value in values_list:
        bin_key = round(value - (value % bin_size), 10)
        if bin_key not in bins:
            closest_bin = min(bins.keys(), key=lambda x: abs(x - bin_key))
            bin_key = closest_bin
        bins[bin_key] += 1

    return bins