"""
ESPN Current Season Scraper

Automatically downloads 2026 PGA Tour stats from ESPN
Run weekly to keep data fresh

Usage: python scrape_espn_current.py
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime
import time

class ESPNCurrentSeasonScraper:
    """Scrapes current season stats from ESPN"""
    
    def __init__(self, db_path="pga_fantasy.db"):
        self.db_path = Path(__file__).parent / db_path
        self.base_url = "https://www.espn.com/golf"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.init_tables()
    
    def init_tables(self):
        """Initialize current season tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Player stats table
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
            
            # Tournament field table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tournament_field (
                    player_name TEXT PRIMARY KEY,
                    fedex_rank INTEGER,
                    world_rank INTEGER,
                    last_updated TIMESTAMP
                )
            """)
            
            # Current tournament table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS current_tournament (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    dates TEXT,
                    course TEXT,
                    purse TEXT,
                    tournament_id TEXT,
                    last_updated TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS player_performance_stats (
                    player_name TEXT PRIMARY KEY,
                    scoring_avg REAL,
                    driving_distance REAL,
                    driving_accuracy REAL,
                    gir_pct REAL,
                    putts_per_hole REAL,
                    birdies_per_round REAL,
                    scoring_avg_rank INTEGER,
                    driving_distance_rank INTEGER,
                    driving_accuracy_rank INTEGER,
                    gir_pct_rank INTEGER,
                    putts_per_hole_rank INTEGER,
                    birdies_per_round_rank INTEGER,
                    composite_score REAL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def scrape_all(self):
        """Scrape all current season data"""
        print("\n" + "="*60)
        print("🏌️ ESPN CURRENT SEASON SCRAPER")
        print("="*60)
        
        results = {
            'fedex_cup': False,
            'money_list': False,
            'world_rankings': False,
            'performance_stats': False,
            'tournament': False
        }
        
        # FedEx Cup Rankings
        print("\n📊 Scraping FedEx Cup Rankings...")
        results['fedex_cup'] = self.scrape_fedex_cup()
        if results['fedex_cup']:
            print("✅ FedEx Cup complete!")
        else:
            print("⚠️  FedEx Cup - partial data")
        
        time.sleep(2)  # Be nice to ESPN
        
        # Money List
        print("\n💰 Scraping Money List...")
        results['money_list'] = self.scrape_money_list()
        if results['money_list']:
            print("✅ Money List complete!")
        else:
            print("⚠️  Money List - partial data")
        
        time.sleep(2)
        
        # World Rankings
        print("\n🌍 Scraping World Golf Rankings...")
        results['world_rankings'] = self.scrape_world_rankings()
        if results['world_rankings']:
            print("✅ World Rankings complete!")
        else:
            print("⚠️  World Rankings - partial data")
        
        time.sleep(2)
        
        # Performance Stats from ESPN API
        print("\n📈 Scraping Performance Stats...")
        results['performance_stats'] = self.scrape_performance_stats()
        if results['performance_stats']:
            print("✅ Performance Stats complete!")
        else:
            print("⚠️  Performance Stats - partial data")

        time.sleep(2)

        # Current Tournament
        print("\n🏆 Getting Current Tournament...")
        results['tournament'] = self.get_current_tournament()
        if results['tournament']:
            print("✅ Tournament info complete!")
        else:
            print("⚠️  Tournament info - using manual entry")
        
        print("\n" + "="*60)
        if all(results.values()):
            print("✅ All data scraped successfully!")
        else:
            print("⚠️  Some data incomplete (see warnings above)")
        print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        return results
    
    def scrape_fedex_cup(self):
        """Scrape FedEx Cup standings from ESPN"""
        try:
            url = f"{self.base_url}/stats/player/_/table/general/sort/cupPoints/dir/desc"
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                print(f"   Could not access ESPN (status {response.status_code})")
                return False
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the stats table
            table = soup.find('table', class_='Table')
            
            if not table:
                print("   Could not find ESPN stats table")
                return False
            
            players = []
            rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
            
            print(f"   Found {len(rows)} players")
            
            for idx, row in enumerate(rows, 1):
                try:
                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue
                    
                    # Player name is usually in a link
                    name_cell = cells[0].find('a') or cells[0]
                    player_name = name_cell.text.strip()
                    
                    # Points are typically in the last relevant column
                    points = 0
                    for cell in cells[1:]:
                        try:
                            val = cell.text.strip().replace(',', '')
                            if val.replace('.', '').isdigit():
                                points = float(val)
                                break
                        except:
                            continue
                    
                    if player_name and idx <= 150:  # Top 150
                        players.append({
                            'player_name': player_name,
                            'fedex_rank': idx,
                            'fedex_points': points
                        })
                except Exception as e:
                    continue
            
            if not players:
                print("   No players extracted")
                return False
            
            # Save to database
            with sqlite3.connect(self.db_path) as conn:
                for player in players:
                    # Update player_stats
                    conn.execute("""
                        INSERT INTO player_stats (player_name, fedex_rank, last_updated)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(player_name) DO UPDATE SET
                            fedex_rank = excluded.fedex_rank,
                            last_updated = CURRENT_TIMESTAMP
                    """, (player['player_name'], player['fedex_rank']))
                    
                    # Update tournament_field
                    conn.execute("""
                        INSERT INTO tournament_field (player_name, fedex_rank, last_updated)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(player_name) DO UPDATE SET
                            fedex_rank = excluded.fedex_rank,
                            last_updated = CURRENT_TIMESTAMP
                    """, (player['player_name'], player['fedex_rank']))
                
                conn.commit()
            
            print(f"   Saved {len(players)} FedEx Cup rankings")
            return True
            
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def scrape_money_list(self):
        """Scrape money list from ESPN"""
        try:
            url = f"{self.base_url}/stats/player/_/table/general/sort/earnings/dir/desc"
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                return False
            
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', class_='Table')
            
            if not table:
                return False
            
            money_data = []
            rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
            
            for row in rows[:150]:
                try:
                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue
                    
                    name_cell = cells[0].find('a') or cells[0]
                    player_name = name_cell.text.strip()
                    
                    # Find money column (usually has $)
                    money = 0
                    for cell in cells[1:]:
                        text = cell.text.strip()
                        if '$' in text:
                            try:
                                money = float(text.replace('$', '').replace(',', ''))
                                break
                            except:
                                continue
                    
                    if player_name and money > 0:
                        money_data.append({
                            'player_name': player_name,
                            'season_money': money
                        })
                except:
                    continue
            
            if not money_data:
                return False
            
            # Save to database
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
            
            print(f"   Saved {len(money_data)} money list entries")
            return True
            
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def scrape_world_rankings(self):
        """Scrape Official World Golf Rankings from ESPN"""
        try:
            url = f"{self.base_url}/rankings"
            response = self.session.get(url, timeout=15)
            
            if response.status_code != 200:
                print(f"   Could not access ESPN rankings (status {response.status_code})")
                return False
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the rankings table
            table = soup.find('table', class_='Table')
            
            if not table:
                print("   Could not find rankings table")
                return False
            
            rankings = []
            rows = table.find('tbody').find_all('tr') if table.find('tbody') else []
            
            print(f"   Found {len(rows)} ranked players")
            
            for idx, row in enumerate(rows, 1):
                try:
                    cells = row.find_all('td')
                    if len(cells) < 2:
                        continue
                    
                    # Rank is first cell or row index
                    rank_text = cells[0].text.strip()
                    try:
                        world_rank = int(rank_text)
                    except:
                        world_rank = idx
                    
                    # Player name is usually in a link
                    name_cell = cells[1].find('a') if len(cells) > 1 else cells[0].find('a')
                    if not name_cell:
                        name_cell = cells[1] if len(cells) > 1 else cells[0]
                    player_name = name_cell.text.strip()
                    
                    if player_name and world_rank <= 200:
                        rankings.append({
                            'player_name': player_name,
                            'world_rank': world_rank
                        })
                except Exception as e:
                    continue
            
            if not rankings:
                print("   No rankings extracted")
                return False
            
            # Save to database
            with sqlite3.connect(self.db_path) as conn:
                for player in rankings:
                    conn.execute("""
                        INSERT INTO player_stats (player_name, world_rank, last_updated)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(player_name) DO UPDATE SET
                            world_rank = excluded.world_rank,
                            last_updated = CURRENT_TIMESTAMP
                    """, (player['player_name'], player['world_rank']))
                conn.commit()
            
            print(f"   Saved {len(rankings)} world rankings")
            return True
            
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def scrape_performance_stats(self):
        """Scrape performance stats from ESPN statistics API"""
        try:
            url = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/statistics"
            response = requests.get(url, timeout=15)
            
            if response.status_code != 200:
                print(f"   ❌ ESPN stats API returned {response.status_code}")
                return False
            
            data = response.json()
            stats_data = data.get('stats', {})
            categories = stats_data.get('categories', []) if isinstance(stats_data, dict) else []
            
            if not categories:
                print("   ❌ No stat categories found")
                return False
            
            # Map ESPN category names to our column names
            stat_map = {
                'scoringAverage': 'scoring_avg',
                'yardsPerDrive': 'driving_distance',
                'driveAccuracyPct': 'driving_accuracy',
                'greensInRegPct': 'gir_pct',
                'strokesPerHole': 'putts_per_hole',
                'birdiesPerRound': 'birdies_per_round',
            }
            
            # Collect all player stats across categories
            all_players = {}  # name -> {stat_col: value}
            
            for cat in categories:
                cat_name = cat.get('name', '')
                col_name = stat_map.get(cat_name)
                
                if col_name is None:
                    continue
                
                leaders = cat.get('leaders', [])
                for rank, entry in enumerate(leaders, 1):
                    name = entry.get('athlete', {}).get('displayName', '')
                    value = entry.get('value')
                    
                    if not name or value is None:
                        continue
                    
                    if name not in all_players:
                        all_players[name] = {}
                    
                    all_players[name][col_name] = float(value)
                    all_players[name][f'{col_name}_rank'] = rank
            
            if not all_players:
                print("   ❌ No player stats collected")
                return False
            
            print(f"   Found stats for {len(all_players)} players")
            
            # Compute composite score
            # Weights based on correlation with tournament success
            weights = {
                'scoring_avg': 0.35,      # strongest predictor
                'gir_pct': 0.25,           # approach quality
                'driving_distance': 0.15,  # power
                'driving_accuracy': 0.10,  # precision
                'putts_per_hole': 0.10,    # putting
                'birdies_per_round': 0.05, # explosiveness
            }
            
            # For each player, compute weighted rank score
            for name, stats in all_players.items():
                weighted_sum = 0
                weight_total = 0
                
                for stat, weight in weights.items():
                    rank_key = f'{stat}_rank'
                    if rank_key in stats:
                        # Convert rank (1=best) to score (100=best)
                        # Rank 1 out of 50 = score 100, Rank 50 = score 2
                        rank = stats[rank_key]
                        score = max(0, (51 - rank) / 50 * 100)
                        weighted_sum += score * weight
                        weight_total += weight
                
                if weight_total > 0:
                    stats['composite_score'] = round(weighted_sum / 1.0, 1)
                else:
                    stats['composite_score'] = 0
            
            # Save to database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                saved = 0
                for name, stats in all_players.items():
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO player_performance_stats
                            (player_name, scoring_avg, driving_distance, driving_accuracy,
                             gir_pct, putts_per_hole, birdies_per_round,
                             scoring_avg_rank, driving_distance_rank, driving_accuracy_rank,
                             gir_pct_rank, putts_per_hole_rank, birdies_per_round_rank,
                             composite_score, last_updated)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (
                            name,
                            stats.get('scoring_avg'),
                            stats.get('driving_distance'),
                            stats.get('driving_accuracy'),
                            stats.get('gir_pct'),
                            stats.get('putts_per_hole'),
                            stats.get('birdies_per_round'),
                            stats.get('scoring_avg_rank'),
                            stats.get('driving_distance_rank'),
                            stats.get('driving_accuracy_rank'),
                            stats.get('gir_pct_rank'),
                            stats.get('putts_per_hole_rank'),
                            stats.get('birdies_per_round_rank'),
                            stats.get('composite_score', 0),
                        ))
                        saved += 1
                    except Exception as e:
                        print(f"   ⚠️  Error saving {name}: {e}")
                
                conn.commit()
                print(f"   ✅ Saved performance stats for {saved} players")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error scraping performance stats: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_current_tournament(self):
        """Get current tournament info"""
        try:
            # Try to scrape from ESPN schedule
            url = f"{self.base_url}/schedule"
            response = self.session.get(url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for "This Week" or current tournament
                # ESPN structure varies, so we'll use a fallback
                
                # Fallback: Week-based schedule
                from datetime import datetime
                week_of_year = datetime.now().isocalendar()[1]
                
                # 2026 PGA Tour schedule
                schedule = {
                    1: {"name": "The Sentry", "course": "Kapalua", "dates": "Jan 2-5"},
                    2: {"name": "The American Express", "course": "La Quinta", "dates": "Jan 16-19"},
                    3: {"name": "Farmers Insurance Open", "course": "Torrey Pines", "dates": "Jan 23-26"},
                    4: {"name": "AT&T Pebble Beach Pro-Am", "course": "Pebble Beach", "dates": "Jan 30 - Feb 2"},
                    5: {"name": "WM Phoenix Open", "course": "TPC Scottsdale", "dates": "Feb 6-9"},
                    6: {"name": "The Genesis Invitational", "course": "Riviera CC", "dates": "Feb 13-16"},
                    7: {"name": "The Cognizant Classic", "course": "PGA National", "dates": "Feb 20-23"},
                    8: {"name": "The Mexico Open", "course": "Vidanta Vallarta", "dates": "Feb 27 - Mar 2"},
                    # Add more as season progresses
                }
                
                tournament = schedule.get(week_of_year, {"name": "Current Tournament", "course": "TBD", "dates": "This Week"})
                
                print(f"   Detected: {tournament['name']}")
                
                # Save to database
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO current_tournament
                        (id, name, dates, course, purse, tournament_id, last_updated)
                        VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (tournament['name'], tournament['dates'], tournament['course'], 'TBD', 'current'))
                    conn.commit()
                
                return True
        except Exception as e:
            print(f"   Error: {e}")
        
        return False
    
    def show_stats(self):
        """Show current database stats"""
        print("\n" + "="*60)
        print("📊 DATABASE STATS")
        print("="*60)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Players in system
                cursor.execute("SELECT COUNT(*) FROM player_stats")
                total = cursor.fetchone()[0]
                print(f"Total players: {total}")
                
                # With FedEx ranks
                cursor.execute("SELECT COUNT(*) FROM player_stats WHERE fedex_rank IS NOT NULL")
                ranked = cursor.fetchone()[0]
                print(f"FedEx ranked: {ranked}")
                
                # With money
                cursor.execute("SELECT COUNT(*) FROM player_stats WHERE season_money > 0")
                money = cursor.fetchone()[0]
                print(f"With earnings: {money}")
                
                # With world rank
                cursor.execute("SELECT COUNT(*) FROM player_stats WHERE world_rank IS NOT NULL")
                world_ranked = cursor.fetchone()[0]
                print(f"World ranked: {world_ranked}")
                
                if ranked > 0:
                    # Top 10
                    print("\nTop 10 FedEx Cup:")
                    cursor.execute("""
                        SELECT player_name, fedex_rank, season_money
                        FROM player_stats
                        WHERE fedex_rank IS NOT NULL
                        ORDER BY fedex_rank
                        LIMIT 10
                    """)
                    for name, rank, money_val in cursor.fetchall():
                        money_str = f"${money_val:,.0f}" if money_val else "N/A"
                        print(f"   {rank}. {name} - {money_str}")
        except Exception as e:
            print(f"Error showing stats: {e}")
        
        print("="*60)

def main():
    scraper = ESPNCurrentSeasonScraper()
    
    # Scrape all data
    results = scraper.scrape_all()
    
    # Show stats
    scraper.show_stats()
    
    print("\n✅ Done! Run this script again next Monday to refresh.")
    print("📱 Start your app: streamlit run app.py")

if __name__ == "__main__":
    main()
