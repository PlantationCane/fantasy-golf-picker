"""
Database Connection Wrapper

Uses Turso HTTP API when deployed on Streamlit Cloud,
falls back to local SQLite for development/scraping.
"""

import sqlite3
import os
from pathlib import Path


class TursoConnection:
    """SQLite-compatible wrapper around Turso's HTTP API"""
    
    def __init__(self, url, token):
        import requests
        self.url = url.replace("libsql://", "https://")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
    
    def execute(self, sql, params=None):
        """Execute a SQL statement"""
        body = self._build_request(sql, params)
        resp = self.session.post(f"{self.url}/v2/pipeline", json=body)
        
        if resp.status_code != 200:
            raise Exception(f"Turso API error {resp.status_code}: {resp.text}")
        
        data = resp.json()
        results = data.get("results", [])
        
        if results and "error" in results[0]:
            error = results[0]["error"]
            raise Exception(f"SQL error: {error.get('message', str(error))}")
        
        if results and "response" in results[0]:
            response = results[0]["response"]
            result = response.get("result", {})
            return TursoCursor(result)
        
        return TursoCursor({})
    
    def _build_request(self, sql, params=None):
        """Build Turso pipeline request"""
        args = []
        if params:
            for p in params:
                if p is None:
                    args.append({"type": "null", "value": None})
                elif isinstance(p, int):
                    args.append({"type": "integer", "value": str(p)})
                elif isinstance(p, float):
                    args.append({"type": "float", "value": p})
                else:
                    args.append({"type": "text", "value": str(p)})
        
        stmt = {"type": "execute", "stmt": {"sql": sql}}
        if args:
            stmt["stmt"]["args"] = args
        
        return {"requests": [stmt]}
    
    def commit(self):
        pass
    
    def close(self):
        pass
    
    def cursor(self):
        return TursoCursorProxy(self)
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass


class TursoCursorProxy:
    """Cursor-like object for Turso"""
    
    def __init__(self, conn):
        self.conn = conn
        self._result = None
    
    def execute(self, sql, params=None):
        self._result = self.conn.execute(sql, params)
        return self
    
    def fetchone(self):
        if self._result:
            return self._result.fetchone()
        return None
    
    def fetchall(self):
        if self._result:
            return self._result.fetchall()
        return []


class TursoCursor:
    """Wraps Turso API response to look like sqlite3 cursor results"""
    
    def __init__(self, result):
        self.columns = [c.get("name", "") for c in result.get("cols", [])]
        self.rows = []
        for row in result.get("rows", []):
            parsed_row = []
            for cell in row:
                val = cell.get("value")
                cell_type = cell.get("type", "text")
                if val is None or cell_type == "null":
                    parsed_row.append(None)
                elif cell_type == "integer":
                    parsed_row.append(int(val))
                elif cell_type == "float":
                    parsed_row.append(float(val))
                else:
                    parsed_row.append(str(val))
            self.rows.append(tuple(parsed_row))
        self._index = 0
        self.description = [(c, None, None, None, None, None, None) for c in self.columns]
    
    def fetchone(self):
        if self._index < len(self.rows):
            row = self.rows[self._index]
            self._index += 1
            return row
        return None
    
    def fetchall(self):
        rows = self.rows[self._index:]
        self._index = len(self.rows)
        return rows
    
    def __iter__(self):
        return iter(self.rows)


def get_connection(db_path="pga_fantasy.db"):
    """
    Get a database connection.
    - On Streamlit Cloud: connects to Turso via HTTP API
    - Locally: connects to SQLite file
    """
    # Try Streamlit Cloud secrets first
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'TURSO_DATABASE_URL' in st.secrets:
            url = st.secrets["TURSO_DATABASE_URL"]
            token = st.secrets["TURSO_AUTH_TOKEN"]
            return TursoConnection(url, token)
    except (ImportError, Exception):
        pass
    
    # Check environment variables (for upload script)
    turso_url = os.environ.get('TURSO_DATABASE_URL')
    turso_token = os.environ.get('TURSO_AUTH_TOKEN')
    
    if turso_url and turso_token:
        return TursoConnection(turso_url, turso_token)
    
    # Fall back to local SQLite
    resolved_path = Path(db_path)
    if not resolved_path.is_absolute():
        script_dir = Path(__file__).parent
        resolved_path = script_dir / db_path
    
    return sqlite3.connect(str(resolved_path))


def get_local_connection(db_path="pga_fantasy.db"):
    """Always get a local SQLite connection (for scrapers)"""
    resolved_path = Path(db_path)
    if not resolved_path.is_absolute():
        script_dir = Path(__file__).parent
        resolved_path = script_dir / db_path
    
    return sqlite3.connect(str(resolved_path))
