"""
Kaggle Historical Data Importer

One-time import of PGA Tour historical results (2015-2025)
Provides course history for every player at every venue

Download the dataset first from:
https://www.kaggle.com/datasets/cviaxmiwnptr/pga-tour-results-2001-to-may-2024
(or similar comprehensive historical dataset)

Then run: python import_kaggle_historical.py
"""

import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime

class KaggleHistoricalImporter:
    """Imports historical tournament data from Kaggle CSV"""
    
    def __init__(self, db_path="pga_fantasy.db"):
        self.db_path = Path(__file__).parent / db_path
        self.init_tables()
    
    def init_tables(self):
        """Initialize tables for historical data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Historical tournament results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historical_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT NOT NULL,
                    tournament_name TEXT NOT NULL,
                    course_name TEXT,
                    year INTEGER,
                    finish_position TEXT,
                    score TEXT,
                    earnings REAL,
                    sg_total REAL,
                    made_cut BOOLEAN,
                    UNIQUE(player_name, tournament_name, year)
                )
            """)
            
            # Course history summary (for fast lookups)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS course_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT NOT NULL,
                    course_name TEXT NOT NULL,
                    appearances INTEGER DEFAULT 0,
                    wins INTEGER DEFAULT 0,
                    top_5s INTEGER DEFAULT 0,
                    top_10s INTEGER DEFAULT 0,
                    made_cuts INTEGER DEFAULT 0,
                    avg_finish REAL,
                    best_finish TEXT,
                    last_played INTEGER,
                    UNIQUE(player_name, course_name)
                )
            """)
            
            conn.commit()
            print("✅ Database tables initialized")
    
    def import_csv(self, csv_file):
        """Import tournament results from Kaggle CSV"""
        print(f"\n📥 Importing from: {csv_file}")
        
        try:
            # Read CSV or TSV file
            if csv_file.endswith('.tsv') or csv_file.endswith('.txt'):
                df = pd.read_csv(csv_file, sep='\t')
                print(f"   Loaded TSV with {len(df):,} rows")
            else:
                df = pd.read_csv(csv_file)
                print(f"   Loaded CSV with {len(df):,} rows")
            
            # Show columns to help map
            print(f"   Columns found: {', '.join(df.columns.tolist())}")
            
            # Standardize column names (common variations)
            column_mapping = {
                'name': 'player_name',
                'Player': 'player_name',
                'Player Name': 'player_name',
                'player': 'player_name',
                'tournament': 'tournament_name',
                'Tournament': 'tournament_name',
                'Tournament Name': 'tournament_name',
                'Event': 'tournament_name',
                'location': 'course_name',
                'Course': 'course_name',
                'Course Name': 'course_name',
                'Venue': 'course_name',
                'season': 'year',
                'Year': 'year',
                'Season': 'year',
                'position': 'finish_position',
                'Finish': 'finish_position',
                'Pos': 'finish_position',
                'Position': 'finish_position',
                'score': 'score',
                'Score': 'score',
                'total': 'score',
                'Total': 'score',
                'earnings': 'earnings',
                'Earnings': 'earnings',
                'Prize Money': 'earnings',
                'Money': 'earnings',
                'fedex_points': 'fedex_points',
                'SG Total': 'sg_total',
                'SG: Total': 'sg_total'
            }
            
            # Rename columns
            df = df.rename(columns=column_mapping)
            
            # Check required columns
            required = ['player_name', 'tournament_name', 'year']
            missing = [col for col in required if col not in df.columns]
            
            if missing:
                print(f"\n❌ Missing required columns: {missing}")
                print("   Please map these columns manually")
                return False
            
            # Clean data
            df['year'] = pd.to_numeric(df['year'], errors='coerce')
            df = df[df['year'].notna()]  # Remove rows without year
            
            # Clean earnings
            if 'earnings' in df.columns:
                df['earnings'] = df['earnings'].astype(str).str.replace('$', '').str.replace(',', '')
                df['earnings'] = pd.to_numeric(df['earnings'], errors='coerce')
            else:
                df['earnings'] = 0
            
            # Import to database
            print(f"\n   Importing {len(df):,} tournament results...")
            
            with sqlite3.connect(self.db_path) as conn:
                imported = 0
                errors = 0
                
                # Convert to list of dicts for easier access
                records = df.to_dict('records')
                
                for idx, row in enumerate(records):
                    try:
                        # Extract values directly from dict
                        player_name = str(row.get('player_name', ''))
                        tournament_name = str(row.get('tournament_name', ''))
                        course_name = str(row.get('course_name', '')) if row.get('course_name') else None
                        year = int(row.get('year')) if row.get('year') else None
                        finish_position = str(row.get('finish_position', '')) if row.get('finish_position') else None
                        score = str(row.get('score', '')) if row.get('score') else None
                        earnings = float(row.get('earnings', 0)) if row.get('earnings') else 0.0
                        
                        # Determine made_cut from finish position
                        made_cut_val = 1  # Default to made cut
                        if finish_position:
                            pos_str = str(finish_position).upper()
                            if pos_str in ['MC', 'WD', 'DQ', 'CUT']:
                                made_cut_val = 0
                        
                        # Skip if no player or tournament name
                        if not player_name or not tournament_name or player_name == 'nan':
                            continue
                        
                        conn.execute("""
                            INSERT OR REPLACE INTO historical_results
                            (player_name, tournament_name, course_name, year,
                             finish_position, score, earnings, sg_total, made_cut)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (player_name, tournament_name, course_name, year, 
                              finish_position, score, earnings, None, made_cut_val))
                        
                        imported += 1
                        
                        if imported % 5000 == 0:
                            print(f"   Imported {imported:,} rows...")
                            conn.commit()  # Commit in batches
                            
                    except Exception as e:
                        errors += 1
                        if errors <= 5:  # Show first 5 errors
                            print(f"   Error on row {idx}: {e}")
                        continue
                
                conn.commit()
            
            print(f"\n✅ Imported {imported:,} historical results")
            if errors > 0:
                print(f"⚠️  {errors:,} rows had errors and were skipped")
            
            # Build course history summaries
            self.build_course_history_summaries()
            
            return True
            
        except Exception as e:
            print(f"\n❌ Error importing CSV: {e}")
            return False
    
    def build_course_history_summaries(self):
        """Build course history summary table from historical results"""
        print("\n📊 Building course history summaries...")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Clear existing summaries
            cursor.execute("DELETE FROM course_history")
            
            # Get all player-course combinations
            cursor.execute("""
                SELECT 
                    player_name,
                    course_name,
                    COUNT(*) as appearances,
                    SUM(CASE WHEN finish_position = '1' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN CAST(REPLACE(finish_position, 'T', '') AS INTEGER) <= 5 
                        AND finish_position NOT IN ('MC', 'WD', 'DQ') THEN 1 ELSE 0 END) as top_5s,
                    SUM(CASE WHEN CAST(REPLACE(finish_position, 'T', '') AS INTEGER) <= 10 
                        AND finish_position NOT IN ('MC', 'WD', 'DQ') THEN 1 ELSE 0 END) as top_10s,
                    SUM(CASE WHEN made_cut = 1 THEN 1 ELSE 0 END) as made_cuts,
                    MAX(year) as last_played
                FROM historical_results
                WHERE course_name IS NOT NULL
                GROUP BY player_name, course_name
                HAVING appearances >= 1
            """)
            
            summaries = cursor.fetchall()
            
            # Insert summaries
            for summary in summaries:
                player, course, apps, wins, top5, top10, cuts, last = summary
                
                # Calculate average finish (only for made cuts)
                cursor.execute("""
                    SELECT finish_position
                    FROM historical_results
                    WHERE player_name = ? AND course_name = ? AND made_cut = 1
                    ORDER BY year DESC
                """, (player, course))
                
                finishes = []
                best_finish = None
                
                for (finish,) in cursor.fetchall():
                    try:
                        # Clean finish position
                        clean_finish = str(finish).replace('T', '').strip()
                        if clean_finish.isdigit():
                            finish_int = int(clean_finish)
                            finishes.append(finish_int)
                            if best_finish is None or finish_int < int(str(best_finish).replace('T', '')):
                                best_finish = finish
                    except:
                        continue
                
                avg_finish = sum(finishes) / len(finishes) if finishes else None
                
                # Insert summary
                cursor.execute("""
                    INSERT INTO course_history
                    (player_name, course_name, appearances, wins, top_5s, top_10s,
                     made_cuts, avg_finish, best_finish, last_played)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (player, course, apps, wins, top5, top10, cuts, avg_finish, best_finish, last))
            
            conn.commit()
            
            # Show summary
            cursor.execute("SELECT COUNT(*) FROM course_history")
            count = cursor.fetchone()[0]
            print(f"✅ Built {count:,} player-course history records")
    
    def show_stats(self):
        """Show import statistics"""
        print("\n" + "="*60)
        print("📊 IMPORT STATISTICS")
        print("="*60)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total results
            cursor.execute("SELECT COUNT(*) FROM historical_results")
            total = cursor.fetchone()[0]
            print(f"Total tournament results: {total:,}")
            
            # Unique players
            cursor.execute("SELECT COUNT(DISTINCT player_name) FROM historical_results")
            players = cursor.fetchone()[0]
            print(f"Unique players: {players:,}")
            
            # Unique courses
            cursor.execute("SELECT COUNT(DISTINCT course_name) FROM historical_results")
            courses = cursor.fetchone()[0]
            print(f"Unique courses: {courses:,}")
            
            # Year range
            cursor.execute("SELECT MIN(year), MAX(year) FROM historical_results")
            min_year, max_year = cursor.fetchone()
            print(f"Year range: {min_year} - {max_year}")
            
            # Course history records
            cursor.execute("SELECT COUNT(*) FROM course_history")
            history = cursor.fetchone()[0]
            print(f"Course history records: {history:,}")
            
            print("="*60)

def main():
    print("="*60)
    print("🏌️ KAGGLE HISTORICAL DATA IMPORTER")
    print("="*60)
    
    importer = KaggleHistoricalImporter()
    
    # Get CSV file path
    print("\n📁 Enter the path to your Kaggle CSV file:")
    print("   (e.g., 'pga_tour_results.csv' or full path)")
    csv_file = input("   > ").strip().strip('"').strip("'")
    
    if not csv_file:
        print("❌ No file specified")
        return
    
    if not Path(csv_file).exists():
        print(f"❌ File not found: {csv_file}")
        return
    
    # Import
    if importer.import_csv(csv_file):
        importer.show_stats()
        
        print("\n✅ Historical data imported successfully!")
        print("\n📖 Sample course history:")
        
        # Show example
        with sqlite3.connect(importer.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT player_name, course_name, appearances, wins, top_10s, avg_finish
                FROM course_history
                WHERE appearances >= 5
                ORDER BY RANDOM()
                LIMIT 5
            """)
            
            for player, course, apps, wins, top10, avg in cursor.fetchall():
                print(f"   {player} at {course}:")
                print(f"      {apps} appearances, {wins} wins, {top10} top-10s, avg: {avg:.1f}")
        
        print("\n🎯 Ready to use! The app will now use real course history.")
    else:
        print("\n❌ Import failed. Please check the file and try again.")

if __name__ == "__main__":
    main()
