"""
Weekly Data Downloader for PGA Tour Stats

Run this script weekly to download fresh data from PGA Tour
Stores everything locally for fast access
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3
import json
import time
from datetime import datetime
from pathlib import Path

class PGATourDataDownloader:
    """Downloads and stores PGA Tour data locally"""
    
    def __init__(self, db_path="pga_fantasy.db"):
        self.db_path = Path(__file__).parent.parent / db_path
        self.base_url = "https://www.pgatour.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.init_data_tables()
    
    def init_data_tables(self):
        """Initialize database tables for storing downloaded data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Current tournament table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS current_tournament (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    name TEXT NOT NULL,
                    dates TEXT,
                    course TEXT,
                    purse TEXT,
                    tournament_id TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tournament field table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tournament_field (
                    player_name TEXT PRIMARY KEY,
                    player_id TEXT,
                    fedex_rank INTEGER,
                    world_rank INTEGER,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Player stats table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_stats (
                    player_name TEXT PRIMARY KEY,
                    player_id TEXT,
                    fedex_rank INTEGER,
                    world_rank INTEGER,
                    season_money REAL,
                    sg_total REAL,
                    sg_total_rank INTEGER,
                    sg_ott REAL,
                    sg_app REAL,
                    sg_arg REAL,
                    sg_putt REAL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tournament results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tournament_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT,
                    tournament_name TEXT,
                    date TEXT,
                    finish TEXT,
                    score TEXT,
                    earnings TEXT,
                    UNIQUE(player_name, tournament_name, date)
                )
            """)
            
            conn.commit()
    
    def download_all_data(self):
        """Download all data in one go"""
        print("\n" + "="*60)
        print("🏌️ PGA TOUR DATA DOWNLOADER")
        print("="*60)
        
        steps = [
            ("Current Tournament", self.download_current_tournament),
            ("FedEx Cup Standings", self.download_fedex_standings),
            ("Strokes Gained Stats", self.download_strokes_gained),
            ("Money List", self.download_money_list),
        ]
        
        for step_name, step_func in steps:
            print(f"\n📊 Downloading {step_name}...")
            try:
                result = step_func()
                if result:
                    print(f"✅ {step_name} complete!")
                else:
                    print(f"⚠️  {step_name} - partial data")
            except Exception as e:
                print(f"❌ {step_name} failed: {e}")
            
            # Be nice to PGA Tour servers
            time.sleep(2)
        
        print("\n" + "="*60)
        print("✅ Data download complete!")
        print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
    
    def download_current_tournament(self):
        """Download current week's tournament info from PGA Tour schedule"""
        try:
            print("  Fetching from PGA Tour schedule...")
            
            # Method 1: Try PGA Tour API endpoint (if available)
            api_url = "https://statdata.pgatour.com/r/current/schedule.json"
            try:
                response = self.session.get(api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # Find current tournament from JSON
                    if 'tournaments' in data:
                        from datetime import datetime
                        current_date = datetime.now()
                        
                        for tournament in data.get('tournaments', []):
                            # Check if tournament is this week
                            t_name = tournament.get('tournament_name') or tournament.get('name')
                            if t_name:
                                print(f"  Found from API: {t_name}")
                                
                                with sqlite3.connect(self.db_path) as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("""
                                        INSERT OR REPLACE INTO current_tournament 
                                        (id, name, dates, course, purse, tournament_id, last_updated)
                                        VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                                    """, (t_name, 'This Week', 'TBD', 'TBD', tournament.get('id', 'current')))
                                    conn.commit()
                                
                                return True
            except:
                pass  # Fall through to web scraping
            
            # Method 2: Scrape schedule page
            schedule_url = f"{self.base_url}/tournaments"
            response = self.session.get(schedule_url, timeout=15)
            
            if response.status_code != 200:
                print(f"  Could not access schedule (status {response.status_code})")
                return self._manual_tournament_entry()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for current/this week tournament
            current_tournament = None
            
            # Try: Look for "This Week" section
            this_week = soup.find(text=lambda t: t and 'this week' in t.lower())
            if this_week:
                parent = this_week.find_parent()
                for _ in range(5):  # Search up to 5 levels up
                    if parent:
                        tournament_name = parent.find(['h2', 'h3', 'h4'])
                        if tournament_name:
                            current_tournament = tournament_name.text.strip()
                            break
                        parent = parent.parent
            
            # Fallback: Look for tournaments with current dates
            if not current_tournament:
                from datetime import datetime
                current_date = datetime.now()
                
                # Find all tournament cards/sections
                tournaments = soup.find_all(['article', 'div'], class_=lambda c: c and ('tournament' in c.lower() or 'event' in c.lower()))
                
                for tournament in tournaments[:5]:  # Check first 5 tournaments
                    name_elem = tournament.find(['h2', 'h3', 'h4', 'a'])
                    date_elem = tournament.find(text=lambda t: t and any(month in t for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']))
                    
                    if name_elem and date_elem:
                        current_tournament = name_elem.text.strip()
                        break
            
            # Fallback: Use known tournament for this date
            if not current_tournament:
                # Hardcoded schedule as last resort (update this weekly!)
                from datetime import datetime
                week_of_year = datetime.now().isocalendar()[1]
                
                # 2026 schedule approximation
                schedule_map = {
                    6: "The Genesis Invitational",  # Week 6 (early Feb)
                    7: "AT&T Pebble Beach Pro-Am",
                    8: "WM Phoenix Open",
                    # Add more as needed
                }
                
                current_tournament = schedule_map.get(week_of_year, "Current Tournament")
            
            # Clean up tournament name
            current_tournament = current_tournament.replace('\n', '').replace('\t', '').strip()
            
            print(f"  Found: {current_tournament}")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO current_tournament 
                    (id, name, dates, course, purse, tournament_id, last_updated)
                    VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (current_tournament, 'This Week', 'TBD', 'TBD', 'current'))
                conn.commit()
            
            return True
            
        except Exception as e:
            print(f"  Error auto-detecting: {e}")
            return self._manual_tournament_entry()
    
    def _manual_tournament_entry(self):
        """Fallback: Manual tournament entry"""
        print("\n  📝 Auto-detection failed. Please enter manually:")
        name = input("  Tournament name: ").strip()
        if not name:
            name = "Current Tournament"
        
        dates = input("  Dates (optional, press Enter to skip): ").strip() or "TBD"
        course = input("  Course (optional, press Enter to skip): ").strip() or "TBD"
        purse = input("  Purse (optional, press Enter to skip): ").strip() or "TBD"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO current_tournament 
                    (id, name, dates, course, purse, tournament_id, last_updated)
                    VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (name, dates, course, purse, 'current'))
                conn.commit()
            return True
        except Exception as e:
            print(f"  Error: {e}")
            return False
    
    def download_fedex_standings(self):
        """Download FedEx Cup standings"""
        try:
            url = f"{self.base_url}/stats/stat.02671.html"
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                print(f"Could not access FedEx standings (status {response.status_code})")
                return False
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find the stats table
            table = soup.find('table', class_='table-stats') or soup.find('table')
            
            if not table:
                print("Could not find FedEx standings table")
                return False
            
            players = []
            rows = table.find_all('tr')[1:]  # Skip header
            
            for row in rows[:100]:  # Top 100 players
                cols = row.find_all('td')
                if len(cols) < 3:
                    continue
                
                try:
                    rank = cols[0].text.strip()
                    player_link = cols[1].find('a')
                    player_name = player_link.text.strip() if player_link else cols[1].text.strip()
                    
                    # Clean up name
                    player_name = player_name.replace('\n', '').replace('\t', '').strip()
                    
                    if player_name and rank.isdigit():
                        players.append({
                            'player_name': player_name,
                            'fedex_rank': int(rank)
                        })
                except:
                    continue
            
            if players:
                with sqlite3.connect(self.db_path) as conn:
                    for player in players:
                        conn.execute("""
                            INSERT OR REPLACE INTO tournament_field 
                            (player_name, fedex_rank, last_updated)
                            VALUES (?, ?, CURRENT_TIMESTAMP)
                        """, (player['player_name'], player['fedex_rank']))
                        
                        conn.execute("""
                            INSERT OR REPLACE INTO player_stats
                            (player_name, fedex_rank, last_updated)
                            VALUES (?, ?, CURRENT_TIMESTAMP)
                        """, (player['player_name'], player['fedex_rank']))
                    
                    conn.commit()
                
                print(f"  Downloaded {len(players)} FedEx Cup standings")
                return True
            
            return False
            
        except Exception as e:
            print(f"  Error downloading FedEx standings: {e}")
            return False
    
    def download_strokes_gained(self):
        """Download Strokes Gained: Total stats"""
        try:
            url = f"{self.base_url}/stats/stat.02675.html"  # SG: Total
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                return False
            
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', class_='table-stats') or soup.find('table')
            
            if not table:
                return False
            
            sg_data = []
            rows = table.find_all('tr')[1:]
            
            for row in rows[:100]:
                cols = row.find_all('td')
                if len(cols) < 3:
                    continue
                
                try:
                    rank = cols[0].text.strip()
                    player_name = cols[1].find('a').text.strip() if cols[1].find('a') else cols[1].text.strip()
                    player_name = player_name.replace('\n', '').replace('\t', '').strip()
                    
                    sg_total = cols[2].text.strip()
                    
                    if player_name and sg_total:
                        sg_data.append({
                            'player_name': player_name,
                            'sg_total': float(sg_total),
                            'sg_total_rank': int(rank) if rank.isdigit() else None
                        })
                except:
                    continue
            
            if sg_data:
                with sqlite3.connect(self.db_path) as conn:
                    for data in sg_data:
                        conn.execute("""
                            INSERT INTO player_stats (player_name, sg_total, sg_total_rank, last_updated)
                            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                            ON CONFLICT(player_name) DO UPDATE SET
                                sg_total = excluded.sg_total,
                                sg_total_rank = excluded.sg_total_rank,
                                last_updated = CURRENT_TIMESTAMP
                        """, (data['player_name'], data['sg_total'], data['sg_total_rank']))
                    conn.commit()
                
                print(f"  Downloaded {len(sg_data)} SG: Total stats")
                return True
            
            return False
            
        except Exception as e:
            print(f"  Error downloading SG stats: {e}")
            return False
    
    def download_money_list(self):
        """Download season money leaders"""
        try:
            url = f"{self.base_url}/stats/stat.109.html"  # Money list
            response = self.session.get(url, timeout=10)
            
            if response.status_code != 200:
                return False
            
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', class_='table-stats') or soup.find('table')
            
            if not table:
                return False
            
            money_data = []
            rows = table.find_all('tr')[1:]
            
            for row in rows[:100]:
                cols = row.find_all('td')
                if len(cols) < 3:
                    continue
                
                try:
                    player_name = cols[1].find('a').text.strip() if cols[1].find('a') else cols[1].text.strip()
                    player_name = player_name.replace('\n', '').replace('\t', '').strip()
                    
                    money_str = cols[2].text.strip().replace('$', '').replace(',', '')
                    
                    if player_name and money_str:
                        money_data.append({
                            'player_name': player_name,
                            'season_money': float(money_str)
                        })
                except:
                    continue
            
            if money_data:
                with sqlite3.connect(self.db_path) as conn:
                    for data in money_data:
                        conn.execute("""
                            INSERT INTO player_stats (player_name, season_money, last_updated)
                            VALUES (?, ?, CURRENT_TIMESTAMP)
                            ON CONFLICT(player_name) DO UPDATE SET
                                season_money = excluded.season_money,
                                last_updated = CURRENT_TIMESTAMP
                        """, (data['player_name'], data['season_money']))
                    conn.commit()
                
                print(f"  Downloaded {len(money_data)} money list entries")
                return True
            
            return False
            
        except Exception as e:
            print(f"  Error downloading money list: {e}")
            return False
    
    def get_data_age(self):
        """Check when data was last updated"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_updated FROM player_stats 
                ORDER BY last_updated DESC LIMIT 1
            """)
            result = cursor.fetchone()
            
            if result:
                last_updated = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
                age = datetime.now() - last_updated
                return age.days
            
            return None

def main():
    """Run the data downloader"""
    downloader = PGATourDataDownloader()
    
    # Check data age
    age = downloader.get_data_age()
    if age is not None:
        print(f"\n📅 Current data is {age} days old")
        if age < 7:
            print("⚠️  Data is less than 7 days old. Download again? (y/n): ", end="")
            if input().strip().lower() != 'y':
                print("Cancelled.")
                return
    
    # Download all data
    downloader.download_all_data()
    
    print("\n✅ Done! Your app will now use this fresh data.")
    print("Run this script again next week to refresh.")

if __name__ == "__main__":
    main()
