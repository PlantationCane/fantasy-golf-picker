"""
PGA Tour JSON API Scraper

Uses PGA Tour's hidden JSON API to fetch tournament results and stats
Much faster and more reliable than HTML scraping!

API Endpoints:
- Tournament Results: pgatour.com/data/r/{tournament_id}/{year}/tournsum.json
- Stats: pgatour.com/data/r/stats/{year}/stat.{stat_id}.json
- Players: pgatour.com/data/players/

Usage: python scrape_pgatour_api.py
"""

import requests
import sqlite3
from pathlib import Path
from datetime import datetime
import time
import json

class PGATourAPIScraper:
    """Scrape PGA Tour data using JSON API"""
    
    def __init__(self, db_path="pga_fantasy.db"):
        self.db_path = Path(__file__).parent / db_path
        self.base_url = "https://www.pgatour.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.init_tables()
        
        # 2026 Tournament IDs (from PGA Tour API)
        self.tournaments_2026 = [
            {'name': 'The Sentry', 'id': '029', 'dates': 'Jan 2-5', 'course': 'Kapalua'},
            {'name': 'The American Express', 'id': '034', 'dates': 'Jan 16-19', 'course': 'La Quinta'},
            {'name': 'Farmers Insurance Open', 'id': '006', 'dates': 'Jan 23-26', 'course': 'Torrey Pines'},
            {'name': 'AT&T Pebble Beach Pro-Am', 'id': '007', 'dates': 'Jan 30 - Feb 2', 'course': 'Pebble Beach'},
            {'name': 'WM Phoenix Open', 'id': '003', 'dates': 'Feb 6-9', 'course': 'TPC Scottsdale'},
            {'name': 'The Genesis Invitational', 'id': '008', 'dates': 'Feb 13-16', 'course': 'Riviera CC'},
            {'name': 'The Cognizant Classic', 'id': '011', 'dates': 'Feb 20-23', 'course': 'PGA National'},
            {'name': 'The Mexico Open', 'id': '540', 'dates': 'Feb 27 - Mar 2', 'course': 'Vidanta Vallarta'},
        ]
    
    def init_tables(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 2026 tournament results
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
            
            # Current season stats (FedEx Cup, money, etc.)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_stats (
                    player_name TEXT PRIMARY KEY,
                    fedex_rank INTEGER,
                    world_rank INTEGER,
                    season_money REAL,
                    sg_total REAL,
                    sg_ott REAL,
                    sg_app REAL,
                    sg_arg REAL,
                    sg_putt REAL,
                    last_updated TIMESTAMP
                )
            """)
            
            # Tournament field
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tournament_field (
                    player_name TEXT PRIMARY KEY,
                    fedex_rank INTEGER,
                    world_rank INTEGER,
                    last_updated TIMESTAMP
                )
            """)
            
            conn.commit()
            print("✅ Database tables initialized")
    
    def scrape_all_2026_tournaments(self):
        """Scrape all completed 2026 tournaments"""
        print("\n" + "="*60)
        print("🏌️ PGA TOUR JSON API SCRAPER")
        print("="*60)
        print("\nScraping from official PGA Tour JSON API...")
        print("This is fast and reliable! ⚡")
        
        total_results = 0
        
        for tournament in self.tournaments_2026:
            print(f"\n{'='*60}")
            print(f"📥 {tournament['name']}")
            print(f"{'='*60}")
            
            results = self.scrape_tournament(tournament)
            if results > 0:
                total_results += results
                print(f"✅ Imported {results} player results")
            else:
                print(f"⚠️  Tournament not available yet (or data error)")
            
            time.sleep(2)  # Be nice to PGA Tour servers
        
        print(f"\n{'='*60}")
        print(f"✅ COMPLETE: {total_results} total results imported")
        print(f"{'='*60}")
        
        # Calculate recent form
        if total_results > 0:
            print(f"\n📊 Calculating recent form...")
            self.calculate_recent_form()
            
            # Update player stats summary
            print(f"\n📊 Updating season stats...")
            self.update_season_stats()
        
        return total_results
    
    def scrape_tournament(self, tournament):
        """Scrape single tournament from JSON API"""
        try:
            # Build API URL
            url = f"{self.base_url}/data/r/{tournament['id']}/2026/tournsum.json"
            
            print(f"   Fetching: {url}")
            
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                print(f"   Status: {response.status_code} - Tournament may not be completed yet")
                return 0
            
            # Parse JSON
            data = response.json()
            
            # Navigate JSON structure
            # Structure: data['years'][0]['tours'][0]['trns'][0]['plrs']
            try:
                year_data = data['years'][0]
                tour_data = year_data['tours'][0]
                tournament_data = tour_data['trns'][0]
                players = tournament_data.get('plrs', [])
                
                if not players:
                    print(f"   No player data found")
                    return 0
                
                print(f"   Found {len(players)} players")
                
                # Import to database
                imported = 0
                with sqlite3.connect(self.db_path) as conn:
                    for player in players:
                        try:
                            # Extract player info
                            player_name = player.get('name', '').strip()
                            if not player_name:
                                continue
                            
                            # Position/finish
                            position = player.get('pos', '')
                            
                            # Score
                            total_score = player.get('tot', '')
                            score_to_par = None
                            if total_score:
                                try:
                                    score_to_par = int(total_score)
                                except:
                                    pass
                            
                            # Rounds
                            rounds = player.get('rnds', [])
                            round1 = int(rounds[0]) if len(rounds) > 0 and rounds[0] else None
                            round2 = int(rounds[1]) if len(rounds) > 1 and rounds[1] else None
                            round3 = int(rounds[2]) if len(rounds) > 2 and rounds[2] else None
                            round4 = int(rounds[3]) if len(rounds) > 3 and rounds[3] else None
                            
                            # Total strokes
                            total_strokes = None
                            if all(r for r in [round1, round2, round3, round4]):
                                total_strokes = round1 + round2 + round3 + round4
                            
                            # Money
                            earnings = player.get('money', 0)
                            if earnings:
                                try:
                                    earnings = float(str(earnings).replace('$', '').replace(',', ''))
                                except:
                                    earnings = 0
                            
                            # FedEx points
                            fedex_points = player.get('pts', 0)
                            if fedex_points:
                                try:
                                    fedex_points = float(fedex_points)
                                except:
                                    fedex_points = 0
                            
                            # Made cut
                            made_cut = position not in ['MC', 'WD', 'DQ', 'CUT'] if position else False
                            
                            # Tournament date (estimate from tournament dates)
                            tournament_date = self._parse_date(tournament['dates'])
                            
                            # Insert
                            conn.execute("""
                                INSERT OR REPLACE INTO tournament_results_2026
                                (player_name, tournament_name, tournament_id, finish_position,
                                 score_to_par, total_strokes, round1, round2, round3, round4,
                                 earnings, fedex_points, made_cut, tournament_date)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (player_name, tournament['name'], tournament['id'], position,
                                  score_to_par, total_strokes, round1, round2, round3, round4,
                                  earnings, fedex_points, made_cut, tournament_date))
                            
                            imported += 1
                            
                        except Exception as e:
                            print(f"   Error importing {player.get('name', 'unknown')}: {e}")
                            continue
                    
                    conn.commit()
                
                return imported
                
            except (KeyError, IndexError) as e:
                print(f"   Error parsing JSON structure: {e}")
                return 0
            
        except Exception as e:
            print(f"   Error: {e}")
            return 0
    
    def _parse_date(self, date_str):
        """Parse tournament date string to YYYY-MM-DD"""
        # e.g., "Jan 2-5" -> "2026-01-05"
        try:
            # Extract month and last day
            parts = date_str.split()
            month_str = parts[0]
            
            # Get end date
            if '-' in date_str:
                day_str = date_str.split('-')[1].split(',')[0].strip()
            else:
                day_str = parts[1].strip()
            
            # Month mapping
            months = {
                'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
            }
            
            month = months.get(month_str, '01')
            day = day_str.zfill(2)
            
            return f"2026-{month}-{day}"
        except:
            return "2026-01-01"
    
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
    
    def update_season_stats(self):
        """Update season totals from tournament results"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Aggregate season stats for each player
            cursor.execute("""
                SELECT 
                    player_name,
                    SUM(earnings) as total_money,
                    SUM(fedex_points) as total_points,
                    AVG(sg_total) as avg_sg_total
                FROM tournament_results_2026
                WHERE made_cut = 1
                GROUP BY player_name
            """)
            
            players = cursor.fetchall()
            
            for player_name, total_money, total_points, avg_sg in players:
                # Calculate FedEx rank based on points
                cursor.execute("""
                    SELECT COUNT(*) + 1
                    FROM (
                        SELECT player_name, SUM(fedex_points) as pts
                        FROM tournament_results_2026
                        GROUP BY player_name
                    )
                    WHERE pts > ?
                """, (total_points,))
                
                fedex_rank = cursor.fetchone()[0]
                
                # Update player_stats
                cursor.execute("""
                    INSERT OR REPLACE INTO player_stats
                    (player_name, fedex_rank, season_money, sg_total, last_updated)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (player_name, fedex_rank, total_money, avg_sg))
                
                # Update tournament_field
                cursor.execute("""
                    INSERT OR REPLACE INTO tournament_field
                    (player_name, fedex_rank, last_updated)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (player_name, fedex_rank))
            
            conn.commit()
            
            print(f"✅ Updated season stats for {len(players)} players")
    
    def show_stats(self):
        """Show imported data statistics"""
        print("\n" + "="*60)
        print("📊 2026 SEASON DATA")
        print("="*60)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total results
            cursor.execute("SELECT COUNT(*) FROM tournament_results_2026")
            total = cursor.fetchone()[0]
            print(f"Tournament results: {total}")
            
            # Tournaments
            cursor.execute("SELECT COUNT(DISTINCT tournament_name) FROM tournament_results_2026")
            tournaments = cursor.fetchone()[0]
            print(f"Tournaments: {tournaments}")
            
            # Players
            cursor.execute("SELECT COUNT(DISTINCT player_name) FROM tournament_results_2026")
            players = cursor.fetchone()[0]
            print(f"Players: {players}")
            
            # Top 10 FedEx Cup
            print(f"\n🏆 Top 10 FedEx Cup Standings:")
            cursor.execute("""
                SELECT player_name, fedex_rank, season_money
                FROM player_stats
                WHERE fedex_rank IS NOT NULL
                ORDER BY fedex_rank
                LIMIT 10
            """)
            
            for name, rank, money in cursor.fetchall():
                print(f"   {rank}. {name} - ${money:,.0f}")
            
            # Recent form leaders
            print(f"\n📈 Top Recent Form (by SG):")
            cursor.execute("""
                SELECT player_name, events_played, avg_sg_total, form_rating
                FROM player_recent_form
                WHERE avg_sg_total IS NOT NULL
                ORDER BY avg_sg_total DESC
                LIMIT 10
            """)
            
            for name, events, avg_sg, rating in cursor.fetchall():
                print(f"   {name}: +{avg_sg:.2f} SG ({events} events) {rating}")
        
        print("="*60)

def main():
    print("="*60)
    print("🏌️ PGA TOUR JSON API SCRAPER")
    print("="*60)
    print("\nThis scraper uses PGA Tour's official JSON API")
    print("Fast, reliable, and gets complete tournament data!")
    print("="*60)
    
    scraper = PGATourAPIScraper()
    
    print("\n⚡ Starting tournament scraping...")
    print("This will take about 20-30 seconds\n")
    
    results = scraper.scrape_all_2026_tournaments()
    
    if results > 0:
        scraper.show_stats()
        
        print("\n✅ SUCCESS! Your database now has:")
        print("  • Complete 2026 tournament results")
        print("  • FedEx Cup standings")
        print("  • Recent form for each player")
        print("  • Season earnings")
        
        print("\n📱 Restart your app to see the data:")
        print("  streamlit run app.py")
    else:
        print("\n⚠️  No tournaments scraped.")
        print("  This could mean:")
        print("  • Tournaments haven't been played yet")
        print("  • API structure changed")
        print("  • Network issues")

if __name__ == "__main__":
    main()
