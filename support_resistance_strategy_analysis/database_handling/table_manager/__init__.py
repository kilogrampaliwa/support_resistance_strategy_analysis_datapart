# database_handling/table_manager/__init__.py
"""
Table manager module for dynamic multi-configuration storage.
"""

from .table_manager import (
    generate_table_name_from_config,
    create_table_if_not_exists,
    create_indices,
    get_table_info,
    list_all_trade_tables,
    drop_table,
    create_new_schema_table,
    insert_new_schema_row,
)

__all__ = [
    'generate_table_name_from_config',
    'create_table_if_not_exists',
    'create_indices',
    'get_table_info',
    'list_all_trade_tables',
    'drop_table',
    'create_new_schema_table',
    'insert_new_schema_row',
]