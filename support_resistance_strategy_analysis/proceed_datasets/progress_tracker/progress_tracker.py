# proceed_datasets/progress_tracker/progress_tracker.py

#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 13.03.2026
# Version: 1.0
# Description: Progress Tracker Module. Tracks and reports progress of dataset processing.
#####################################################

from datetime import datetime, timedelta
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Tracks processing progress with ETA calculation and reporting.
    """

    def __init__(self, total_items: int, report_interval: int = 10):
        """
        Initialize ProgressTracker.

        Args:
            total_items: Total number of items to process
            report_interval: Report progress every N items
        """
        self.total_items = total_items
        self.report_interval = report_interval
        self.current_item = 0
        self.start_time = datetime.now()
        self.last_report_time = self.start_time

        self.stats = {
            'succeeded': 0,
            'failed': 0,
            'skipped': 0
        }

    def update(self, success: bool = True, skipped: bool = False):
        """
        Update progress.

        Args:
            success: Whether operation succeeded
            skipped: Whether operation was skipped
        """
        self.current_item += 1

        if skipped:
            self.stats['skipped'] += 1
        elif success:
            self.stats['succeeded'] += 1
        else:
            self.stats['failed'] += 1

        # Report progress at intervals
        if self.current_item % self.report_interval == 0 or self.current_item == self.total_items:
            self._report_progress()

    def _report_progress(self):
        """Report current progress."""
        elapsed = datetime.now() - self.start_time
        progress_pct = (self.current_item / self.total_items) * 100

        # Calculate ETA
        if self.current_item > 0:
            time_per_item = elapsed.total_seconds() / self.current_item
            remaining_items = self.total_items - self.current_item
            eta_seconds = time_per_item * remaining_items
            eta = timedelta(seconds=int(eta_seconds))
        else:
            eta = "Unknown"

        logger.info(
            f"Progress: {self.current_item}/{self.total_items} ({progress_pct:.1f}%) | "
            f"Succeeded: {self.stats['succeeded']} | "
            f"Failed: {self.stats['failed']} | "
            f"Elapsed: {str(elapsed).split('.')[0]} | "
            f"ETA: {eta}"
        )

    def get_summary(self) -> Dict:
        """
        Get processing summary.

        Returns:
            Dictionary with summary statistics
        """
        elapsed = datetime.now() - self.start_time

        return {
            'total_items': self.total_items,
            'processed': self.current_item,
            'succeeded': self.stats['succeeded'],
            'failed': self.stats['failed'],
            'skipped': self.stats['skipped'],
            'elapsed_seconds': elapsed.total_seconds(),
            'items_per_second': self.current_item / elapsed.total_seconds() if elapsed.total_seconds() > 0 else 0,
            'success_rate_pct': (self.stats['succeeded'] / self.current_item * 100) if self.current_item > 0 else 0
        }
