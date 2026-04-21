#one_day_proceeding\levels_finder\simple_frequencies.py


#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 05.03.2026
# Version: 1.0
# Description: This module provides a class to calculate simple frequencies of values in a list and filter levels based on a specified threshold.
#####################################################


from one_day_proceeding.levels_finder.histo_mapping import histoMapping

class SimpleFrequencies:
    """A class to calculate simple frequencies of values in a list and filter levels based on a specified threshold."""

    def __init__(self, values: list, bin_size: int, threshold: int):

        self.values = values
        self.bin_size = bin_size
        self.threshold = threshold

        self.histo = self._make_histo()
        self.levels = self._filter_levels()

    def _make_histo(self)->dict:
        """Create a histogram mapping of the values using the specified bin size."""
        return histoMapping(self.values, self.bin_size)

    def _filter_levels(self)->list:
        """Filter levels from the histogram based on the specified frequency threshold."""
        return [level for level, freq in self.histo.items() if freq >= self.threshold]

    def __call__(self)->list:
        """Return the filtered levels when the instance is called."""
        return self.levels