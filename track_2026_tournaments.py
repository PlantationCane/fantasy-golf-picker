"""
2026 PGA Tour Tournament Tracker

Scrapes all completed 2026 tournaments with:
- Complete leaderboards (finish, score, earnings, FedEx points)
- Strokes Gained stats per tournament
- Recent form calculation (last 3-5 events)

Run weekly to update with latest tournaments
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
import time

class Tournament2026Tracker:
    """Track all 2026 PGA Tour tournaments"""
    
    def __init__(self, db_path="pga_fantasy.db"):
        self.db_path = Path(__file__).parent / db_path
        self.base_url = "https://www.pgatour.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.init_tables()
        
        # 2026 Tournament Schedule (update as season progresses)
        self.completed_tournaments = [
            {
                'name': 'The Sentry',
                'id': '029',  # PGA Tour tournament ID
                'dates': 'Jan 2-5',
                'course': 'Kapalua',
                'completed': True
            },
            {
                'name': 'The American Express',
                'id': '034',
                'dates': 'Jan 16-19',
                'course': 'La Quinta',
                'completed': True
            },
            {
                'name': 'Farmers Insurance Open',
                'id': '006',
                'dates': 'Jan 23-26',
                'course': 'Torrey Pines',
                'completed': True
            },
            {
                'name': 'AT&T Pebble Beach Pro-Am',
                'id': '007',
                'dates': 'Jan 30 - Feb 2',
                'course': 'Pebble Beach',
                'completed': True
            },
            {
                'name': 'WM Phoenix Open',
                'id': '003',
                'dates': 'Feb 6-9',
                'course': 'TPC Scottsdale',
                'completed': False  # Currently playing
            },
            {
                'name': 'The Genesis Invitational',
                'id': '008',
                'dates': 'Feb 13-16',
                'course': 'Riviera CC',
                'completed': False
            }
        ]
    
    def init_tables(self):
        """Initialize 2026 tournament tracking tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 2026 tournament results (player + tournament + detailed stats)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tournament_results_2026 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT NOT NULL,
                    tournament_name TEXT NOT NULL,
                    tournament_id TEXT,
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
            
            # Player recent form summary (calculated from last 3-5 events)
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
            print("✅ 2026 tournament tables initialized")
    
    def scrape_all_tournaments(self):
        """Scrape all completed 2026 tournaments"""
        print("\n" + "="*60)
        print("🏌️ 2026 TOURNAMENT TRACKER")
        print("="*60)
        
        completed = [t for t in self.completed_tournaments if t['completed']]
        
        print(f"\n📊 Found {len(completed)} completed tournaments to scrape:")
        for t in completed:
            print(f"   • {t['name']} ({t['dates']})")
        
        total_results = 0
        
        for tournament in completed:
            print(f"\n{'='*60}")
            print(f"📥 Scraping: {tournament['name']}")
            print(f"{'='*60}")
            
            results = self.scrape_tournament_results(tournament)
            if results > 0:
                total_results += results
                print(f"✅ Imported {results} player results")
            else:
                print(f"⚠️  No results found")
            
            time.sleep(3)  # Be nice to PGA Tour servers
        
        print(f"\n{'='*60}")
        print(f"✅ COMPLETE: {total_results} total player results imported")
        print(f"{'='*60}")
        
        # Calculate recent form for all players
        print(f"\n📊 Calculating recent form...")
        self.calculate_recent_form()
        
        return total_results
    
    def scrape_tournament_results(self, tournament):
        """Scrape results for a single tournament"""
        try:
            # Try official PGA Tour results page
            # URL format: https://www.pgatour.com/tournaments/[tournament-name]/[year]/R[tournament-id]
            
            # For now, use a simpler approach - scrape from stats pages
            # This is a placeholder - real implementation would parse tournament pages
            
            print(f"   Tournament: {tournament['name']}")
            print(f"   Course: {tournament['course']}")
            print(f"   Dates: {tournament['dates']}")
            
            # TEMPORARY: Create sample data structure
            # In production, this would actually scrape PGA Tour
            
            sample_results = self._get_sample_tournament_data(tournament)
            
            # Import to database
            imported = 0
            with sqlite3.connect(self.db_path) as conn:
                for result in sample_results:
                    try:
                        conn.execute("""
                            INSERT OR REPLACE INTO tournament_results_2026
                            (player_name, tournament_name, tournament_id, finish_position,
                             score_to_par, earnings, fedex_points, sg_total, made_cut, tournament_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            result['player_name'],
                            tournament['name'],
                            tournament['id'],
                            result['finish'],
                            result['score_to_par'],
                            result['earnings'],
                            result['fedex_points'],
                            result['sg_total'],
                            result['made_cut'],
                            result['date']
                        ))
                        imported += 1
                    except Exception as e:
                        print(f"   Error importing {result.get('player_name')}: {e}")
                        continue
                
                conn.commit()
            
            return imported
            
        except Exception as e:
            print(f"   Error scraping tournament: {e}")
            return 0
    
    def _get_sample_tournament_data(self, tournament):
        """Generate sample tournament data (TEMPORARY - replace with real scraper)"""
        # This is placeholder data showing the structure
        # Real implementation would scrape actual results
        
        sample_players = [
            'Scottie Scheffler', 'Rory McIlroy', 'Jon Rahm', 'Viktor Hovland',
            'Patrick Cantlay', 'Xander Schauffele', 'Collin Morikawa', 'Max Homa',
            'Tommy Fleetwood', 'Justin Thomas', 'Tony Finau', 'Jordan Spieth',
            'Sam Burns', 'Will Zalatoris', 'Cameron Young', 'Hideki Matsuyama',
            'Matt Fitzpatrick', 'Chris Gotterup', 'Maverick McNealy', 'Patrick Rodgers',
            'Keegan Bradley', 'Russell Henley', 'Brian Harman', 'Jason Day',
            'Rickie Fowler', 'Adam Scott', 'Justin Rose', 'Sahith Theegala'
        ]
        
        results = []
        for idx, player in enumerate(sample_players, 1):
            # Generate realistic tournament results
            made_cut = idx <= 70
            
            if made_cut:
                finish = idx
                score_to_par = -15 + (idx - 1)  # Winner at -15, decreasing
                earnings = max(0, 1500000 - (idx * 15000))
                fedex_points = max(0, 500 - (idx * 5))
                sg_total = 2.5 - (idx * 0.05)  # Better players = higher SG
            else:
                finish = 'MC'
                score_to_par = 2
                earnings = 0
                fedex_points = 0
                sg_total = -1.0
            
            results.append({
                'player_name': player,
                'finish': str(finish) if finish != 'MC' else 'MC',
                'score_to_par': score_to_par,
                'earnings': earnings,
                'fedex_points': fedex_points,
                'sg_total': sg_total,
                'made_cut': made_cut,
                'date': '2026-01-26'  # Date of tournament
            })
        
        return results
    
    def calculate_recent_form(self):
        """Calculate recent form for all players based on last 3-5 events"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all players who played in 2026
            cursor.execute("""
                SELECT DISTINCT player_name
                FROM tournament_results_2026
            """)
            
            players = [row[0] for row in cursor.fetchall()]
            
            for player in players:
                # Get last 5 tournaments for this player
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
                
                # Calculate average finish (only for made cuts)
                finishes = []
                sg_totals = []
                top_10s = 0
                
                for finish, sg, made_cut in recent_events:
                    if made_cut and finish and finish != 'MC':
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
                
                # Determine form rating
                form_rating = 'Unknown'
                if avg_sg:
                    if avg_sg >= 1.5:
                        form_rating = '🔥 Excellent'
                    elif avg_sg >= 0.5:
                        form_rating = '✅ Good'
                    elif avg_sg >= -0.5:
                        form_rating = '🔶 Average'
                    else:
                        form_rating = '🔻 Poor'
                
                # Insert form summary
                cursor.execute("""
                    INSERT OR REPLACE INTO player_recent_form
                    (player_name, events_played, avg_finish, avg_sg_total,
                     best_finish, cuts_made, top_10s, form_rating, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (player, events_played, avg_finish, avg_sg,
                      str(best_finish) if best_finish else None, cuts_made, top_10s, form_rating))
            
            conn.commit()
            
            # Show summary
            cursor.execute("SELECT COUNT(*) FROM player_recent_form")
            count = cursor.fetchone()[0]
            print(f"✅ Calculated recent form for {count} players")
    
    def show_stats(self):
        """Show 2026 tournament statistics"""
        print("\n" + "="*60)
        print("📊 2026 SEASON STATISTICS")
        print("="*60)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total results
            cursor.execute("SELECT COUNT(*) FROM tournament_results_2026")
            total = cursor.fetchone()[0]
            print(f"Total tournament results: {total}")
            
            # Unique tournaments
            cursor.execute("SELECT COUNT(DISTINCT tournament_name) FROM tournament_results_2026")
            tournaments = cursor.fetchone()[0]
            print(f"Tournaments tracked: {tournaments}")
            
            # Unique players
            cursor.execute("SELECT COUNT(DISTINCT player_name) FROM tournament_results_2026")
            players = cursor.fetchone()[0]
            print(f"Players with results: {players}")
            
            print(f"\n📈 Recent Form Leaders:")
            cursor.execute("""
                SELECT player_name, events_played, avg_sg_total, form_rating
                FROM player_recent_form
                WHERE avg_sg_total IS NOT NULL
                ORDER BY avg_sg_total DESC
                LIMIT 10
            """)
            
            for name, events, avg_sg, rating in cursor.fetchall():
                print(f"   {name}: {avg_sg:.2f} SG ({events} events) - {rating}")
        
        print("="*60)

def main():
    print("="*60)
    print("🏌️ 2026 PGA TOUR TOURNAMENT TRACKER")
    print("="*60)
    print("\nThis scrapes all completed 2026 tournaments with:")
    print("  • Complete leaderboards")
    print("  • Strokes gained stats")
    print("  • Recent form calculation")
    print("="*60)
    
    tracker = Tournament2026Tracker()
    
    print("\n⚠️  NOTE: Currently using sample data structure")
    print("Real PGA Tour scraping will be implemented next")
    print("\nProceed with sample import? (y/n): ", end='')
    
    response = input().strip().lower()
    
    if response == 'y':
        results = tracker.scrape_all_tournaments()
        tracker.show_stats()
        
        print("\n✅ Done! Your database now has:")
        print("  • 2026 tournament results")
        print("  • Recent form for each player")
        print("\n📱 Restart your app to see the data:")
        print("  streamlit run app.py")
    else:
        print("\n❌ Cancelled")

if __name__ == "__main__":
    main()
