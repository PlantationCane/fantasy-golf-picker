import sqlite3
import pandas as pd

try:
    from db_connection import get_connection
    HAS_DB_WRAPPER = True
except ImportError:
    HAS_DB_WRAPPER = False
from datetime import datetime
from pathlib import Path

class DatabaseManager:
    """Manages SQLite database for player picks and history"""
    
    def __init__(self, db_path="pga_fantasy.db"):
        self.db_path = Path(__file__).parent.parent / db_path
        self.init_database()

    def _get_conn(self):
        """Get database connection (cloud or local)"""
        if HAS_DB_WRAPPER:
            return get_connection(str(self.db_path))
        return sqlite3.connect(str(self.db_path))
    
    def init_database(self):
        """Initialize database tables"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # Picks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS picks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT NOT NULL,
                    tournament_name TEXT NOT NULL,
                    tournament_date DATE NOT NULL,
                    pick_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finish_position INTEGER,
                    money_won REAL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Used players tracking (for quick lookups)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS used_players (
                    player_name TEXT PRIMARY KEY,
                    tournament_name TEXT NOT NULL,
                    week_used TEXT NOT NULL,
                    pick_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Player stats cache (to reduce API calls)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_stats_cache (
                    player_name TEXT PRIMARY KEY,
                    stats_json TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def add_pick(self, player_name, tournament_name, tournament_date=None):
        """Add a new player pick"""
        if tournament_date is None:
            tournament_date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                # Check if player already used
                cursor.execute(
                    "SELECT player_name FROM used_players WHERE player_name = ?",
                    (player_name,)
                )
                if cursor.fetchone():
                    return False
                
                # Add to picks
                cursor.execute("""
                    INSERT INTO picks (player_name, tournament_name, tournament_date)
                    VALUES (?, ?, ?)
                """, (player_name, tournament_name, tournament_date))
                
                # Add to used_players
                week_used = datetime.now().strftime("%Y-W%U")
                cursor.execute("""
                    INSERT INTO used_players (player_name, tournament_name, week_used)
                    VALUES (?, ?, ?)
                """, (player_name, tournament_name, week_used))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding pick: {e}")
            return False
    
    def is_player_used(self, player_name):
        """Check if player has already been picked"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT player_name FROM used_players WHERE player_name = ?",
                (player_name,)
            )
            return cursor.fetchone() is not None
    
    def get_used_players(self):
        """Get list of all used players"""
        with self._get_conn() as conn:
            df = pd.read_sql_query(
                "SELECT player_name FROM used_players",
                conn
            )
            return df['player_name'].tolist() if not df.empty else []
    
    def get_player_used_week(self, player_name):
        """Get the tournament name when player was used"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT tournament_name FROM used_players WHERE player_name = ?",
                (player_name,)
            )
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_picks_count(self):
        """Get total number of picks made"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM picks")
            return cursor.fetchone()[0]
    
    def get_all_picks(self):
        """Get all picks with details"""
        with self._get_conn() as conn:
            return pd.read_sql_query("""
                SELECT 
                    player_name as 'Player',
                    tournament_name as 'Tournament',
                    tournament_date as 'Date',
                    finish_position as 'Finish',
                    money_won as 'Money Won',
                    pick_date as 'Pick Date'
                FROM picks
                ORDER BY tournament_date DESC
            """, conn)
    
    def update_pick_results(self, player_name, tournament_name, finish_position, money_won):
        """Update pick with tournament results"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE picks 
                    SET finish_position = ?, 
                        money_won = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE player_name = ? AND tournament_name = ?
                """, (finish_position, money_won, player_name, tournament_name))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating pick results: {e}")
            return False
    
    def cache_player_stats(self, player_name, stats_json):
        """Cache player stats to reduce API calls"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO player_stats_cache (player_name, stats_json, last_updated)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (player_name, stats_json))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error caching stats: {e}")
            return False
    
    def get_cached_player_stats(self, player_name, max_age_hours=24):
        """Get cached player stats if fresh enough"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT stats_json, last_updated
                FROM player_stats_cache
                WHERE player_name = ?
                AND datetime(last_updated) > datetime('now', '-' || ? || ' hours')
            """, (player_name, max_age_hours))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def clear_season_data(self):
        """Clear all picks for new season (use with caution!)"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM picks")
                cursor.execute("DELETE FROM used_players")
                conn.commit()
                return True
        except Exception as e:
            print(f"Error clearing season data: {e}")
            return False
    
    def add_historical_picks(self, picks_data):
        """Bulk add historical picks (for initial setup)"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                
                for pick in picks_data:
                    # Add to picks
                    cursor.execute("""
                        INSERT INTO picks (player_name, tournament_name, tournament_date)
                        VALUES (?, ?, ?)
                    """, (pick['player_name'], pick['tournament_name'], pick['tournament_date']))
                    
                    # Add to used_players
                    cursor.execute("""
                        INSERT OR IGNORE INTO used_players (player_name, tournament_name, week_used)
                        VALUES (?, ?, ?)
                    """, (pick['player_name'], pick['tournament_name'], pick.get('week_used', 'Historical')))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding historical picks: {e}")
            return False
