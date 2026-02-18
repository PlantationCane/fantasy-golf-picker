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
        """Get current week's tournament information"""
        # Hardcoded for Genesis Invitational
        tournament_info = {
            'name': 'The Genesis Invitational',
            'dates': 'Feb 13-16, 2026',
            'course': 'Riviera Country Club',
            'purse': '$20,000,000',
            'tournament_id': 'r2026008'
        }
        
        self.current_tournament = tournament_info
        return tournament_info
    
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
    
    def get_player_stats(self, player_name, player_id=None):
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
                
                # Get Riviera course history (aggregated stats)
                course_history_df = pd.read_sql_query("""
                    SELECT appearances as 'Appearances',
                           wins as 'Wins',
                           top_5s as 'Top 5s',
                           top_10s as 'Top 10s',
                           avg_finish as 'Avg Finish',
                           best_finish as 'Best',
                           last_played as 'Last Played'
                    FROM course_history
                    WHERE player_name = ? AND course_name LIKE '%Riviera%'
                    LIMIT 1
                """, conn, params=(player_name,))
                
                # Get detailed year-by-year Riviera history
                detailed_history_df = pd.read_sql_query("""
                    SELECT year as 'Year',
                           finish_position as 'Finish',
                           score as 'Score',
                           earnings as 'Earnings',
                           sg_total as 'SG Total'
                    FROM historical_results
                    WHERE player_name = ? AND course_name LIKE '%Riviera%'
                    ORDER BY year DESC
                """, conn, params=(player_name,))
                
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
