# proceed_datasets/__init__.py

"""
Dataset Processing Module

Automated processing of OHLC datasets from input_data through the
trading analysis pipeline (one_day_proceeding) with database storage
(database_handling).

Main Components:
- DatasetProcessor: High-level orchestrator
- DatasetLoader: Load data from files
- TimeframeDetector: Detect H1, D1, etc
- BatchProcessor: Process through pipeline
- ProgressTracker: Monitor progress

Quick Start:
    from proceed_datasets import DatasetProcessor
    from database_handling import TradingDatabase
    
    # Setup
    db = TradingDatabase(password="your_password")
    processor = DatasetProcessor(database=db)
    
    # Scan available datasets
    datasets = processor.scan_datasets()
    print(f"Found {len(datasets)} datasets")
    
    # Process specific file
    results = processor.process_dataset_by_name("EURUSD_H1.txt")
    
    # Process all H1 datasets
    results = processor.process_by_timeframe("H1")
"""

from proceed_datasets.dataset_processor import DatasetProcessor
from proceed_datasets.data_loader.dataset_loader import DatasetLoader
from proceed_datasets.timeframe_detector.timeframe_detector import TimeframeDetector
from proceed_datasets.batch_processor.batch_processor import BatchProcessor
from proceed_datasets.progress_tracker.progress_tracker import ProgressTracker

__all__ = [
    'DatasetProcessor',
    'DatasetLoader',
    'TimeframeDetector',
    'BatchProcessor',
    'ProgressTracker'
]

__version__ = '1.0.0'
