"""Patch database.py to support Turso cloud DB"""

text = open('utils\\database.py', 'r').read()

# Add import
old_imports = 'import sqlite3\nimport pandas as pd'
new_imports = 'import sqlite3\nimport pandas as pd\n\ntry:\n    from db_connection import get_connection\n    HAS_DB_WRAPPER = True\nexcept ImportError:\n    HAS_DB_WRAPPER = False'
text = text.replace(old_imports, new_imports)

# Add _get_conn method after init_database call
old_init = '        self.init_database()'
new_init = '        self.init_database()\n\n    def _get_conn(self):\n        """Get database connection (cloud or local)\"""\n        if HAS_DB_WRAPPER:\n            return get_connection(str(self.db_path))\n        return sqlite3.connect(str(self.db_path))'
text = text.replace(old_init, new_init)

# Replace all sqlite3.connect calls
text = text.replace('sqlite3.connect(self.db_path)', 'self._get_conn()')

open('utils\\database.py', 'w').write(text)
print('Done! Patched database.py for cloud support.')
