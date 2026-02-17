"""
ESPN Golf API Scraper

Uses ESPN's hidden JSON API for fast, reliable data
No HTML parsing needed!

Usage: python scrape_espn_json_api.py
"""

import requests
import sqlite3
from pathlib import Path
from datetime import datetime
import datetime as dt
import time

class ESPNGolfAPIScraper:
    """Scrape PGA Tour data using ESPN's JSON API"""
    
    def __init__(self, db_path="pga_fantasy.db"):
        self.db_path = Path(__file__).parent / db_path
        self.api_base = "https://site.api.espn.com/apis/site/v2/sports/golf/pga"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.init_tables()
    
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
            
            # Player stats
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
            
            conn.commit()
            print("✅ Database tables initialized")
    
    def list_available_tournaments(self):
        """List recent completed tournaments"""
        print("\n" + "="*60)
        print("📅 AVAILABLE TOURNAMENTS")
        print("="*60)
        
        # Try to get recent tournaments by going back in time
        today = dt.datetime.now()
        
        tournaments = []
        
        # Check last 60 days for completed tournaments
        for days_ago in range(0, 60, 7):  # Check weekly
            check_date = today - dt.timedelta(days=days_ago)
            date_str = check_date.strftime('%Y%m%d')
            
            try:
                url = f"{self.api_base}/scoreboard?dates={date_str}"
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'events' in data and data['events']:
                        for event in data['events']:
                            status = event.get('status', {}).get('type', {}).get('name', '')
                            
                            if status in ['Final', 'STATUS_FINAL']:
                                tourn_name = event.get('name', 'Unknown')
                                tourn_date = event.get('date', '')
                                
                                if 'T' in tourn_date:
                                    tourn_date = tourn_date.split('T')[0]
                                
                                # Avoid duplicates
                                if tourn_name not in [t[0] for t in tournaments]:
                                    tournaments.append((tourn_name, tourn_date, date_str))
            except:
                continue
        
        if not tournaments:
            print("\n❌ No completed tournaments found in last 60 days")
            return []
        
        print(f"\n✅ Found {len(tournaments)} completed tournament(s):\n")
        for i, (name, date, _) in enumerate(tournaments, 1):
            print(f"   {i}. {name} ({date})")
        
        return tournaments
    
    def _fetch_statistics(self, event_id=None):
        """Fetch earnings and FedEx Cup points from statistics endpoint"""
        if event_id:
            # Event-specific stats (season totals up to this event)
            url = f"{self.api_base}/statistics?event={event_id}"
        else:
            # Season-wide stats
            url = f"{self.api_base}/statistics"
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                print(f"   ⚠️  Statistics endpoint returned {response.status_code}")
                return {}
            
            data = response.json()
            
            # Parse categories to extract earnings and FedEx points
            stats_dict = {}  # {player_name: {'earnings': X, 'fedex_points': Y}}
            
            if 'stats' not in data:
                return {}
            
            stats = data['stats']
            
            if isinstance(stats, dict) and 'categories' in stats:
                categories = stats['categories']
            elif isinstance(stats, list):
                # Handle if stats is a list
                categories = []
                for stat in stats:
                    if 'categories' in stat:
                        categories.extend(stat['categories'])
            else:
                return {}
            
            for category in categories:
                cat_name = category.get('name', '')
                cat_abbr = category.get('abbreviation', '')
                leaders = category.get('leaders', [])
                
                # Earnings
                if cat_abbr == 'EARNINGS' or cat_name == 'officialAmount':
                    for leader in leaders:
                        player_name = leader.get('athlete', {}).get('displayName', '')
                        value = leader.get('value', 0)
                        
                        if player_name and value:
                            if player_name not in stats_dict:
                                stats_dict[player_name] = {}
                            stats_dict[player_name]['earnings'] = float(value)
                
                # FedEx Cup Points
                elif cat_name == 'cupPoints':
                    for leader in leaders:
                        player_name = leader.get('athlete', {}).get('displayName', '')
                        value = leader.get('value', 0)
                        
                        if player_name and value:
                            if player_name not in stats_dict:
                                stats_dict[player_name] = {}
                            stats_dict[player_name]['fedex_points'] = float(value)
            
            return stats_dict
            
        except Exception as e:
            print(f"   ⚠️  Error fetching statistics: {e}")
            return {}
    
    def scrape_current_tournament(self):
        """Scrape the current/most recent PGA Tour tournament"""
        return self.scrape_tournament_by_date(dt.datetime.now().strftime('%Y%m%d'))
    
    def scrape_tournament_by_date(self, date_str):
        """Scrape tournament from specific date"""
        print("\n" + "="*60)
        print("⛳ ESPN GOLF JSON API SCRAPER")
        print("="*60)
        
        url = f"{self.api_base}/scoreboard?dates={date_str}"
        
        print(f"\n📥 Fetching: {url}")
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            if 'events' not in data or not data['events']:
                print(f"\n❌ No tournament data found for {date_str}")
                return 0
            
            event = data['events'][0]
            
            # Get event ID for statistics lookup
            event_id = event.get('id')
            
            tournament_name = event.get('name', 'Unknown Tournament')
            tournament_date = event.get('date', dt.datetime.now().strftime('%Y-%m-%d'))
            
            if 'T' in tournament_date:
                tournament_date = tournament_date.split('T')[0]
            
            print(f"\n🏆 Tournament: {tournament_name}")
            print(f"📅 Date: {tournament_date}")
            
            status = event.get('status', {}).get('type', {}).get('name', 'Unknown')
            print(f"📊 Status: {status}")
            
            if status not in ['Final', 'STATUS_FINAL']:
                print(f"\n⚠️  Tournament is not final")
                print(f"   Status: {status}")
                return 0
            
            # Fetch earnings and FedEx points statistics
            print(f"\n📊 Fetching statistics (earnings & FedEx points)...")
            statistics = self._fetch_statistics(event_id)
            if statistics:
                print(f"   ✅ Found statistics for {len(statistics)} players")
            else:
                print(f"   ⚠️  No statistics data available")
            
            competitions = event.get('competitions', [])
            if not competitions:
                print(f"\n❌ No competition data found")
                return 0
            
            competition = competitions[0]
            competitors = competition.get('competitors', [])
            
            if not competitors:
                print(f"\n❌ No player data found")
                return 0
            
            print(f"\n✅ Found {len(competitors)} players")
            
            players = self._parse_competitors(competitors, statistics)
            
            # Debug: Show first player
            if players:
                print(f"\n🔍 Debug - First player data:")
                first = players[0]
                print(f"   Name: {first.get('player_name')}")
                print(f"   Position: {first.get('position')}")
                print(f"   Score: {first.get('score_to_par')}")
                print(f"   Rounds: {first.get('round1')}, {first.get('round2')}, {first.get('round3')}, {first.get('round4')}")
                print(f"   Earnings: ${first.get('earnings', 0):,.0f}" if first.get('earnings') else "   Earnings: N/A")
                print(f"   FedEx Points: {first.get('fedex_points', 0)}" if first.get('fedex_points') else "   FedEx Points: N/A")
            else:
                print(f"\n❌ No players parsed!")
            
            imported = self._import_results(players, tournament_name, tournament_date)
            
            print(f"\n✅ Imported {imported} player results")
            
            print(f"\n📊 Calculating recent form...")
            self.calculate_recent_form()
            
            print(f"\n📊 Updating season stats...")
            self.update_season_stats()
            
            print("\n" + "="*60)
            print("✅ SCRAPE COMPLETE!")
            print("="*60)
            
            return imported
            
        except requests.exceptions.RequestException as e:
            print(f"\n❌ Network Error: {e}")
            return 0
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return 0
        """Scrape the current/most recent PGA Tour tournament"""
        print("\n" + "="*60)
        print("⛳ ESPN GOLF JSON API SCRAPER")
        print("="*60)
        
        # Get scoreboard data
        url = f"{self.api_base}/scoreboard"
        
        print(f"\n📥 Fetching: {url}")
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract tournament info
            if 'events' not in data or not data['events']:
                print(f"\n❌ No tournament data found")
                return 0
            
            event = data['events'][0]  # Get most recent event
            
            tournament_name = event.get('name', 'Unknown Tournament')
            tournament_date = event.get('date', datetime.now().strftime('%Y-%m-%d'))
            
            # Parse date if it's ISO format
            if 'T' in tournament_date:
                tournament_date = tournament_date.split('T')[0]
            
            print(f"\n🏆 Tournament: {tournament_name}")
            print(f"📅 Date: {tournament_date}")
            
            # Check status
            status = event.get('status', {}).get('type', {}).get('name', 'Unknown')
            print(f"📊 Status: {status}")
            
            if status not in ['Final', 'STATUS_FINAL']:
                print(f"\n⚠️  Tournament is still in progress")
                print(f"   Status: {status}")
                print(f"   Come back after it's completed!")
                return 0
            
            # Extract players from competitions
            competitions = event.get('competitions', [])
            if not competitions:
                print(f"\n❌ No competition data found")
                return 0
            
            competition = competitions[0]
            competitors = competition.get('competitors', [])
            
            if not competitors:
                print(f"\n❌ No player data found")
                return 0
            
            print(f"\n✅ Found {len(competitors)} players")
            
            # Parse players
            players = self._parse_competitors(competitors)
            
            # Import to database
            imported = self._import_results(players, tournament_name, tournament_date)
            
            print(f"\n✅ Imported {imported} player results")
            
            # Calculate recent form
            print(f"\n📊 Calculating recent form...")
            self.calculate_recent_form()
            
            # Update season stats
            print(f"\n📊 Updating season stats...")
            self.update_season_stats()
            
            print("\n" + "="*60)
            print("✅ SCRAPE COMPLETE!")
            print("="*60)
            
            return imported
            
        except requests.exceptions.RequestException as e:
            print(f"\n❌ Network Error: {e}")
            return 0
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def _parse_competitors(self, competitors, statistics=None):
        """Parse competitor data from ESPN JSON"""
        if statistics is None:
            statistics = {}
        
        players = []
        
        # Debug: Show first competitor structure
        if competitors:
            print(f"\n🔍 Debug - First competitor structure:")
            comp = competitors[0]
            print(f"   Keys: {list(comp.keys())}")
            print(f"   Order: {comp.get('order')}")
            print(f"   ID: {comp.get('id')}")
            print(f"   Type: {comp.get('type')}")
            if 'athlete' in comp:
                print(f"   Athlete keys: {list(comp['athlete'].keys())}")
                print(f"   Display name: {comp['athlete'].get('displayName')}")
            print(f"   Status: {comp.get('status')}")
            print(f"   Score: {comp.get('score')}")
            if 'statistics' in comp and len(comp['statistics']) > 0:
                print(f"   First statistic: {comp['statistics'][0]}")
            else:
                print(f"   Statistics: {comp.get('statistics', [])} (empty)")
            
            # Check last competitor (should be worse position)
            print(f"\n🔍 Debug - Last competitor (for comparison):")
            last = competitors[-1]
            print(f"   Order: {last.get('order')}")
            print(f"   Name: {last.get('athlete', {}).get('displayName')}")
            print(f"   Score: {last.get('score')}")
        
        for comp in competitors:
            try:
                # Athlete info
                athlete = comp.get('athlete', {})
                player_name = athlete.get('displayName', '')
                
                if not player_name:
                    print(f"   Skipping: No player name")
                    continue
                
                # Position/rank - ESPN uses 'order' field for leaderboard position
                position = str(comp.get('order', ''))
                
                # Score - ESPN returns this as a string like "-5" or "E"
                score_to_par = comp.get('score', 'E')
                
                # Parse score to par
                if score_to_par == 'E' or score_to_par == '' or score_to_par is None:
                    score_to_par_int = 0
                else:
                    try:
                        score_to_par_int = int(score_to_par)
                    except:
                        score_to_par_int = None
                
                # Line scores (rounds) - may be ints or dicts
                linescores = comp.get('linescores', [])
                round1 = None
                round2 = None
                round3 = None
                round4 = None
                
                try:
                    if len(linescores) > 0:
                        r1 = linescores[0]
                        round1 = int(r1.get('value', r1)) if isinstance(r1, dict) else int(r1)
                except:
                    pass
                    
                try:
                    if len(linescores) > 1:
                        r2 = linescores[1]
                        round2 = int(r2.get('value', r2)) if isinstance(r2, dict) else int(r2)
                except:
                    pass
                    
                try:
                    if len(linescores) > 2:
                        r3 = linescores[2]
                        round3 = int(r3.get('value', r3)) if isinstance(r3, dict) else int(r3)
                except:
                    pass
                    
                try:
                    if len(linescores) > 3:
                        r4 = linescores[3]
                        round4 = int(r4.get('value', r4)) if isinstance(r4, dict) else int(r4)
                except:
                    pass
                
                # Total strokes
                total_strokes = None
                rounds = [r for r in [round1, round2, round3, round4] if r is not None]
                if len(rounds) >= 4:  # Need all 4 rounds
                    total_strokes = sum(rounds)
                
                # Statistics - Get from statistics endpoint if available
                earnings = None
                fedex_points = None
                sg_total = None
                sg_ott = None
                sg_app = None
                sg_arg = None
                sg_putt = None
                
                # Look up player in statistics data
                if player_name in statistics:
                    player_stats = statistics[player_name]
                    earnings = player_stats.get('earnings')
                    fedex_points = player_stats.get('fedex_points')
                
                # Made cut
                made_cut = position not in ['MC', 'CUT', 'WD', 'DQ']
                
                player_data = {
                    'player_name': player_name,
                    'position': position,
                    'score_to_par': score_to_par_int,
                    'round1': round1,
                    'round2': round2,
                    'round3': round3,
                    'round4': round4,
                    'total_strokes': total_strokes,
                    'earnings': earnings,
                    'fedex_points': fedex_points,
                    'sg_total': sg_total,
                    'sg_ott': sg_ott,
                    'sg_app': sg_app,
                    'sg_arg': sg_arg,
                    'sg_putt': sg_putt,
                    'made_cut': made_cut
                }
                
                players.append(player_data)
                
            except Exception as e:
                if len(players) == 0:  # Only show first error for debugging
                    print(f"   First parse error for {comp.get('athlete', {}).get('displayName', 'unknown')}: {e}")
                continue
        
        print(f"   Parsed {len(players)} players from {len(competitors)} competitors")
        
        return players
    
    def _import_results(self, players, tournament_name, tournament_date):
        """Import results to database"""
        imported = 0
        errors = 0
        error_details = []
        
        with sqlite3.connect(self.db_path) as conn:
            for player in players:
                try:
                    if not player.get('player_name'):
                        errors += 1
                        error_details.append("No player name")
                        continue
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO tournament_results_2026
                        (player_name, tournament_name, finish_position, score_to_par,
                         total_strokes, round1, round2, round3, round4, earnings,
                         fedex_points, sg_total, sg_ott, sg_app, sg_arg, sg_putt,
                         made_cut, tournament_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        player['player_name'],
                        tournament_name,
                        player['position'],
                        player['score_to_par'],
                        player['total_strokes'],
                        player['round1'],
                        player['round2'],
                        player['round3'],
                        player['round4'],
                        player['earnings'],
                        player['fedex_points'],
                        player['sg_total'],
                        player['sg_ott'],
                        player['sg_app'],
                        player['sg_arg'],
                        player['sg_putt'],
                        player['made_cut'],
                        tournament_date
                    ))
                    imported += 1
                except Exception as e:
                    errors += 1
                    error_msg = f"{player.get('player_name', 'unknown')}: {str(e)}"
                    error_details.append(error_msg)
            
            conn.commit()
        
        # Show error summary
        if errors > 0:
            print(f"\n⚠️  {errors} import errors:")
            for detail in error_details[:10]:  # Show first 10
                print(f"   - {detail}")
            if len(error_details) > 10:
                print(f"   ... and {len(error_details) - 10} more")
        
        return imported
    
    def calculate_recent_form(self):
        """Calculate recent form for all players"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT DISTINCT player_name FROM tournament_results_2026")
            players = [row[0] for row in cursor.fetchall()]
            
            for player in players:
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
                
                finishes = []
                sg_totals = []
                top_10s = 0
                
                for finish, sg_total, made_cut in recent_events:
                    if made_cut and finish and finish not in ['MC', 'WD', 'DQ', 'CUT']:
                        try:
                            finish_num = int(str(finish).replace('T', ''))
                            finishes.append(finish_num)
                            if finish_num <= 10:
                                top_10s += 1
                        except:
                            pass
                    
                    if sg_total is not None:
                        sg_totals.append(float(sg_total))
                
                avg_finish = sum(finishes) / len(finishes) if finishes else None
                avg_sg_total = sum(sg_totals) / len(sg_totals) if sg_totals else None
                best_finish = min(finishes) if finishes else None
                
                # Form rating
                form_rating = 'Unknown'
                if avg_sg_total is not None:
                    if avg_sg_total >= 1.5:
                        form_rating = '🔥 Excellent'
                    elif avg_sg_total >= 0.5:
                        form_rating = '✅ Good'
                    elif avg_sg_total >= -0.5:
                        form_rating = '🔶 Average'
                    else:
                        form_rating = '🔻 Poor'
                elif avg_finish is not None:
                    if avg_finish <= 10:
                        form_rating = '🔥 Excellent'
                    elif avg_finish <= 25:
                        form_rating = '✅ Good'
                    elif avg_finish <= 50:
                        form_rating = '🔶 Average'
                    else:
                        form_rating = '🔻 Poor'
                
                cursor.execute("""
                    INSERT OR REPLACE INTO player_recent_form
                    (player_name, events_played, avg_finish, avg_sg_total,
                     best_finish, cuts_made, top_10s, form_rating, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (player, events_played, avg_finish, avg_sg_total,
                      str(best_finish) if best_finish else None,
                      cuts_made, top_10s, form_rating))
            
            conn.commit()
            
            cursor.execute("SELECT COUNT(*) FROM player_recent_form")
            count = cursor.fetchone()[0]
            print(f"✅ Updated form for {count} players")
    
    def update_season_stats(self):
        """Update season totals"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    player_name,
                    SUM(earnings) as total_money,
                    SUM(fedex_points) as total_points
                FROM tournament_results_2026
                WHERE made_cut = 1
                GROUP BY player_name
            """)
            
            players = cursor.fetchall()
            
            for player_name, total_money, total_points in players:
                # Calculate FedEx rank based on points (if available)
                if total_points is not None and total_points > 0:
                    cursor.execute("""
                        SELECT COUNT(*) + 1
                        FROM (
                            SELECT player_name, SUM(fedex_points) as pts
                            FROM tournament_results_2026
                            WHERE fedex_points IS NOT NULL
                            GROUP BY player_name
                        )
                        WHERE pts > ?
                    """, (total_points,))
                    
                    fedex_rank = cursor.fetchone()[0]
                else:
                    fedex_rank = None
                
                cursor.execute("""
                    INSERT OR REPLACE INTO player_stats
                    (player_name, fedex_rank, season_money, last_updated)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (player_name, fedex_rank, total_money))
            
            conn.commit()
            
            print(f"✅ Updated season stats for {len(players)} players")
    
    def show_stats(self):
        """Show imported data statistics"""
        print("\n" + "="*60)
        print("📊 2026 SEASON DATA")
        print("="*60)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM tournament_results_2026")
            total = cursor.fetchone()[0]
            print(f"Tournament results: {total}")
            
            cursor.execute("SELECT COUNT(DISTINCT tournament_name) FROM tournament_results_2026")
            tournaments = cursor.fetchone()[0]
            print(f"Tournaments: {tournaments}")
            
            cursor.execute("SELECT COUNT(DISTINCT player_name) FROM tournament_results_2026")
            players = cursor.fetchone()[0]
            print(f"Players: {players}")
            
            print(f"\n🏆 Top 10 Recent Performers (by best finish):")
            cursor.execute("""
                SELECT 
                    player_name,
                    MIN(CAST(finish_position AS INTEGER)) as best_finish,
                    AVG(CAST(finish_position AS INTEGER)) as avg_finish,
                    COUNT(*) as events
                FROM tournament_results_2026
                WHERE finish_position != '' 
                    AND finish_position NOT IN ('MC', 'CUT', 'WD', 'DQ')
                    AND CAST(finish_position AS INTEGER) > 0
                GROUP BY player_name
                HAVING COUNT(*) >= 1
                ORDER BY best_finish, avg_finish
                LIMIT 10
            """)
            
            for name, best, avg, events in cursor.fetchall():
                print(f"   {name}: Best={best}, Avg={avg:.1f}, Events={events}")
        
        print("="*60)

def main():
    import sys
    
    print("="*60)
    print("⛳ ESPN GOLF JSON API SCRAPER")
    print("="*60)
    print("\nUses ESPN's hidden JSON API for clean, fast data!")
    print("="*60)
    
    scraper = ESPNGolfAPIScraper()
    
    # List available tournaments
    tournaments = scraper.list_available_tournaments()
    
    if not tournaments:
        print("\n❌ No completed tournaments found")
        print("   Try again after a tournament finishes!")
        return
    
    # Check for --latest flag (auto-mode for batch files)
    if '--latest' in sys.argv:
        choice = '1'
        print(f"\n🤖 Auto-mode: scraping latest tournament ({tournaments[0][0]})")
    elif '--all' in sys.argv:
        choice = 'all'
        print(f"\n🤖 Auto-mode: scraping all {len(tournaments)} tournaments")
    else:
        # Interactive mode
        print(f"\n" + "="*60)
        choice = input("Enter tournament number to scrape (or 'all' for all): ").strip().lower()
    
    results = 0
    
    if choice == 'all':
        print(f"\n📥 Scraping all {len(tournaments)} tournaments...\n")
        for i, (name, date, date_str) in enumerate(tournaments, 1):
            print(f"\n--- Tournament {i}/{len(tournaments)} ---")
            results += scraper.scrape_tournament_by_date(date_str)
            time.sleep(2)  # Be nice to ESPN's servers
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(tournaments):
                name, date, date_str = tournaments[idx]
                results = scraper.scrape_tournament_by_date(date_str)
            else:
                print(f"\n❌ Invalid choice")
                return
        except ValueError:
            print(f"\n❌ Invalid input")
            return
    
    if results > 0:
        scraper.show_stats()
        
        print("\n✅ SUCCESS! Your database now has:")
        print("  • Complete tournament results (scores, rounds, positions)")
        print("  • Player finish positions")
        print("  • Earnings and FedEx Cup points")
        print("  • Recent form for each player")
        
        print("\n📱 Restart your app to see the data:")
        print("  streamlit run app.py")
        
        print("\n🔄 Run this script weekly after tournaments:")
        print("  python scrape_espn_json_api.py")
    else:
        print("\n⚠️  No data scraped")
        print("  Tournament may still be in progress")

if __name__ == "__main__":
    main()
