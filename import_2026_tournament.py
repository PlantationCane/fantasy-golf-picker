"""
Import 2026 Tournament Results from CSV

Imports complete tournament results including:
- Leaderboard (finish, score, earnings, FedEx points)
- Strokes Gained stats (if available)
- Automatically calculates recent form

Usage: python import_2026_tournament.py tournament_results.csv
"""

import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
import sys

class Tournament2026Importer:
    """Import 2026 tournament results from CSV"""
    
    def __init__(self, db_path="pga_fantasy.db"):
        self.db_path = Path(__file__).parent / db_path
        self.init_tables()
    
    def init_tables(self):
        """Initialize 2026 tournament tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 2026 tournament results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tournament_results_2026 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT NOT NULL,
                    tournament_name TEXT NOT NULL,
                    finish_position TEXT,
                    score_to_par INTEGER,
                    total_strokes INTEGER,
                    round1 INTEGER,
                    round2 INTEGER,
                    round3 INTEGER,
                    round4 INTEGER,
                    earnings REAL,
                    fedex_points REAL,
                    sg_total REAL,
                    sg_ott REAL,
                    sg_app REAL,
                    sg_arg REAL,
                    sg_putt REAL,
                    made_cut BOOLEAN,
                    tournament_date DATE,
                    UNIQUE(player_name, tournament_name)
                )
            """)
            
            # Player recent form
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_recent_form (
                    player_name TEXT PRIMARY KEY,
                    events_played INTEGER,
                    avg_finish REAL,
                    avg_sg_total REAL,
                    best_finish TEXT,
                    cuts_made INTEGER,
                    top_10s INTEGER,
                    form_rating TEXT,
                    last_updated TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def import_csv(self, csv_path, tournament_name=None, tournament_date=None):
        """Import tournament results from CSV"""
        print("\n" + "="*60)
        print("📥 IMPORT 2026 TOURNAMENT")
        print("="*60)
        
        csv_path = Path(csv_path)
        if not csv_path.exists():
            print(f"\n❌ Error: File not found: {csv_path}")
            return False
        
        print(f"\n📂 Loading: {csv_path.name}")
        
        try:
            # Read CSV (handle both CSV and TSV)
            if csv_path.suffix.lower() in ['.tsv', '.txt']:
                df = pd.read_csv(csv_path, sep='\t')
            else:
                df = pd.read_csv(csv_path)
            
            print(f"✅ Loaded {len(df)} rows")
            print(f"\n📋 Columns found:")
            for i, col in enumerate(df.columns, 1):
                print(f"  {i}. {col}")
            
            # Get tournament info
            if not tournament_name:
                print(f"\n📝 Enter tournament name:")
                tournament_name = input("  > ").strip()
                if not tournament_name:
                    tournament_name = "Unknown Tournament"
            
            if not tournament_date:
                print(f"\n📅 Enter tournament date (YYYY-MM-DD, or press Enter for today):")
                tournament_date = input("  > ").strip()
                if not tournament_date:
                    tournament_date = datetime.now().strftime('%Y-%m-%d')
            
            # Detect column mappings
            column_map = self._detect_columns(df)
            
            print(f"\n📊 Detected columns:")
            for key, val in column_map.items():
                if val:
                    print(f"  {key}: {val}")
            
            # Check if we have required columns
            if not column_map.get('player_name'):
                print(f"\n❌ Error: Could not find player name column")
                print(f"Available columns: {', '.join(df.columns)}")
                return False
            
            # Import data
            print(f"\n⏳ Importing tournament results...")
            imported = self._import_results(df, column_map, tournament_name, tournament_date)
            
            print(f"\n✅ Imported {imported} player results for {tournament_name}")
            
            # Recalculate recent form
            print(f"\n📊 Recalculating recent form for all players...")
            self.calculate_recent_form()
            
            print("\n" + "="*60)
            print("✅ IMPORT COMPLETE!")
            print("="*60)
            print(f"\nTournament: {tournament_name}")
            print(f"Date: {tournament_date}")
            print(f"Players: {imported}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error importing: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _detect_columns(self, df):
        """Auto-detect column names"""
        column_map = {}
        
        # Common variations for each field
        mappings = {
            'player_name': ['player', 'name', 'player name', 'golfer'],
            'finish_position': ['pos', 'position', 'finish', 'place', 'rank'],
            'score_to_par': ['to par', 'score', 'total score', 'par'],
            'total_strokes': ['total', 'strokes', 'total strokes'],
            'round1': ['r1', 'round 1', 'round1', 'rd1'],
            'round2': ['r2', 'round 2', 'round2', 'rd2'],
            'round3': ['r3', 'round 3', 'round3', 'rd3'],
            'round4': ['r4', 'round 4', 'round4', 'rd4'],
            'earnings': ['earnings', 'money', 'prize', 'winnings'],
            'fedex_points': ['fedex', 'points', 'fedex points', 'fedexcup points'],
            'sg_total': ['sg total', 'sg: total', 'strokes gained total'],
            'sg_ott': ['sg ott', 'sg: ott', 'sg off the tee'],
            'sg_app': ['sg app', 'sg: app', 'sg approach'],
            'sg_arg': ['sg arg', 'sg: arg', 'sg around green'],
            'sg_putt': ['sg putt', 'sg: putt', 'sg putting']
        }
        
        for field, variations in mappings.items():
            for col in df.columns:
                col_lower = col.lower().strip()
                if any(var in col_lower for var in variations):
                    column_map[field] = col
                    break
        
        return column_map
    
    def _import_results(self, df, column_map, tournament_name, tournament_date):
        """Import results to database"""
        imported = 0
        
        with sqlite3.connect(self.db_path) as conn:
            # Convert to records for easier access
            records = df.to_dict('records')
            
            for row in records:
                try:
                    # Extract player name
                    player_name = str(row.get(column_map.get('player_name', ''), ''))
                    if not player_name or player_name == 'nan':
                        continue
                    
                    # Extract other fields
                    finish_position = str(row.get(column_map.get('finish_position', ''), '')) if column_map.get('finish_position') else None
                    score_to_par = self._safe_int(row.get(column_map.get('score_to_par', '')))
                    total_strokes = self._safe_int(row.get(column_map.get('total_strokes', '')))
                    round1 = self._safe_int(row.get(column_map.get('round1', '')))
                    round2 = self._safe_int(row.get(column_map.get('round2', '')))
                    round3 = self._safe_int(row.get(column_map.get('round3', '')))
                    round4 = self._safe_int(row.get(column_map.get('round4', '')))
                    earnings = self._safe_float(row.get(column_map.get('earnings', '')))
                    fedex_points = self._safe_float(row.get(column_map.get('fedex_points', '')))
                    sg_total = self._safe_float(row.get(column_map.get('sg_total', '')))
                    sg_ott = self._safe_float(row.get(column_map.get('sg_ott', '')))
                    sg_app = self._safe_float(row.get(column_map.get('sg_app', '')))
                    sg_arg = self._safe_float(row.get(column_map.get('sg_arg', '')))
                    sg_putt = self._safe_float(row.get(column_map.get('sg_putt', '')))
                    
                    # Determine made cut
                    made_cut = True
                    if finish_position:
                        pos_str = str(finish_position).upper()
                        if pos_str in ['MC', 'WD', 'DQ', 'CUT']:
                            made_cut = False
                    
                    # Insert
                    conn.execute("""
                        INSERT OR REPLACE INTO tournament_results_2026
                        (player_name, tournament_name, finish_position, score_to_par,
                         total_strokes, round1, round2, round3, round4, earnings,
                         fedex_points, sg_total, sg_ott, sg_app, sg_arg, sg_putt,
                         made_cut, tournament_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (player_name, tournament_name, finish_position, score_to_par,
                          total_strokes, round1, round2, round3, round4, earnings,
                          fedex_points, sg_total, sg_ott, sg_app, sg_arg, sg_putt,
                          made_cut, tournament_date))
                    
                    imported += 1
                    
                except Exception as e:
                    print(f"  Error importing {player_name}: {e}")
                    continue
            
            conn.commit()
        
        return imported
    
    def _safe_int(self, value):
        """Safely convert to int"""
        try:
            if pd.isna(value) or value == '':
                return None
            # Remove non-numeric characters
            cleaned = str(value).replace(',', '').replace('$', '').strip()
            return int(float(cleaned))
        except:
            return None
    
    def _safe_float(self, value):
        """Safely convert to float"""
        try:
            if pd.isna(value) or value == '':
                return None
            # Remove non-numeric characters
            cleaned = str(value).replace(',', '').replace('$', '').strip()
            return float(cleaned)
        except:
            return None
    
    def calculate_recent_form(self):
        """Calculate recent form for all players"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all players
            cursor.execute("SELECT DISTINCT player_name FROM tournament_results_2026")
            players = [row[0] for row in cursor.fetchall()]
            
            for player in players:
                # Get last 5 tournaments
                cursor.execute("""
                    SELECT finish_position, sg_total, made_cut
                    FROM tournament_results_2026
                    WHERE player_name = ?
                    ORDER BY tournament_date DESC
                    LIMIT 5
                """, (player,))
                
                recent_events = cursor.fetchall()
                
                if not recent_events:
                    continue
                
                events_played = len(recent_events)
                cuts_made = sum(1 for e in recent_events if e[2] == 1)
                
                # Calculate stats
                finishes = []
                sg_totals = []
                top_10s = 0
                
                for finish, sg, made_cut in recent_events:
                    if made_cut and finish and finish not in ['MC', 'WD', 'DQ']:
                        try:
                            finish_num = int(str(finish).replace('T', ''))
                            finishes.append(finish_num)
                            if finish_num <= 10:
                                top_10s += 1
                        except:
                            pass
                    
                    if sg:
                        sg_totals.append(float(sg))
                
                avg_finish = sum(finishes) / len(finishes) if finishes else None
                avg_sg = sum(sg_totals) / len(sg_totals) if sg_totals else None
                best_finish = min(finishes) if finishes else None
                
                # Form rating
                form_rating = 'Unknown'
                if avg_sg is not None:
                    if avg_sg >= 1.5:
                        form_rating = '🔥 Excellent'
                    elif avg_sg >= 0.5:
                        form_rating = '✅ Good'
                    elif avg_sg >= -0.5:
                        form_rating = '🔶 Average'
                    else:
                        form_rating = '🔻 Poor'
                
                # Insert
                cursor.execute("""
                    INSERT OR REPLACE INTO player_recent_form
                    (player_name, events_played, avg_finish, avg_sg_total,
                     best_finish, cuts_made, top_10s, form_rating, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (player, events_played, avg_finish, avg_sg,
                      str(best_finish) if best_finish else None, cuts_made, top_10s, form_rating))
            
            conn.commit()
            
            cursor.execute("SELECT COUNT(*) FROM player_recent_form")
            count = cursor.fetchone()[0]
            print(f"✅ Updated form for {count} players")

def main():
    if len(sys.argv) < 2:
        print("="*60)
        print("📥 2026 TOURNAMENT CSV IMPORTER")
        print("="*60)
        print("\nUsage: python import_2026_tournament.py <csv_file>")
        print("\nExample:")
        print("  python import_2026_tournament.py farmers_results.csv")
        print("\nThe CSV should have columns like:")
        print("  Player Name, Position, Score, Earnings, FedEx Points")
        print("="*60)
        return
    
    csv_path = sys.argv[1]
    
    importer = Tournament2026Importer()
    
    if importer.import_csv(csv_path):
        print("\n✅ Success! Data imported.")
        print("\n📱 Restart your app to see updated stats:")
        print("  streamlit run app.py")
    else:
        print("\n❌ Import failed")

if __name__ == "__main__":
    main()
