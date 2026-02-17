"""
Upload Local Database to Turso Cloud (Fast Version)

Usage: 
  set TURSO_AUTH_TOKEN=your_token
  python upload_to_turso.py              (weekly tables only - fast)
  python upload_to_turso.py --all        (includes historical - slow, one time only)
"""

import sqlite3
import os
import sys
import requests
from pathlib import Path

TURSO_URL = "https://pga-fantasy-plantationcane.aws-us-east-1.turso.io"
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

WEEKLY_TABLES = [
    'tournament_results_2026',
    'player_stats',
    'player_recent_form',
    'picks',
    'used_players',
]

HISTORICAL_TABLES = [
    'historical_results',
    'course_history',
]


class TursoUploader:
    def __init__(self, url, token):
        self.url = url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
    
    def _make_arg(self, p):
        """Convert a Python value to Turso API arg format"""
        if p is None:
            return {"type": "null"}
        elif isinstance(p, bool):
            return {"type": "integer", "value": str(int(p))}
        elif isinstance(p, int):
            return {"type": "integer", "value": str(p)}
        elif isinstance(p, float):
            return {"type": "float", "value": p}
        else:
            return {"type": "text", "value": str(p)}
    
    def execute_batch(self, statements):
        requests_list = []
        for sql, params in statements:
            args = [self._make_arg(p) for p in params] if params else []
            stmt = {"type": "execute", "stmt": {"sql": sql}}
            if args:
                stmt["stmt"]["args"] = args
            requests_list.append(stmt)
        
        body = {"requests": requests_list}
        resp = self.session.post(f"{self.url}/v2/pipeline", json=body, timeout=120)
        
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}: {resp.text[:300]}")
        
        data = resp.json()
        # Check for individual statement errors
        for i, result in enumerate(data.get("results", [])):
            if "error" in result:
                raise Exception(f"Statement {i} error: {result['error']}")
        
        return data
    
    def execute(self, sql, params=None):
        return self.execute_batch([(sql, params)])


def get_local_db():
    db_path = Path(__file__).parent / "pga_fantasy.db"
    if not db_path.exists():
        print(f"Error: not found: {db_path}")
        sys.exit(1)
    return sqlite3.connect(str(db_path))


def sync_table(local_conn, turso, table_name):
    cursor = local_conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    if cursor.fetchone()[0] == 0:
        print(f"   Skipping '{table_name}' (not found)")
        return 0
    
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    local_count = cursor.fetchone()[0]
    if local_count == 0:
        print(f"   Skipping '{table_name}' (empty)")
        return 0
    
    print(f"   {table_name}: {local_count} rows...", flush=True)
    
    # Create table in Turso (drop and recreate for clean sync)
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    schema = cursor.fetchone()[0]
    
    try:
        turso.execute(f"DROP TABLE IF EXISTS {table_name}")
    except:
        pass
    turso.execute(schema)
    
    # Get data
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    cursor.execute(f"PRAGMA table_info({table_name})")
    num_cols = len(cursor.fetchall())
    placeholders = ','.join(['?' for _ in range(num_cols)])
    insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
    
    # Upload in batches
    batch_size = 200
    inserted = 0
    errors = 0
    
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        statements = [(insert_sql, list(row)) for row in batch]
        
        try:
            turso.execute_batch(statements)
            inserted += len(batch)
        except Exception as e:
            # Retry one at a time
            for sql, params in statements:
                try:
                    turso.execute(sql, params)
                    inserted += 1
                except Exception as e2:
                    errors += 1
        
        pct = min(100, int((i + batch_size) / len(rows) * 100))
        print(f"\r   {table_name}: {pct}% ({inserted}/{local_count})", end="", flush=True)
    
    suffix = f" ({errors} errors)" if errors else ""
    print(f"\r   {table_name}: done - {inserted} rows{suffix}          ")
    return inserted


def main():
    include_historical = '--all' in sys.argv
    
    print("=" * 60)
    if include_historical:
        print("   FULL UPLOAD (including historical - one time)")
    else:
        print("   WEEKLY UPLOAD (fast)")
    print("=" * 60)
    
    if not TURSO_TOKEN:
        print("\nError: TURSO_AUTH_TOKEN not set!")
        print("Run: set TURSO_AUTH_TOKEN=your_token_here")
        sys.exit(1)
    
    local_conn = get_local_db()
    turso = TursoUploader(TURSO_URL, TURSO_TOKEN)
    
    try:
        turso.execute("SELECT 1")
        print("Cloud connection OK\n")
    except Exception as e:
        print(f"Error connecting: {e}")
        sys.exit(1)
    
    tables = WEEKLY_TABLES + (HISTORICAL_TABLES if include_historical else [])
    
    total = 0
    for table in tables:
        total += sync_table(local_conn, turso, table)
    
    print(f"\n{'=' * 60}")
    print(f"Done! {total} rows uploaded")
    if not include_historical:
        print("(Run with --all to include historical data - one time only)")
    print(f"{'=' * 60}")
    
    local_conn.close()


if __name__ == "__main__":
    main()
