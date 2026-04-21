# proceed_datasets/dataset_processor.py

#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 13.03.2026
# Version: 1.0
# Description: Dataset Processor - Main Orchestrator. High-level interface for processing datasets from input_data through the trading analysis pipeline (one_day_proceeding) and saving to database (database_handling).
#####################################################

"""
Dataset Processor - Main Orchestrator

High-level interface for processing datasets from input_data through
the trading analysis pipeline (one_day_proceeding) and saving to database
(database_handling).

Main workflow:
1. Scan input_data for available files
2. Detect timeframes (H1, D1, etc)
3. Present options to user
4. Process selected datasets
5. Save results to database
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Callable
import logging

from proceed_datasets.data_loader.dataset_loader import DatasetLoader
from proceed_datasets.timeframe_detector.timeframe_detector import TimeframeDetector
from proceed_datasets.batch_processor.batch_processor import BatchProcessor
from proceed_datasets.progress_tracker.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


class DatasetProcessor:
    """
    Main orchestrator for dataset processing.

    High-level interface that combines:
    - DatasetLoader: Load data from input_data
    - TimeframeDetector: Detect H1, D1, etc
    - BatchProcessor: Process through pipeline
    - Database: Save results

    Example:
        processor = DatasetProcessor(database=db)

        # List available datasets
        datasets = processor.scan_datasets()

        # Process specific dataset
        results = processor.process_dataset_by_name("EURUSD_H1.txt")

        # Process all H1 datasets
        results = processor.process_by_timeframe("H1")
    """

    def __init__(
        self,
        input_dir: str = "input_data",
        database=None,
        step_size: int = 100,
        min_history: int = 200,
        future_bars: int = 100,
        default_timeframe: str = "D1"
    ):
        """
        Initialize DatasetProcessor.

        Args:
            input_dir: Path to input data directory
            database: TradingDatabase instance (optional)
            step_size: Bars between analyses
            min_history: Minimum history needed
            future_bars: Future bars for validation
            default_timeframe: Default timeframe if not detected (default: "D1")
        """
        self.loader = DatasetLoader(input_dir)
        self.detector = TimeframeDetector()
        self.batch_processor = BatchProcessor(
            database=database,
            step_size=step_size,
            min_history=min_history,
            future_bars=future_bars
        )
        self.database = database
        self.default_timeframe = default_timeframe

    def scan_datasets(self, detect_timeframe: bool = False) -> List[Dict]:
        """
        Scan input_data directory and analyze available datasets.

        Args:
            detect_timeframe: Attempt to detect timeframe for each file (default: False)
                            If False, all files assumed to be D1 (daily)

        Returns:
            List of dataset information dictionaries

        Example:
            [
                {
                    'filename': 'EURUSD_D1.txt',
                    'path': 'input_data/EURUSD_D1.txt',
                    'pair': 'EURUSD',
                    'timeframe': 'D1',
                    'rows': 10000,
                    'valid': True
                },
                ...
            ]
        """
        logger.info("Scanning input_data directory...")

        files = self.loader.list_available_files()
        datasets = []

        for filepath in files:
            dataset_info = self._analyze_file(filepath, detect_timeframe)
            datasets.append(dataset_info)

        logger.info(f"Found {len(datasets)} datasets")

        return datasets

    def _analyze_file(self, filepath: Path, detect_timeframe: bool) -> Dict:
        """
        Analyze single file.

        Args:
            filepath: Path to file
            detect_timeframe: Detect timeframe (if False, defaults to D1)

        Returns:
            Dataset information dictionary
        """
        info = self.loader.get_file_info(filepath)

        # Try to extract pair name from filename
        pair = self._extract_pair_from_filename(filepath.name)
        info['pair'] = pair

        # Detect or default timeframe
        if detect_timeframe:
            # Try from filename first
            timeframe = self.detector.detect_from_filename(filepath.name)

            # If not found, try loading data and detecting
            if not timeframe and info.get('has_ohlc'):
                try:
                    df = self.loader.load_file(filepath)
                    if df is not None:
                        timeframe = self.detector.detect_timeframe(df)
                except Exception as e:
                    logger.error(f"Failed to detect timeframe for {filepath.name}: {e}")

            info['timeframe'] = timeframe
            info['timeframe_detected'] = timeframe is not None
        else:
            # Default to configured default timeframe (usually D1)
            timeframe = self.detector.detect_from_filename(filepath.name)
            if not timeframe:
                timeframe = self.default_timeframe
                logger.debug(f"{filepath.name}: Defaulting to {self.default_timeframe}")

            info['timeframe'] = timeframe
            info['timeframe_detected'] = False  # Not detected, defaulted or from filename

        info['valid'] = info.get('has_ohlc', False) and info.get('timeframe') is not None

        return info

    def _extract_pair_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract currency pair from filename.

        Args:
            filename: Name of file

        Returns:
            Pair string (e.g., "EURUSD") or None

        Example:
            "EURUSD_H1.txt" -> "EURUSD"
            "gbpusd_daily.csv" -> "GBPUSD"
        """
        # Common currency pairs
        common_pairs = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'NZDUSD', 'USDCAD',
            'EURGBP', 'EURJPY', 'GBPJPY', 'AUDJPY', 'EURAUD', 'EURCHF', 'GBPCHF'
        ]

        filename_upper = filename.upper()

        for pair in common_pairs:
            if pair in filename_upper:
                return pair

        # Try to extract 6-letter sequence (XXXYYY format)
        import re
        match = re.search(r'[A-Z]{6}', filename_upper)
        if match:
            return match.group(0)

        logger.debug(f"Could not extract pair from filename: {filename}")
        return None

    def get_datasets_by_timeframe(self, timeframe: str) -> List[Dict]:
        """
        Get all datasets with specific timeframe.

        Args:
            timeframe: Timeframe to filter (e.g., "H1", "D1")

        Returns:
            List of matching datasets
        """
        all_datasets = self.scan_datasets()
        matching = [d for d in all_datasets if d.get('timeframe') == timeframe]

        logger.info(f"Found {len(matching)} datasets with timeframe {timeframe}")

        return matching

    def process_dataset_by_name(
        self,
        filename: str,
        save_to_db: bool = True,
        direction_method: str = "linear"
    ) -> Dict:
        """
        Process specific dataset by filename.

        Args:
            filename: Name of file in input_data
            save_to_db: Save results to database
            direction_method: Direction detection method

        Returns:
            Processing results dictionary
        """
        filepath = self.loader.input_dir / filename

        if not filepath.exists():
            logger.error(f"File not found: {filepath}")
            return {'error': 'File not found'}

        # Analyze file
        info = self._analyze_file(filepath, detect_timeframe=True)

        if not info['valid']:
            logger.error(f"Invalid dataset: {info}")
            return {'error': 'Invalid dataset', 'info': info}

        # Load data
        df = self.loader.load_file(filepath)
        if df is None:
            return {'error': 'Failed to load data'}

        # Process
        results = self.batch_processor.process_dataset(
            df=df,
            pair=info['pair'],
            timeframe=info['timeframe'],
            save_to_db=save_to_db,
            direction_method=direction_method
        )

        return results

    def process_by_timeframe(
        self,
        timeframe: str,
        save_to_db: bool = True,
        direction_method: str = "linear"
    ) -> List[Dict]:
        """
        Process all datasets with specific timeframe.

        Args:
            timeframe: Timeframe to process (e.g., "H1")
            save_to_db: Save results to database
            direction_method: Direction detection method

        Returns:
            List of processing results
        """
        datasets = self.get_datasets_by_timeframe(timeframe)

        if not datasets:
            logger.warning(f"No datasets found with timeframe {timeframe}")
            return []

        logger.info(f"Processing {len(datasets)} {timeframe} datasets")

        all_results = []

        for dataset_info in datasets:
            logger.info(f"Processing: {dataset_info['filename']}")

            result = self.process_dataset_by_name(
                filename=dataset_info['filename'],
                save_to_db=save_to_db,
                direction_method=direction_method
            )

            all_results.append(result)

        return all_results

    def list_available_datasets(self, group_by_timeframe: bool = True) -> Dict:
        """
        List all available datasets in a user-friendly format.

        Args:
            group_by_timeframe: Group results by timeframe

        Returns:
            Dictionary with dataset information
        """
        datasets = self.scan_datasets()

        if not group_by_timeframe:
            return {'datasets': datasets, 'total': len(datasets)}

        # Group by timeframe
        grouped = {}
        for dataset in datasets:
            tf = dataset.get('timeframe', 'unknown')
            if tf not in grouped:
                grouped[tf] = []
            grouped[tf].append(dataset)

        # Summary
        summary = {
            'total_datasets': len(datasets),
            'valid_datasets': sum(1 for d in datasets if d.get('valid')),
            'by_timeframe': {tf: len(ds) for tf, ds in grouped.items()},
            'datasets_by_timeframe': grouped
        }

        return summary
