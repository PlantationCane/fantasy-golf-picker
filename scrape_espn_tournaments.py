"""
ESPN Golf Tournament Scraper

Automatically scrapes completed PGA Tour tournaments from ESPN
Much easier than manual CSV export!

Usage: python scrape_espn_tournaments.py
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
from pathlib import Path
from datetime import datetime
import time
import re

class ESPNGolfScraper:
    """Scrape PGA Tour tournament results from ESPN"""
    
    def __init__(self, db_path="pga_fantasy.db"):
        self.db_path = Path(__file__).parent / db_path
        self.base_url = "https://www.espn.com"
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
    
    def scrape_current_tournament(self):
        """Scrape the current/most recent PGA Tour tournament from ESPN"""
        print("\n" + "="*60)
        print("⛳ ESPN GOLF SCRAPER")
        print("="*60)
        
        # ESPN PGA Tour leaderboard
        url = "https://www.espn.com/golf/leaderboard"
        
        print(f"\n📥 Fetching: {url}")
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract tournament name
            tournament_name = self._extract_tournament_name(soup)
            print(f"\n🏆 Tournament: {tournament_name}")
            
            # Check if tournament is final
            status = self._check_tournament_status(soup)
            print(f"📊 Status: {status}")
            
            if status != "Final":
                print(f"\n⚠️  Tournament is still in progress")
                print(f"   Come back after it's completed!")
                return 0
            
            # Extract leaderboard data
            players = self._extract_leaderboard(soup)
            
            if not players:
                print(f"\n❌ No leaderboard data found")
                return 0
            
            print(f"\n✅ Found {len(players)} players")
            
            # Now scrape Player Stats page for Strokes Gained data
            print(f"\n📊 Fetching Player Stats (Strokes Gained)...")
            player_stats = self._scrape_player_stats()
            
            if player_stats:
                print(f"✅ Found Strokes Gained data for {len(player_stats)} players")
                # Merge stats into players
                self._merge_player_stats(players, player_stats)
            else:
                print(f"⚠️  No Strokes Gained data found (may not be available yet)")
            
            # Get tournament date
            tournament_date = datetime.now().strftime('%Y-%m-%d')
            
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
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def _extract_tournament_name(self, soup):
        """Extract tournament name from page"""
        try:
            # Try multiple selectors
            title_elem = soup.find('h1', class_='headline')
            if title_elem:
                return title_elem.text.strip()
            
            title_elem = soup.find('div', class_='headline')
            if title_elem:
                return title_elem.text.strip()
            
            # Fallback: look in page title
            title = soup.find('title')
            if title:
                text = title.text
                # Extract tournament name from title
                if '-' in text:
                    return text.split('-')[0].strip()
            
            return "Unknown Tournament"
        except:
            return "Unknown Tournament"
    
    def _check_tournament_status(self, soup):
        """Check if tournament is completed"""
        try:
            # Look for "Final" status
            status_elem = soup.find(text=re.compile(r'Final', re.IGNORECASE))
            if status_elem:
                return "Final"
            
            # Look for round indicators
            round_elem = soup.find(text=re.compile(r'Round [1-4]', re.IGNORECASE))
            if round_elem:
                return round_elem.strip()
            
            return "Unknown"
        except:
            return "Unknown"
    
    def _extract_leaderboard(self, soup):
        """Extract player data from leaderboard table"""
        players = []
        
        try:
            # Find the leaderboard table
            table = soup.find('table', class_='Table')
            if not table:
                # Try alternative selector
                table = soup.find('div', class_='leaderboard')
            
            if not table:
                print("   Could not find leaderboard table")
                return players
            
            # Find all rows
            rows = table.find_all('tr')
            
            for row in rows:
                try:
                    # Skip header rows
                    if row.find('th'):
                        continue
                    
                    cells = row.find_all('td')
                    if len(cells) < 6:
                        continue
                    
                    # Extract position (first cell)
                    position = cells[0].text.strip()
                    
                    # Player name is in second cell
                    # ESPN often has the name inside a <a> tag or <span>
                    player_cell = cells[1]
                    
                    # Try multiple methods to extract player name
                    player_name = None
                    
                    # Method 1: Find <a> tag (most common)
                    player_link = player_cell.find('a')
                    if player_link:
                        player_name = player_link.text.strip()
                    
                    # Method 2: Find <span> tag
                    if not player_name:
                        player_span = player_cell.find('span')
                        if player_span:
                            player_name = player_span.text.strip()
                    
                    # Method 3: Get all text from cell
                    if not player_name:
                        player_name = player_cell.get_text(strip=True)
                    
                    # Validate player name
                    if not player_name or player_name in ['POS', 'PLAYER', '']:
                        continue
                    
                    # Skip if name is just a number (means we got position by mistake)
                    if player_name.replace('T', '').replace('E', '').replace('-', '').replace('+', '').isdigit():
                        continue
                    
                    # Debug: Print first few players to check
                    if len(players) < 3:
                        print(f"   Debug: Position={position}, Player={player_name}")
                    
                    # Score to par (third cell)
                    score_text = cells[2].text.strip()
                    score_to_par = self._parse_score(score_text)
                    
                    # Rounds (R1, R2, R3, R4)
                    round1 = self._safe_int(cells[3].text.strip()) if len(cells) > 3 else None
                    round2 = self._safe_int(cells[4].text.strip()) if len(cells) > 4 else None
                    round3 = self._safe_int(cells[5].text.strip()) if len(cells) > 5 else None
                    round4 = self._safe_int(cells[6].text.strip()) if len(cells) > 6 else None
                    
                    # Total strokes
                    total_strokes = None
                    if len(cells) > 7:
                        total_strokes = self._safe_int(cells[7].text.strip())
                    
                    # Calculate total if not provided
                    if not total_strokes and all(r for r in [round1, round2, round3, round4]):
                        total_strokes = round1 + round2 + round3 + round4
                    
                    # Earnings
                    earnings = None
                    if len(cells) > 8:
                        earnings = self._parse_money(cells[8].text.strip())
                    
                    # FedEx points
                    fedex_points = None
                    if len(cells) > 9:
                        fedex_points = self._safe_float(cells[9].text.strip())
                    
                    # Made cut
                    made_cut = position not in ['MC', 'CUT', 'WD', 'DQ']
                    
                    player_data = {
                        'player_name': player_name,
                        'position': position,
                        'score_to_par': score_to_par,
                        'round1': round1,
                        'round2': round2,
                        'round3': round3,
                        'round4': round4,
                        'total_strokes': total_strokes,
                        'earnings': earnings,
                        'fedex_points': fedex_points,
                        'made_cut': made_cut,
                        # Initialize SG stats (will be filled from Player Stats page)
                        'sg_total': None,
                        'sg_ott': None,
                        'sg_app': None,
                        'sg_arg': None,
                        'sg_putt': None
                    }
                    
                    players.append(player_data)
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            print(f"   Error parsing table: {e}")
        
        return players
    
    def _scrape_player_stats(self):
        """Scrape Player Stats page for Strokes Gained data"""
        try:
            # Player Stats tab is usually at the same URL with a different parameter
            # or it's a tab that loads via JavaScript
            # Let's try the direct link first
            stats_url = "https://www.espn.com/golf/leaderboard/_/tab/stats"
            
            response = self.session.get(stats_url, timeout=15)
            if response.status_code != 200:
                return {}
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            player_stats = {}
            
            # Find the stats table
            table = soup.find('table', class_='Table')
            if not table:
                return {}
            
            rows = table.find_all('tr')
            
            for row in rows:
                try:
                    if row.find('th'):
                        continue
                    
                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue
                    
                    # Player name
                    player_elem = cells[0].find('a')
                    if player_elem:
                        player_name = player_elem.text.strip()
                    else:
                        player_name = cells[0].text.strip()
                    
                    if not player_name:
                        continue
                    
                    # The columns typically are:
                    # Player, SG: Total, SG: OTT, SG: App, SG: ARG, SG: Putt
                    # (column order may vary)
                    
                    stats = {
                        'sg_total': self._safe_float(cells[1].text.strip()) if len(cells) > 1 else None,
                        'sg_ott': self._safe_float(cells[2].text.strip()) if len(cells) > 2 else None,
                        'sg_app': self._safe_float(cells[3].text.strip()) if len(cells) > 3 else None,
                        'sg_arg': self._safe_float(cells[4].text.strip()) if len(cells) > 4 else None,
                        'sg_putt': self._safe_float(cells[5].text.strip()) if len(cells) > 5 else None
                    }
                    
                    player_stats[player_name] = stats
                    
                except Exception as e:
                    continue
            
            return player_stats
            
        except Exception as e:
            print(f"   Error scraping player stats: {e}")
            return {}
    
    def _merge_player_stats(self, players, player_stats):
        """Merge Strokes Gained data into player results"""
        for player in players:
            player_name = player['player_name']
            if player_name in player_stats:
                stats = player_stats[player_name]
                player['sg_total'] = stats.get('sg_total')
                player['sg_ott'] = stats.get('sg_ott')
                player['sg_app'] = stats.get('sg_app')
                player['sg_arg'] = stats.get('sg_arg')
                player['sg_putt'] = stats.get('sg_putt')
    
    def _parse_score(self, score_text):
        """Parse score to par (e.g., '-16', 'E', '+2')"""
        try:
            score_text = score_text.strip()
            if score_text == 'E':
                return 0
            # Remove any non-numeric characters except +/-
            score_text = re.sub(r'[^\d+-]', '', score_text)
            if score_text:
                return int(score_text)
        except:
            pass
        return None
    
    def _parse_money(self, money_text):
        """Parse money string (e.g., '$1,638,000')"""
        try:
            # Remove $ and commas
            cleaned = money_text.replace('$', '').replace(',', '').strip()
            if cleaned:
                return float(cleaned)
        except:
            pass
        return None
    
    def _safe_int(self, value):
        """Safely convert to int"""
        try:
            if not value or value == '--':
                return None
            return int(value)
        except:
            return None
    
    def _safe_float(self, value):
        """Safely convert to float"""
        try:
            if not value or value == '--':
                return None
            return float(value)
        except:
            return None
    
    def _import_results(self, players, tournament_name, tournament_date):
        """Import results to database"""
        imported = 0
        errors = 0
        
        with sqlite3.connect(self.db_path) as conn:
            for player in players:
                try:
                    # Validate we have required data
                    if not player.get('player_name'):
                        errors += 1
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
                        player.get('sg_total'),
                        player.get('sg_ott'),
                        player.get('sg_app'),
                        player.get('sg_arg'),
                        player.get('sg_putt'),
                        player['made_cut'],
                        tournament_date
                    ))
                    imported += 1
                except Exception as e:
                    errors += 1
                    if errors <= 5:  # Show first 5 errors
                        print(f"   Error importing {player.get('player_name', 'unknown')}: {e}")
            
            conn.commit()
        
        if errors > 5:
            print(f"   ... and {errors - 5} more errors")
        
        return imported
    
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
                
                for finish, sg_total, made_cut in recent_events:
                    if made_cut and finish and finish not in ['MC', 'WD', 'DQ', 'CUT']:
                        try:
                            finish_num = int(str(finish).replace('T', ''))
                            finishes.append(finish_num)
                            if finish_num <= 10:
                                top_10s += 1
                        except:
                            pass
                    
                    # Add SG Total if available
                    if sg_total is not None:
                        sg_totals.append(float(sg_total))
                
                avg_finish = sum(finishes) / len(finishes) if finishes else None
                avg_sg_total = sum(sg_totals) / len(sg_totals) if sg_totals else None
                best_finish = min(finishes) if finishes else None
                
                # Form rating - prioritize SG Total if available, otherwise use finish position
                form_rating = 'Unknown'
                if avg_sg_total is not None:
                    # Use Strokes Gained for form rating (best indicator)
                    if avg_sg_total >= 1.5:
                        form_rating = '🔥 Excellent'
                    elif avg_sg_total >= 0.5:
                        form_rating = '✅ Good'
                    elif avg_sg_total >= -0.5:
                        form_rating = '🔶 Average'
                    else:
                        form_rating = '🔻 Poor'
                elif avg_finish is not None:
                    # Fallback to finish position
                    if avg_finish <= 10:
                        form_rating = '🔥 Excellent'
                    elif avg_finish <= 25:
                        form_rating = '✅ Good'
                    elif avg_finish <= 50:
                        form_rating = '🔶 Average'
                    else:
                        form_rating = '🔻 Poor'
                
                # Insert
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
        """Update season totals from tournament results"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Aggregate season stats
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
                # Calculate FedEx rank
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
                money_str = f"${money:,.0f}" if money else "$0"
                print(f"   {rank}. {name} - {money_str}")
        
        print("="*60)

def main():
    print("="*60)
    print("⛳ ESPN GOLF SCRAPER")
    print("="*60)
    print("\nAutomatically scrapes completed PGA Tour tournaments")
    print("from ESPN's leaderboard")
    print("="*60)
    
    scraper = ESPNGolfScraper()
    
    results = scraper.scrape_current_tournament()
    
    if results > 0:
        scraper.show_stats()
        
        print("\n✅ SUCCESS! Your database now has:")
        print("  • Complete tournament results")
        print("  • FedEx Cup standings")
        print("  • Recent form for each player")
        
        print("\n📱 Restart your app to see the data:")
        print("  streamlit run app.py")
        
        print("\n🔄 Run this script weekly after tournaments:")
        print("  python scrape_espn_tournaments.py")
    else:
        print("\n⚠️  No data scraped")
        print("  Tournament may still be in progress")
        print("  or there was an error parsing the page")

if __name__ == "__main__":
    main()
