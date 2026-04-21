# proceed_datasets/batch_processor/batch_processor.py

#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 13.03.2026
# Version: 1.0
# Description: Batch Processor Module. Processes multiple datasets through the one_day_proceeding pipeline and saves results to database via database_handling.
#####################################################

import pandas as pd
from typing import List, Dict, Optional, Callable
from datetime import datetime
import logging

from one_day_proceeding.one_day_proceeding import OneDayProceeding
from one_day_proceeding.trade_finalizer.trade_finalizer import TradeFinalizer
from one_day_proceeding.one_day_output.one_day_output import OneDayOutput

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Processes datasets in batch through the trading analysis pipeline.

    Workflow:
    1. Load dataset
    2. Iterate through timepoints
    3. Run one_day_proceeding analysis
    4. Finalize trade
    5. Format output
    6. Save to database (optional)
    """

    def __init__(
        self,
        database=None,
        step_size: int = 100,
        min_history: int = 200,
        future_bars: int = 100
    ):
        """
        Initialize BatchProcessor.

        Args:
            database: TradingDatabase instance (optional)
            step_size: Number of bars between analyses
            min_history: Minimum bars needed before first analysis
            future_bars: Bars needed after analysis for validation
        """
        self.database = database
        self.step_size = step_size
        self.min_history = min_history
        self.future_bars = future_bars

    def process_dataset(
        self,
        df: pd.DataFrame,
        pair: str,
        timeframe: str,
        save_to_db: bool = True,
        direction_method: str = "linear",
        callback: Optional[Callable] = None
    ) -> Dict:
        """
        Process entire dataset through pipeline.

        Args:
            df: OHLC DataFrame
            pair: Currency pair (e.g., "EURUSD")
            timeframe: Timeframe (e.g., "H1")
            save_to_db: Save results to database
            direction_method: Direction detection method
            callback: Progress callback function(current, total, trade_data)

        Returns:
            Dictionary with processing results and statistics
        """
        logger.info(f"Processing {pair} {timeframe}: {len(df)} rows")

        results = {
            'pair': pair,
            'timeframe': timeframe,
            'total_rows': len(df),
            'trades_generated': 0,
            'trades_saved': 0,
            'trades_failed': 0,
            'start_time': datetime.now(),
            'trades': []
        }

        # Validate DataFrame
        if not isinstance(df.index, pd.DatetimeIndex):
            logger.error("DataFrame must have DatetimeIndex")
            results['error'] = "Invalid DataFrame index"
            return results

        # Calculate iteration points
        start_idx = self.min_history
        end_idx = len(df) - self.future_bars

        if start_idx >= end_idx:
            logger.error(f"Dataset too small: need {self.min_history + self.future_bars} rows, have {len(df)}")
            results['error'] = "Dataset too small"
            return results

        total_iterations = (end_idx - start_idx) // self.step_size
        logger.info(f"Processing {total_iterations} iterations (step: {self.step_size})")

        # Process each iteration
        for i, idx in enumerate(range(start_idx, end_idx, self.step_size)):
            cutoff_datetime = df.index[idx]

            try:
                # Run analysis pipeline
                trade_result = self._process_single_trade(
                    df=df,
                    cutoff_datetime=cutoff_datetime,
                    timeframe=timeframe,
                    direction_method=direction_method
                )

                if trade_result:
                    results['trades_generated'] += 1
                    results['trades'].append(trade_result)

                    # Save to database if requested
                    if save_to_db and self.database:
                        if self._save_to_database(pair, timeframe, trade_result):
                            results['trades_saved'] += 1
                        else:
                            results['trades_failed'] += 1

                # Callback for progress reporting
                if callback:
                    callback(i + 1, total_iterations, trade_result)

            except Exception as e:
                logger.error(f"Failed to process iteration {i} at {cutoff_datetime}: {e}")
                results['trades_failed'] += 1

        # Calculate statistics
        results['end_time'] = datetime.now()
        results['duration_seconds'] = (results['end_time'] - results['start_time']).total_seconds()
        results['success_rate'] = (
            (results['trades_generated'] / total_iterations * 100)
            if total_iterations > 0 else 0
        )

        logger.info(f"Processing complete: {results['trades_generated']} trades generated, "
                   f"{results['trades_saved']} saved to DB")

        return results

    def _process_single_trade(
        self,
        df: pd.DataFrame,
        cutoff_datetime,
        timeframe: str,
        direction_method: str
    ) -> Optional[Dict]:
        """
        Process single trade through pipeline.

        Args:
            df: OHLC DataFrame
            cutoff_datetime: Analysis cutoff point
            timeframe: Timeframe
            direction_method: Direction detection method

        Returns:
            Trade data dictionary or None if failed
        """
        # A: Run analysis
        processor = OneDayProceeding(
            df=df,
            cutoff_datetime=cutoff_datetime,
            timeframe=timeframe,
            direction_method=direction_method
        )

        trade_data = processor.run_analysis()

        # Check for errors
        if "error" in trade_data:
            logger.debug(f"Analysis error at {cutoff_datetime}: {trade_data['error']}")
            return None

        # Get future data
        future_data = processor.get_future_data()

        # F: Finalize trade
        finalizer = TradeFinalizer(trade_data, future_data)
        finalized = finalizer.finalize()

        # O: Format output
        output = OneDayOutput(finalized)
        trade_row = output.to_row()

        return trade_row

    def _save_to_database(
        self,
        pair: str,
        timeframe: str,
        trade_data: Dict
    ) -> bool:
        """
        Save trade to database.

        Args:
            pair: Currency pair
            timeframe: Timeframe
            trade_data: Trade data dictionary

        Returns:
            True if saved successfully
        """
        if not self.database:
            logger.warning("No database configured")
            return False

        try:
            success = self.database.insert_trade(pair, timeframe, trade_data)
            return success
        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
            return False

    def process_multiple_datasets(
        self,
        datasets: List[Dict],
        save_to_db: bool = True,
        callback: Optional[Callable] = None
    ) -> List[Dict]:
        """
        Process multiple datasets.

        Args:
            datasets: List of dicts with 'df', 'pair', 'timeframe'
            save_to_db: Save results to database
            callback: Progress callback

        Returns:
            List of result dictionaries

        Example:
            datasets = [
                {'df': df1, 'pair': 'EURUSD', 'timeframe': 'H1'},
                {'df': df2, 'pair': 'GBPUSD', 'timeframe': 'H1'},
            ]
        """
        all_results = []
        total_datasets = len(datasets)

        logger.info(f"Processing {total_datasets} datasets")

        for i, dataset in enumerate(datasets):
            logger.info(f"Dataset {i+1}/{total_datasets}: {dataset['pair']} {dataset['timeframe']}")

            result = self.process_dataset(
                df=dataset['df'],
                pair=dataset['pair'],
                timeframe=dataset['timeframe'],
                save_to_db=save_to_db,
                direction_method=dataset.get('direction_method', 'linear'),
                callback=callback
            )

            all_results.append(result)

        # Summary statistics
        total_trades = sum(r['trades_generated'] for r in all_results)
        total_saved = sum(r['trades_saved'] for r in all_results)

        logger.info(f"Batch processing complete: {total_trades} trades generated, "
                   f"{total_saved} saved to database")

        return all_results
