# proceed_datasets/timeframe_detector/timeframe_detector.py

#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 13.03.2026
# Version: 1.0
# Description: Timeframe Detector Module. Analyzes OHLC data to detect timeframe (H1, D1, M5, etc).
#####################################################



import pandas as pd
from typing import Optional, Dict
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class TimeframeDetector:
    """
    Detects timeframe of OHLC data by analyzing time differences.

    Supports:
    - H1 (1 hour)
    - H4 (4 hours)
    - D1 (1 day)
    - M5, M15, M30 (minutes)
    - W1 (1 week)
    """

    TIMEFRAME_PATTERNS = {
        'M1': 60,           # 1 minute in seconds
        'M5': 300,          # 5 minutes
        'M15': 900,         # 15 minutes
        'M30': 1800,        # 30 minutes
        'H1': 3600,         # 1 hour
        'H4': 14400,        # 4 hours
        'D1': 86400,        # 1 day
        'W1': 604800,       # 1 week
    }

    def __init__(self, tolerance: float = 0.1):
        """
        Initialize TimeframeDetector.

        Args:
            tolerance: Tolerance for matching (0.1 = 10% deviation allowed)
        """
        self.tolerance = tolerance

    def detect_timeframe(
        self,
        df: pd.DataFrame,
        sample_size: int = 100
    ) -> Optional[str]:
        """
        Detect timeframe from DataFrame.

        Args:
            df: DataFrame with DatetimeIndex
            sample_size: Number of samples to analyze

        Returns:
            Timeframe string (e.g., "H1", "D1") or None
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            logger.error("DataFrame index must be DatetimeIndex")
            return None

        if len(df) < 2:
            logger.error("DataFrame too short for timeframe detection")
            return None

        # Calculate time differences
        time_diffs = df.index.to_series().diff().dt.total_seconds()

        # Remove NaN (first row)
        time_diffs = time_diffs.dropna()

        # Sample if dataset is large
        if len(time_diffs) > sample_size:
            time_diffs = time_diffs.sample(n=sample_size, random_state=42)

        # Get most common time difference
        median_diff = time_diffs.median()
        mode_diff = time_diffs.mode()[0] if len(time_diffs.mode()) > 0 else median_diff

        logger.debug(f"Median time diff: {median_diff}s, Mode: {mode_diff}s")

        # Match to known timeframes
        for timeframe, expected_seconds in self.TIMEFRAME_PATTERNS.items():
            lower_bound = expected_seconds * (1 - self.tolerance)
            upper_bound = expected_seconds * (1 + self.tolerance)

            if lower_bound <= mode_diff <= upper_bound:
                logger.info(f"Detected timeframe: {timeframe} "
                           f"(expected: {expected_seconds}s, found: {mode_diff}s)")
                return timeframe

        logger.warning(f"Could not match timeframe (time diff: {mode_diff}s)")
        return None

    def analyze_timeframe_consistency(
        self,
        df: pd.DataFrame
    ) -> Dict:
        """
        Analyze how consistent the timeframe is.

        Args:
            df: DataFrame with DatetimeIndex

        Returns:
            Dictionary with consistency metrics
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            return {'error': 'Not a DatetimeIndex'}

        # Calculate all time differences
        time_diffs = df.index.to_series().diff().dt.total_seconds().dropna()

        if len(time_diffs) == 0:
            return {'error': 'No time differences to analyze'}

        # Count occurrences
        diff_counts = Counter(time_diffs)
        most_common = diff_counts.most_common(5)

        # Calculate consistency
        total = len(time_diffs)
        most_common_count = most_common[0][1]
        consistency_pct = (most_common_count / total) * 100

        return {
            'total_intervals': total,
            'most_common_diff_seconds': most_common[0][0],
            'most_common_count': most_common_count,
            'consistency_pct': consistency_pct,
            'top_5_diffs': most_common,
            'mean_diff': time_diffs.mean(),
            'median_diff': time_diffs.median(),
            'std_diff': time_diffs.std(),
            'has_gaps': consistency_pct < 95.0
        }
    
    def detect_from_filename(self, filename: str) -> Optional[str]:
        """
        Try to detect timeframe from filename.

        Args:
            filename: Name of file

        Returns:
            Timeframe string or None

        Example:
            "EURUSD_H1_2024.txt" -> "H1"
            "gbpusd_1h.csv" -> "H1"
        """
        filename_upper = filename.upper()

        # Direct matches
        for timeframe in self.TIMEFRAME_PATTERNS.keys():
            if timeframe in filename_upper:
                logger.info(f"Detected timeframe from filename: {timeframe}")
                return timeframe

        # Alternative notations
        alt_patterns = {
            '1H': 'H1',
            '4H': 'H4',
            '1D': 'D1',
            'HOURLY': 'H1',
            'DAILY': 'D1',
            '5M': 'M5',
            '15M': 'M15',
            '30M': 'M30',
        }

        for pattern, timeframe in alt_patterns.items():
            if pattern in filename_upper:
                logger.info(f"Detected timeframe from filename pattern '{pattern}': {timeframe}")
                return timeframe

        logger.debug(f"Could not detect timeframe from filename: {filename}")
        return None
