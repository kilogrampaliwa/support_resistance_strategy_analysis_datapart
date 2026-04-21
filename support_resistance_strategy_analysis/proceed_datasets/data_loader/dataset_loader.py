# proceed_datasets/data_loader/dataset_loader.py

#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 13.03.2026
# Version: 1.0
# Description: Dataset Loader Module. Handles loading and validating OHLC data from input_data directory.
#####################################################


import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class DatasetLoader:
    """
    Loads OHLC datasets from input_data directory.

    Supports:
    - .txt files (tab or comma separated)
    - .csv files
    - Automatic datetime parsing
    - Data validation
    """

    REQUIRED_COLUMNS = ['open', 'high', 'low', 'close']
    DATETIME_COLUMNS = ['timestamp', 'datetime', 'date', 'time']

    def __init__(self, input_data_dir: str = "input_data"):
        """
        Initialize DatasetLoader.

        Args:
            input_data_dir: Path to input data directory
        """
        self.input_dir = Path(input_data_dir)

        if not self.input_dir.exists():
            logger.warning(f"Input directory does not exist: {self.input_dir}")
            self.input_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created input directory: {self.input_dir}")

    def list_available_files(self) -> List[Path]:
        """
        List all available data files in input directory.

        Returns:
            List of Path objects for .txt and .csv files
        """
        files = []

        # Find .txt files
        files.extend(self.input_dir.glob("*.txt"))

        # Find .csv files
        files.extend(self.input_dir.glob("*.csv"))

        files = sorted(files)
        logger.info(f"Found {len(files)} data files in {self.input_dir}")

        return files

    def load_file(
        self,
        filepath: Path,
        parse_dates: bool = True,
        validate: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Load single data file.

        Supports:
        - Files with headers
        - Files without headers (auto-detects and assigns names)
        - w_avre column (weighted average) - automatically detected and kept

        Args:
            filepath: Path to file
            parse_dates: Parse datetime column to DatetimeIndex
            validate: Validate required columns

        Returns:
            DataFrame with OHLC data, or None if failed
        """
        try:
            # Try to determine separator
            with open(filepath, 'r') as f:
                first_line = f.readline().strip()

            # Detect separator
            if '\t' in first_line:
                sep = '\t'
            elif ',' in first_line:
                sep = ','
            elif ';' in first_line:
                sep = ';'
            else:
                sep = None  # Let pandas auto-detect

            # Check if file has headers
            has_header = self._detect_header(first_line, sep)

            if has_header:
                # Load with headers
                df = pd.read_csv(filepath, sep=sep)
                # Normalize column names (lowercase)
                df.columns = df.columns.str.lower().str.strip()
            else:
                # Load without headers - assign standard names
                df = pd.read_csv(filepath, sep=sep, header=None)
                df = self._assign_column_names(df, Path(filepath).name)

            logger.info(f"Loaded {Path(filepath).name}: {len(df)} rows, columns: {list(df.columns)}")

            # Parse datetime if requested
            if parse_dates:
                df = self._parse_datetime(df, Path(filepath).name)

            # Validate if requested
            if validate:
                if not self._validate_dataframe(df, Path(filepath).name):
                    return None

            return df

        except Exception as e:
            logger.error(f"Failed to load {Path(filepath).name}: {e}")
            return None

    def _detect_header(self, first_line: str, sep: str) -> bool:
        """
        Detect if file has header row.

        Args:
            first_line: First line of file
            sep: Separator character

        Returns:
            True if file has header, False otherwise
        """
        if sep:
            parts = first_line.split(sep)
        else:
            # Try common separators
            for s in [',', '\t', ';']:
                if s in first_line:
                    parts = first_line.split(s)
                    break
            else:
                parts = [first_line]

        if not parts:
            return False

        # Check if first part looks like a datetime or number
        first_part = parts[0].strip()

        # If it starts with digit, likely no header
        if first_part and first_part[0].isdigit():
            return False

        # If contains common column names, has header
        common_names = ['timestamp', 'datetime', 'date', 'time', 'open', 'high', 'low', 'close', 'volume']
        if any(name in first_part.lower() for name in common_names):
            return True

        # Default: assume no header if first part is numeric-like
        try:
            float(first_part)
            return False
        except:
            return True

    def _assign_column_names(self, df: pd.DataFrame, filename: str) -> pd.DataFrame:
        """
        Assign standard column names to headerless file.

        Expected formats:
        - 7 columns: date, time, open, high, low, close, w_avre
        - 6 columns: datetime, open, high, low, close, w_avre
        - 6 columns: datetime, open, high, low, close, volume
        - 5 columns: datetime, open, high, low, close

        Args:
            df: DataFrame without headers
            filename: Name of file (for logging)

        Returns:
            DataFrame with assigned column names
        """
        num_cols = len(df.columns)

        logger.info(f"{filename}: No header detected, {num_cols} columns found")

        if num_cols == 7:
            # Format: date, time, open, high, low, close, w_avre
            df.columns = ['date', 'time', 'open', 'high', 'low', 'close', 'w_avre']
            # Combine date and time
            df['datetime'] = df['date'].astype(str) + df['time'].astype(str).str.zfill(6)
            df = df.drop(columns=['date', 'time'])
            # Reorder
            cols = ['datetime', 'open', 'high', 'low', 'close', 'w_avre']
            df = df[cols]
            logger.info(f"{filename}: Assigned 7-column format (date, time, OHLC, w_avre)")

        elif num_cols == 6:
            # Check if first column looks like combined datetime (YYYYMMDD)
            first_val = str(df.iloc[0, 0])
            if len(first_val) >= 8 and first_val[:8].isdigit():
                # Format: datetime, time, open, high, low, close
                # OR: datetime, open, high, low, close, w_avre/volume
                # Need to check second column
                second_val = df.iloc[0, 1]
                try:
                    # If second column is numeric and < 240000 (time), it's time column
                    if float(second_val) < 240000:
                        df.columns = ['date', 'time', 'open', 'high', 'low', 'close']
                        df['datetime'] = df['date'].astype(str) + df['time'].astype(str).str.zfill(6)
                        df = df.drop(columns=['date', 'time'])
                        df = df[['datetime', 'open', 'high', 'low', 'close']]
                        logger.info(f"{filename}: Assigned 6-column format (date, time, OHLC)")
                    else:
                        # Second column is price-like, so: datetime, OHLC, w_avre
                        df.columns = ['datetime', 'open', 'high', 'low', 'close', 'w_avre']
                        logger.info(f"{filename}: Assigned 6-column format (datetime, OHLC, w_avre)")
                except:
                    # Default to datetime, OHLC, extra
                    df.columns = ['datetime', 'open', 'high', 'low', 'close', 'w_avre']
                    logger.info(f"{filename}: Assigned 6-column format (datetime, OHLC, w_avre)")
            else:
                df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
                logger.info(f"{filename}: Assigned 6-column format (datetime, OHLC, volume)")

        elif num_cols == 5:
            # Format: datetime, open, high, low, close
            df.columns = ['datetime', 'open', 'high', 'low', 'close']
            logger.info(f"{filename}: Assigned 5-column format (datetime, OHLC)")

        else:
            logger.warning(f"{filename}: Unexpected number of columns ({num_cols}), "
                          f"assigning generic names")
            # Assign generic names
            names = ['col_' + str(i) for i in range(num_cols)]
            # Try to assign OHLC to middle columns
            if num_cols >= 5:
                names[0] = 'datetime'
                names[1] = 'open'
                names[2] = 'high'
                names[3] = 'low'
                names[4] = 'close'
            df.columns = names

        return df

    def _parse_datetime(self, df: pd.DataFrame, filename: str) -> pd.DataFrame:
        """
        Parse datetime column and set as index.

        Supports multiple formats:
        - Standard: "2024-01-01 00:00:00"
        - Combined: "20240101000000" (YYYYMMDDHHMMSS)
        - Date only: "20240101" (YYYYMMDD) - assumes 00:00:00

        Args:
            df: DataFrame
            filename: Name of file (for logging)

        Returns:
            DataFrame with DatetimeIndex
        """
        # Find datetime column
        datetime_col = None
        for col in self.DATETIME_COLUMNS:
            if col in df.columns:
                datetime_col = col
                break

        if datetime_col is None:
            # Try first column if it looks like datetime
            first_col = df.columns[0]
            try:
                # Test if parseable
                self._try_parse_datetime(df[first_col].iloc[0])
                datetime_col = first_col
                logger.info(f"{filename}: Using first column '{first_col}' as datetime")
            except:
                logger.warning(f"{filename}: No datetime column found")
                return df

        # Parse datetime
        try:
            # Check format
            sample = str(df[datetime_col].iloc[0])

            if len(sample) >= 14 and sample[:14].isdigit():
                # Format: YYYYMMDDHHMMSS (e.g., "20010131000000")
                df[datetime_col] = pd.to_datetime(df[datetime_col], format='%Y%m%d%H%M%S')
                logger.info(f"{filename}: Parsed as YYYYMMDDHHMMSS format")

            elif len(sample) == 8 and sample.isdigit():
                # Format: YYYYMMDD (e.g., "20010131")
                df[datetime_col] = pd.to_datetime(df[datetime_col], format='%Y%m%d')
                logger.info(f"{filename}: Parsed as YYYYMMDD format")

            else:
                # Try pandas auto-parsing
                df[datetime_col] = pd.to_datetime(df[datetime_col])
                logger.info(f"{filename}: Parsed with pandas auto-detect")

            df.set_index(datetime_col, inplace=True)
            df.sort_index(inplace=True)
            logger.info(f"{filename}: DateTime range: {df.index[0]} to {df.index[-1]}")

        except Exception as e:
            logger.error(f"{filename}: Failed to parse datetime: {e}")
            logger.debug(f"Sample value: {df[datetime_col].iloc[0]}")

        return df

    def _try_parse_datetime(self, value):
        """
        Try to parse a single datetime value.

        Args:
            value: Value to parse

        Raises:
            Exception if not parseable
        """
        value_str = str(value)

        # Try different formats
        if len(value_str) >= 14 and value_str[:14].isdigit():
            pd.to_datetime(value_str, format='%Y%m%d%H%M%S')
        elif len(value_str) == 8 and value_str.isdigit():
            pd.to_datetime(value_str, format='%Y%m%d')
        else:
            pd.to_datetime(value_str)

    def _validate_dataframe(self, df: pd.DataFrame, filename: str) -> bool:
        """
        Validate DataFrame has required OHLC columns.

        Args:
            df: DataFrame to validate
            filename: Name of file (for logging)

        Returns:
            True if valid, False otherwise
        """
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]

        if missing_cols:
            logger.error(f"{filename}: Missing required columns: {missing_cols}")
            return False

        # Check for NaN values
        nan_counts = df[self.REQUIRED_COLUMNS].isna().sum()
        if nan_counts.any():
            logger.warning(f"{filename}: Found NaN values: {nan_counts[nan_counts > 0].to_dict()}")

        # Check data types
        for col in self.REQUIRED_COLUMNS:
            if not pd.api.types.is_numeric_dtype(df[col]):
                logger.error(f"{filename}: Column '{col}' is not numeric: {df[col].dtype}")
                return False

        # Check DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            logger.warning(f"{filename}: Index is not DatetimeIndex: {type(df.index)}")

        logger.info(f"{filename}: Validation passed")
        return True

    def get_file_info(self, filepath: Path) -> Dict:
        """
        Get information about a file without loading all data.

        Args:
            filepath: Path to file

        Returns:
            Dictionary with file information
        """
        info = {
            'filename': filepath.name,
            'path': str(filepath),
            'exists': filepath.exists()
        }

        # Check if file exists before accessing
        if not filepath.exists():
            info['size_mb'] = 0
            return info

        info['size_mb'] = filepath.stat().st_size / (1024 * 1024)

        try:
            # Load just first few rows to get info
            df_sample = pd.read_csv(filepath, nrows=10)
            df_sample.columns = df_sample.columns.str.lower().str.strip()

            info['columns'] = list(df_sample.columns)
            info['has_ohlc'] = all(col in df_sample.columns for col in self.REQUIRED_COLUMNS)

            # Try to get total row count
            with open(filepath) as f:
                row_count = sum(1 for line in f) - 1  # -1 for header
            info['rows'] = row_count

        except Exception as e:
            logger.error(f"Failed to get info for {filepath.name}: {e}")
            info['error'] = str(e)

        return info
