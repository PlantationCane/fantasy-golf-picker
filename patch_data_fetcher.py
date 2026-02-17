"""Patch data_fetcher.py to support Turso cloud DB"""

text = open('utils\\data_fetcher.py', 'r').read()

# Add import block after existing imports
old_imports = 'import sqlite3\nimport json\nimport time'
new_imports = '''import sqlite3
import json
import time

try:
    from db_connection import get_connection
    HAS_DB_WRAPPER = True
except ImportError:
    HAS_DB_WRAPPER = False'''
text = text.replace(old_imports, new_imports)

# Add _get_conn method after db_path line
old_init = "        self.db_path = Path(__file__).parent.parent / \"pga_fantasy.db\""
new_init = '''        self.db_path = Path(__file__).parent.parent / "pga_fantasy.db"

    def _get_conn(self):
        """Get database connection (cloud or local)"""
        if HAS_DB_WRAPPER:
            return get_connection(str(self.db_path))
        return sqlite3.connect(str(self.db_path))'''
text = text.replace(old_init, new_init)

# Replace all sqlite3.connect calls with _get_conn
text = text.replace('sqlite3.connect(self.db_path)', 'self._get_conn()')

open('utils\\data_fetcher.py', 'w').write(text)

# Verify
count = text.count('_get_conn')
print(f'Done! Patched data_fetcher.py ({count} references to _get_conn)')
