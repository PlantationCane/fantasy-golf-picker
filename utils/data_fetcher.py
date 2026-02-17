import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import json
import time

class PGADataFetcher:
    """Fetches data from PGA Tour and database"""
    
    def __init__(self):
        self.base_url = "https://www.pgatour.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.current_tournament = None
        self.player_cache = {}
        self.db_path = Path(__file__).parent.parent / "pga_fantasy.db"
    
    def get_current_tournament(self):
        """Get current week's tournament information from ESPN API"""
        try:
            # Fetch live tournament data from ESPN
            response = requests.get('https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard', timeout=10)
            data = response.json()
            
            events = data.get('events', [])
            
            # Look for in-progress or scheduled tournament
            for event in events:
                status = event.get('status', {}).get('type', {}).get('name', '')
                
                if status in ['STATUS_IN_PROGRESS', 'STATUS_SCHEDULED']:
                    # Extract tournament info
                    name = event.get('name', 'Unknown Tournament')
                    
                    # Get course name from competitions
                    course = 'TBD'
                    competitions = event.get('competitions', [])
                    if competitions:
                        venue = competitions[0].get('venue', {})
                        course = venue.get('fullName', 'TBD')
                    
                    # Get dates
                    date_str = event.get('date', '')
                    dates = 'TBD'
                    if date_str:
                        try:
                            start_date = datetime.strptime(date_str[:10], '%Y-%m-%d')
                            end_date = start_date + timedelta(days=3)
                            dates = f"{start_date.strftime('%b %d')}-{end_date.strftime('%d')}, {start_date.year}"
                        except:
                            dates = date_str[:10]
                    
                    tournament_info = {
                        'name': name,
                        'dates': dates,
                        'course': course,
                        'purse': 'TBD',
                        'tournament_id': event.get('id', '')
                    }
                    
                    self.current_tournament = tournament_info
                    return tournament_info
            
            # No in-progress/scheduled event found — use calendar to find next upcoming
            leagues = data.get('leagues', [])
            if leagues:
                calendar = leagues[0].get('calendar', [])
                now = datetime.utcnow()
                
                for entry in calendar:
                    start_str = entry.get('startDate', '')
                    if not start_str:
                        continue
                    try:
                        start_date = datetime.strptime(start_str[:10], '%Y-%m-%d')
                    except:
                        continue
                    
                    # Find the next tournament that hasn't ended yet
                    end_str = entry.get('endDate', start_str)
                    try:
                        end_date = datetime.strptime(end_str[:10], '%Y-%m-%d')
                    except:
                        end_date = start_date + timedelta(days=3)
                    
                    if end_date.date() >= (now - timedelta(days=1)).date():
                        name = entry.get('label', 'Unknown Tournament')
                        event_id = entry.get('id', '')
                        dates = f"{start_date.strftime('%b %d')}-{end_date.strftime('%d')}, {start_date.year}"
                        
                        # Try to get venue from the event detail API
                        course = 'TBD'
                        try:
                            detail_url = f"https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard?dates={start_date.strftime('%Y%m%d')}"
                            detail_resp = requests.get(detail_url, timeout=10)
                            detail_data = detail_resp.json()
                            for evt in detail_data.get('events', []):
                                comps = evt.get('competitions', [])
                                if comps:
                                    venue = comps[0].get('venue', {})
                                    course = venue.get('fullName', 'TBD')
                                    break
                        except:
                            pass
                        
                        tournament_info = {
                            'name': name,
                            'dates': dates,
                            'course': course,
                            'purse': 'TBD',
                            'tournament_id': event_id
                        }
                        
                        self.current_tournament = tournament_info
                        return tournament_info
            
            # Nothing found at all
            return {
                'name': 'No Current Tournament',
                'dates': 'TBD',
                'course': 'TBD',
                'purse': 'TBD',
                'tournament_id': ''
            }
            
        except Exception as e:
            print(f"Error fetching current tournament: {e}")
            return {
                'name': 'Tournament Data Unavailable',
                'dates': 'TBD',
                'course': 'TBD',
                'purse': 'TBD',
                'tournament_id': ''
            }
    
    def get_tournament_field(self, tournament_id=None):
        """Get list of players with 2026 tournament results"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # ONLY players with 2026 results - reduces from 833 to ~194
                query = """
                    SELECT DISTINCT player_name
                    FROM tournament_results_2026
                    ORDER BY player_name
                """
                
                df = pd.read_sql_query(query, conn)
                df.columns = ['player_name']
                df['player_id'] = None
                df['fedex_rank'] = None
                df['world_rank'] = None
                
                return df
                
        except Exception as e:
            print(f"Error fetching field: {e}")
            return pd.DataFrame()
    
    def get_player_stats(self, player_name, player_id=None, tournament_name=None):
        """Get comprehensive player statistics from database"""
        try:
            # Check cache first
            if player_name in self.player_cache:
                cached_time, data = self.player_cache[player_name]
                if datetime.now() - cached_time < timedelta(hours=24):
                    return data
            
            # Fetch from database
            with sqlite3.connect(self.db_path) as conn:
                # Get player stats
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT fedex_rank, season_money, sg_total
                    FROM player_stats
                    WHERE player_name = ?
                """, (player_name,))
                
                stats_row = cursor.fetchone()
                
                if stats_row:
                    fedex_rank, season_money, sg_total = stats_row
                else:
                    fedex_rank, season_money, sg_total = None, 0, 0
                
                # Get recent form
                cursor.execute("""
                    SELECT avg_finish, form_rating
                    FROM player_recent_form
                    WHERE player_name = ?
                """, (player_name,))
                
                form_row = cursor.fetchone()
                recent_form = self._format_form_rating(form_row[1] if form_row else None, player_name)
                
                # Get tournament results for 2026
                results_df = pd.read_sql_query("""
                    SELECT tournament_name as 'Tournament',
                           tournament_date as 'Date',
                           finish_position as 'Finish',
                           score_to_par as 'Score',
                           earnings as 'Earnings'
                    FROM tournament_results_2026
                    WHERE player_name = ?
                    ORDER BY tournament_date DESC
                """, conn, params=(player_name,))
                
                # Get tournament history - dynamic based on current tournament
                if tournament_name:
                    # Extract key tournament identifier (e.g., "Pebble Beach" from "AT&T Pebble Beach Pro-Am")
                    # Common keywords to identify tournaments
                    tournament_keywords = ['Pebble Beach', 'Genesis', 'Memorial', 'Players', 'Masters', 
                                         'PGA Championship', 'U.S. Open', 'Open Championship', 'Phoenix',
                                         'Honda Classic', 'Arnold Palmer', 'Wells Fargo', 'Byron Nelson']
                    
                    # Find matching keyword in tournament name
                    search_term = None
                    for keyword in tournament_keywords:
                        if keyword.lower() in tournament_name.lower():
                            search_term = keyword
                            break
                    
                    # If no keyword match, use the last 2-3 significant words
                    if not search_term:
                        words = tournament_name.split()
                        search_term = ' '.join(words[-2:]) if len(words) >= 2 else tournament_name
                    
                    # Get detailed year-by-year tournament history
                    detailed_history_df = pd.read_sql_query("""
                        SELECT year as 'Year',
                               finish_position as 'Finish',
                               score as 'Score',
                               earnings as 'Earnings',
                               sg_total as 'SG Total'
                        FROM historical_results
                        WHERE player_name = ? AND tournament_name LIKE ?
                        ORDER BY year DESC
                    """, conn, params=(player_name, f'%{search_term}%'))
                    
                    # Compute aggregated stats from detailed history
                    if not detailed_history_df.empty:
                        appearances = len(detailed_history_df)
                        
                        # Parse finishes (handle "T3", "CUT", etc.)
                        finishes = []
                        for f in detailed_history_df['Finish']:
                            try:
                                # Remove 'T' prefix and convert
                                finish_str = str(f).replace('T', '').replace('CUT', '999')
                                finishes.append(int(finish_str))
                            except:
                                pass
                        
                        if finishes:
                            wins = sum(1 for f in finishes if f == 1)
                            top_5s = sum(1 for f in finishes if f <= 5)
                            top_10s = sum(1 for f in finishes if f <= 10)
                            valid_finishes = [f for f in finishes if f < 900]  # Exclude missed cuts
                            avg_finish = sum(valid_finishes) / len(valid_finishes) if valid_finishes else 0
                            best_finish = min(finishes) if finishes else 0
                            last_year = detailed_history_df['Year'].iloc[0] if 'Year' in detailed_history_df else None
                            
                            course_history_df = pd.DataFrame([{
                                'Appearances': appearances,
                                'Wins': wins,
                                'Top 5s': top_5s,
                                'Top 10s': top_10s,
                                'Avg Finish': round(avg_finish, 1),
                                'Best': best_finish,
                                'Last Played': last_year
                            }])
                        else:
                            course_history_df = pd.DataFrame()
                    else:
                        course_history_df = pd.DataFrame()
                else:
                    # No tournament specified - return empty DataFrames
                    course_history_df = pd.DataFrame()
                    detailed_history_df = pd.DataFrame()
                
                stats = {
                    'name': player_name,
                    'player_id': player_id,
                    'fedex_rank': fedex_rank,
                    'world_rank': None,  # Not in our database
                    'season_money': season_money or 0,
                    'sg_total': sg_total or 0,
                    'sg_total_rank': None,
                    'sg_ott': 0,
                    'sg_app': 0,
                    'sg_arg': 0,
                    'sg_putt': 0,
                    'recent_form': recent_form,
                    'tournament_results': results_df,
                    'course_history': course_history_df,
                    'detailed_course_history': detailed_history_df
                }
            
            # Cache the data
            self.player_cache[player_name] = (datetime.now(), stats)
            
            return stats
            
        except Exception as e:
            print(f"Error fetching player stats for {player_name}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'name': player_name,
                'player_id': player_id,
                'fedex_rank': None,
                'world_rank': None,
                'season_money': 0,
                'sg_total': 0,
                'sg_total_rank': None,
                'sg_ott': 0,
                'sg_app': 0,
                'sg_arg': 0,
                'sg_putt': 0,
                'recent_form': 'N/A',
                'tournament_results': pd.DataFrame(),
                'course_history': pd.DataFrame(),
                'detailed_course_history': pd.DataFrame()
            }
    
    def _format_form_rating(self, rating, player_name=None):
        """Convert form rating to display string with stats"""
        if rating is None:
            return 'N/A'
        
        # If already a string description, check if it needs stats added
        if isinstance(rating, str):
            # If it already has stats in it, return as-is
            if '(' in rating:
                return rating
            # Otherwise return the string
            return rating
        
        # Convert to float for numeric comparison
        try:
            rating = float(rating)
        except (ValueError, TypeError):
            return 'N/A'
        
        # Get actual form stats if we have player_name
        stats_detail = ""
        if player_name:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT recent_events, avg_finish, best_finish
                        FROM player_recent_form
                        WHERE player_name = ?
                    """, (player_name,))
                    form_row = cursor.fetchone()
                    if form_row:
                        events, avg, best = form_row
                        if events and avg:
                            stats_detail = f" ({events} events, Avg: {avg:.1f}, Best: {best})"
            except:
                pass
        
        if rating >= 80:
            return f'🔥 Excellent{stats_detail}'
        elif rating >= 60:
            return f'✅ Good{stats_detail}'
        elif rating >= 40:
            return f'🔶 Average{stats_detail}'
        else:
            return f'🔻 Poor{stats_detail}'
    
    def search_player(self, player_name):
        """Search for a player and return their stats"""
        try:
            return self.get_player_stats(player_name)
        except:
            return None
    
    def refresh_data(self):
        """Refresh all cached data"""
        self.current_tournament = None
        self.player_cache.clear()
        self.get_current_tournament()
        return True
