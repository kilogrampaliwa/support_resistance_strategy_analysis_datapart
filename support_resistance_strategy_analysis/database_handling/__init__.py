# database_handling/__init__.py

"""
Database Handling Module for Trading Analysis

Provides complete PostgreSQL database management for storing
and analyzing trading strategy results.

Main components:
- DatabaseManager: Connection and table management
- DataOperations: CRUD operations
- QueryBuilder: Advanced queries and analytics
- TradingDatabase: Unified high-level interface

Quick start:
    from database_handling import TradingDatabase
    
    db = TradingDatabase(
        host="localhost",
        database="trading_analysis",
        user="postgres",
        password="your_password"
    )
    
    # Insert trade
    db.insert_trade("EURUSD", "H1", trade_data)
    
    # Query trades
    df = db.get_trades("EURUSD", "H1")
    
    # Get statistics
    stats = db.get_performance_stats("EURUSD", "H1")
"""

from database_handling.database_interface import TradingDatabase, connect_to_database
from database_handling.database_manager.database_manager import DatabaseManager
from database_handling.data_operations.data_operations import DataOperations
from database_handling.query_builder.query_builder import QueryBuilder

__all__ = [
    'TradingDatabase',
    'connect_to_database',
    'DatabaseManager',
    'DataOperations',
    'QueryBuilder'
]

__version__ = '1.0.0'
