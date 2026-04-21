# database_handling/database_cleaner/database_cleaner.py

#####################################################
# Module verified by: kilogrampaliwa
# Date of verification: 13.03.2026
# Version: 1.0
# Description: Database cleaning utilities for TradingDatabase compatibility
#####################################################


"""
Database cleaning utilities - FIXED for TradingDatabase compatibility
"""

import logging
import gc
from typing import Optional

logger = logging.getLogger(__name__)


class DatabaseCleaner:
    """Handles database cleanup operations for single or multiple tables"""

    def __init__(self, db_interface):
        """
        Args:
            db_interface: TradingDatabase instance with db_manager
        """
        self.db_interface = db_interface
        # Extract db_manager for compatibility with TradingDatabase
        self.db_manager = getattr(db_interface, 'db_manager', None)

        if not self.db_manager:
            raise ValueError("db_interface must have 'db_manager' attribute")

    def truncate_table(self, table_name: str) -> bool:
        """
        Truncates a specific table.

        Args:
            table_name: Name of table to truncate

        Returns:
            True if successful, False otherwise
        """
        if not self.db_manager:
            logger.error("No database manager available")
            return False

        try:
            logger.info(f"Truncating {table_name} table...")

            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Count before
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count_before = cursor.fetchone()[0]
                    logger.info(f"  Rows before: {count_before}")

                    # Truncate
                    cursor.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE")
                    conn.commit()

                    # Count after
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count_after = cursor.fetchone()[0]
                    logger.info(f"  Rows after: {count_after}")

            logger.info(f"✓ Table {table_name} truncated successfully")
            return True

        except Exception as e:
            logger.error(f"Error truncating table {table_name}: {e}")
            return False

    def clean_all_trade_tables(self) -> dict:
        """
        Truncates ALL tables starting with 'trades_'.

        Returns:
            Dictionary with results per table
        """
        logger.info("=" * 60)
        logger.info("CLEANING ALL TRADE TABLES")
        logger.info("=" * 60)

        results = {}

        try:
            # Get list of all trade tables
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT tablename
                        FROM pg_tables
                        WHERE schemaname = 'public'
                          AND tablename LIKE 'trades_%'
                        ORDER BY tablename
                    """)
                    tables = [row[0] for row in cursor.fetchall()]

            logger.info(f"Found {len(tables)} trade tables to clean")

            # Clean each table
            for table in tables:
                success = self.truncate_table(table)
                results[table] = "SUCCESS" if success else "FAILED"

            logger.info("=" * 60)
            logger.info("ALL TABLES CLEANED")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error cleaning all tables: {e}")

        return results

    def vacuum_analyze(self, table_name: Optional[str] = None) -> bool:
        """
        Runs VACUUM ANALYZE on specific table or entire database.

        Args:
            table_name: Table to vacuum, or None for entire database

        Returns:
            True if successful
        """
        try:
            logger.info("Running VACUUM ANALYZE...")

            with self.db_manager.get_connection() as conn:
                # VACUUM cannot run inside transaction block
                old_isolation = conn.isolation_level
                conn.set_isolation_level(0)  # autocommit

                with conn.cursor() as cursor:
                    if table_name:
                        cursor.execute(f"VACUUM ANALYZE {table_name}")
                        logger.info(f"✓ VACUUM completed for {table_name}")
                    else:
                        cursor.execute("VACUUM ANALYZE")
                        logger.info("✓ VACUUM completed for entire database")

                conn.set_isolation_level(old_isolation)

            return True

        except Exception as e:
            logger.error(f"Error running VACUUM: {e}")
            return False

    def clear_python_cache(self) -> int:
        """
        Clears Python's garbage collector cache.

        Returns:
            Number of objects collected
        """
        logger.info("Clearing Python cache...")
        collected = gc.collect()
        logger.info(f"  Collected {collected} objects")
        logger.info("✓ Python cache cleared")
        return collected

    def verify_empty(self, table_name: str) -> bool:
        """
        Verifies that a table is empty.

        Args:
            table_name: Table to check

        Returns:
            True if table is empty (0 rows)
        """
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]

                    if count == 0:
                        logger.info(f"  ✓ {table_name} is clean (0 rows)")
                        return True
                    else:
                        logger.warning(f"  ✗ {table_name} still has {count} rows")
                        return False

        except Exception as e:
            logger.error(f"Error verifying {table_name}: {e}")
            return False

    def full_cleanup(self, table_name: str) -> bool:
        """
        Complete cleanup procedure for a specific table:
        1. Truncate table
        2. VACUUM ANALYZE
        3. Clear Python cache
        4. Verify empty

        Args:
            table_name: Table to clean

        Returns:
            True if all steps successful
        """
        logger.info("=" * 60)
        logger.info(f"STARTING DATABASE CLEANUP: {table_name}")
        logger.info("=" * 60)

        success = True

        # Step 1: Truncate
        if not self.truncate_table(table_name):
            success = False

        # Step 2: VACUUM
        if not self.vacuum_analyze(table_name):
            success = False

        # Step 3: Python cache
        self.clear_python_cache()

        # Step 4: Verify
        logger.info("Verifying cleanup...")
        if not self.verify_empty(table_name):
            success = False

        if success:
            logger.info(f"✓ DATABASE CLEANUP COMPLETED SUCCESSFULLY: {table_name}")
        else:
            logger.warning(f"⚠ DATABASE CLEANUP HAD ISSUES: {table_name}")

        logger.info("=" * 60)

        return success


# Standalone function for backward compatibility
def clean_database(db_interface, table_name: str = "trades_analysis") -> bool:
    """
    Convenience function for cleaning a specific table.

    Args:
        db_interface: TradingDatabase instance
        table_name: Table to clean

    Returns:
        True if successful
    """
    cleaner = DatabaseCleaner(db_interface)
    return cleaner.full_cleanup(table_name)
