import pandas as pd
import numpy as np
from datetime import datetime

class WinPredictor:
    """Calculates win probabilities and value scores for players"""
    
    def __init__(self):
        self.weights = {
            'fedex_rank': 0.20,
            'world_rank': 0.15,
            'sg_total': 0.10,
            'recent_form': 0.30,
            'course_history': 0.25
        }
    
    def get_ranked_field(self, tournament_info):
        """Get tournament field ranked by win probability"""
        from utils.data_fetcher import PGADataFetcher
        from utils.database import DatabaseManager
        
        data_fetcher = PGADataFetcher()
        db_manager = DatabaseManager()
        
        # Get tournament field
        field_df = data_fetcher.get_tournament_field(tournament_info.get('tournament_id'))
        
        if field_df.empty:
            # Return sample data if no real data available
            field_df = self._get_sample_field()
        
        # Calculate predictions for each player
        predictions = []
        
        for _, player in field_df.iterrows():
            player_stats = data_fetcher.get_player_stats(
                player['player_name'],
                player.get('player_id'),
                tournament_name=tournament_info.get('name')
            )
            
            # Calculate win probability
            win_prob = self._calculate_win_probability(player_stats, tournament_info)
            
            # Calculate value score
            value_score = self._calculate_value_score(player_stats, win_prob)
            
            # Check if player is already used
            is_used = db_manager.is_player_used(player['player_name'])
            
            predictions.append({
                'rank': 0,  # Will be set after sorting
                'player_name': player['player_name'],
                'win_probability': win_prob,
                'value_score': value_score,
                'fedex_rank': player_stats.get('fedex_rank', 'N/A'),
                'world_rank': player_stats.get('world_rank', 'N/A'),
                'season_money': player_stats.get('season_money', 0),
                'sg_total': player_stats.get('sg_total', 0),
                'sg_ott': player_stats.get('sg_ott', 0),
                'sg_app': player_stats.get('sg_app', 0),
                'sg_arg': player_stats.get('sg_arg', 0),
                'sg_putt': player_stats.get('sg_putt', 0),
                'recent_form': player_stats.get('recent_form', 'N/A'),
                'course_history': self._format_course_history(
                    player_stats.get('course_history'),
                    player_stats.get('detailed_course_history')
                ),
                'is_used': is_used
            })
        
        # Convert to DataFrame and sort
        predictions_df = pd.DataFrame(predictions)
        predictions_df = predictions_df.sort_values('win_probability', ascending=False).reset_index(drop=True)
        predictions_df['rank'] = range(1, len(predictions_df) + 1)
        
        return predictions_df
    
    def _calculate_win_probability(self, player_stats, tournament_info):
        """Calculate win probability based on multiple factors"""
        
        # Base probability from rankings (handle None values)
        fedex_rank = player_stats.get('fedex_rank')
        world_rank = player_stats.get('world_rank')
        
        # Default to middle rank if None
        if fedex_rank is None:
            fedex_rank = 100
        if world_rank is None:
            world_rank = 100
        
        # Convert ranks to scores (lower rank = higher score)
        fedex_score = max(0, (200 - fedex_rank) / 200) * 100
        world_score = max(0, (200 - world_rank) / 200) * 100
        
        # Strokes gained score
        sg_total = player_stats.get('sg_total', 0)
        sg_score = min(100, max(0, (sg_total + 2) * 20))  # Normalize around 0, cap at 100
        
        # Recent form score (simplified)
        form = player_stats.get('recent_form', 'N/A')
        form_scores = {
            '🔥 Excellent': 90,
            '✅ Good': 70,
            '🔶 Average': 50,
            '🔻 Poor': 30,
            'N/A': 50
        }
        form_score = form_scores.get(form, 50)
        
        # Course history score
        course_history = player_stats.get('course_history', pd.DataFrame())
        detailed_course_history = player_stats.get('detailed_course_history', pd.DataFrame())
        course_score = self._calculate_course_history_score(course_history, detailed_course_history)
        
        # Weighted average
        win_prob = (
            self.weights['fedex_rank'] * fedex_score +
            self.weights['world_rank'] * world_score +
            self.weights['sg_total'] * sg_score +
            self.weights['recent_form'] * form_score +
            self.weights['course_history'] * course_score
        )
        
        # Normalize to reasonable probability range (0.1% to 25%)
        win_prob = 0.1 + (win_prob / 100) * 24.9
        
        return round(win_prob, 2)
    
    def _calculate_course_history_score(self, course_history_df, detailed_history_df=None):
        """Calculate score based on course history with recency weighting"""
        if course_history_df.empty:
            return 50  # Neutral score if no history

        try:
            current_year = datetime.now().year

            # If we have detailed year-by-year data, use recency-weighted scoring
            if detailed_history_df is not None and not detailed_history_df.empty:
                weighted_finish_sum = 0
                weight_total = 0
                weighted_wins = 0
                weighted_top5s = 0
                weighted_top10s = 0

                for _, row in detailed_history_df.iterrows():
                    try:
                        year = int(row.get('Year', current_year))
                        f_str = str(row.get('Finish', '')).strip().upper()
                        if f_str in ('CUT', 'MC', 'MDF', 'WD', 'DQ', 'DNS', 'NONE', 'NAN'):
                            finish = 70
                        else:
                            finish = int(f_str.replace('T', ''))
                    except:
                        continue

                    # Sliding scale: 1.0 for current year, -0.15 per year, floor 0.30
                    age = current_year - year
                    weight = max(0.30, 1.0 - age * 0.15)

                    weighted_finish_sum += finish * weight
                    weight_total += weight
                    if finish == 1:
                        weighted_wins += weight
                    if finish <= 5:
                        weighted_top5s += weight
                    if finish <= 10:
                        weighted_top10s += weight

                if weight_total == 0:
                    return 50

                weighted_avg = weighted_finish_sum / weight_total

                score = 50  # Start neutral

                # Wins — tempered by weighted avg finish
                if weighted_wins > 0:
                    win_bonus = 20 * weighted_wins
                    if weighted_avg > 40:
                        win_bonus *= 0.4
                    elif weighted_avg > 30:
                        win_bonus *= 0.7
                    score += win_bonus

                score += weighted_top5s * 8
                score += weighted_top10s * 4

                # Weighted avg finish contribution
                if weighted_avg < 20:
                    score += 25
                elif weighted_avg < 30:
                    score += 15
                elif weighted_avg < 40:
                    score += 5
                elif weighted_avg > 50:
                    score -= 10

                appearances = len(detailed_history_df)
                if appearances >= 5:
                    score += 5

                return min(100, max(20, score))

            # Fallback: use aggregated stats (no recency weighting)
            row = course_history_df.iloc[0]
            wins = row.get('Wins', 0) or 0
            top_5s = row.get('Top 5s', 0) or 0
            top_10s = row.get('Top 10s', 0) or 0
            avg_finish = row.get('Avg Finish', 50)
            appearances = row.get('Appearances', 0) or 0

            score = 50
            if wins > 0:
                win_bonus = 20 * wins
                if avg_finish and avg_finish > 40:
                    win_bonus *= 0.4
                elif avg_finish and avg_finish > 30:
                    win_bonus *= 0.7
                score += win_bonus
            score += top_5s * 8
            score += top_10s * 4
            if avg_finish:
                if avg_finish < 20:
                    score += 25
                elif avg_finish < 30:
                    score += 15
                elif avg_finish < 40:
                    score += 5
                elif avg_finish > 50:
                    score -= 10
            if appearances >= 5:
                score += 5

            return min(100, max(20, score))

        except Exception as e:
            print(f"Error calculating course history score: {e}")
            return 50
    
    def _calculate_value_score(self, player_stats, win_probability):
        """Calculate value score (probability relative to ranking)"""
        
        # Value is when win probability is high relative to ranking
        # Lower ranked players with decent win probability = high value
        
        fedex_rank = player_stats.get('fedex_rank')
        if fedex_rank is None:
            fedex_rank = 100
        
        # Expected win probability based on rank
        expected_prob = max(0.1, (200 - fedex_rank) / 200 * 15)
        
        # Value is the ratio of actual to expected
        value_ratio = win_probability / expected_prob if expected_prob > 0 else 1
        
        # Convert to 0-100 scale
        value_score = min(100, value_ratio * 50)
        
        return round(value_score, 2)
    
    def _format_course_history(self, course_history_df, detailed_history_df=None):
        """Format course history for display with recency-weighted rating"""
        if course_history_df is None or course_history_df.empty:
            return "No history"
        
        try:
            row = course_history_df.iloc[0]
            wins = row.get('Wins', 0) or 0
            top_5s = row.get('Top 5s', 0) or 0
            top_10s = row.get('Top 10s', 0) or 0
            avg_finish = row.get('Avg Finish', 99)
            appearances = row.get('Appearances', 0) or 0
            best = row.get('Best', 'N/A')
            
            # Build stats detail string (always uses career totals for display)
            stats = []
            if wins > 0:
                stats.append(f"{int(wins)} win{'s' if wins > 1 else ''}")
            if top_5s > 0:
                stats.append(f"{int(top_5s)} top 5{'s' if top_5s != 1 else ''}")
            if top_10s > 0:
                stats.append(f"{int(top_10s)} top 10{'s' if top_10s != 1 else ''}")
            if avg_finish and avg_finish < 90:
                stats.append(f"Avg: {avg_finish:.1f}")
            if not stats and appearances > 0:
                stats.append(f"{int(appearances)} apps")
            stats_str = f" ({', '.join(stats)})" if stats else ""

            # Use recency-weighted stats for the RATING LABEL if detailed data available
            if detailed_history_df is not None and not detailed_history_df.empty:
                current_year = datetime.now().year
                weighted_finish_sum = 0
                weight_total = 0
                weighted_wins = 0
                weighted_top10s = 0

                for _, r in detailed_history_df.iterrows():
                    try:
                        year = int(r.get('Year', current_year))
                        f_str = str(r.get('Finish', '')).strip().upper()
                        finish = 70 if f_str in ('CUT', 'MC', 'MDF', 'WD', 'DQ', 'DNS', 'NONE', 'NAN') \
                            else int(f_str.replace('T', ''))
                    except:
                        continue
                    age = current_year - year
                    weight = max(0.30, 1.0 - age * 0.15)
                    weighted_finish_sum += finish * weight
                    weight_total += weight
                    if finish == 1:
                        weighted_wins += weight
                    if finish <= 10:
                        weighted_top10s += weight

                w_avg = weighted_finish_sum / weight_total if weight_total else avg_finish
                avg_ok = w_avg <= 35
                avg_decent = w_avg <= 50

            else:
                # Fall back to career averages
                weighted_wins = wins
                weighted_top10s = top_10s
                avg_ok = avg_finish and avg_finish <= 35
                avg_decent = avg_finish and avg_finish <= 50

            # Rate based on recency-weighted performance
            if (weighted_wins > 0 and avg_ok) or (weighted_top10s >= 3 and avg_ok):
                return f"🔥 Excellent{stats_str}"
            elif weighted_wins > 0 and avg_decent:
                return f"✅ Good{stats_str}"
            elif weighted_top10s >= 3 or (weighted_top10s >= 1 and avg_ok):
                return f"✅ Good{stats_str}"
            elif weighted_top10s >= 1 or (avg_finish and avg_finish < 40):
                return f"🔶 Average{stats_str}"
            else:
                return f"🔻 Poor{stats_str}" if stats_str else "🔻 Poor"
        except Exception as e:
            return "N/A"
    
    def _is_top_10(self, finish):
        """Check if finish is top 10"""
        try:
            if str(finish).startswith('T'):
                return int(finish[1:]) <= 10
            return int(finish) <= 10
        except:
            return False
    
    def _made_cut(self, finish):
        """Check if player made the cut"""
        return str(finish) not in ['MC', 'WD', 'DQ']
    
    def _get_sample_field(self):
        """Return sample field data for testing"""
        sample_players = [
            {'player_name': 'Scottie Scheffler', 'player_id': '46046', 'fedex_rank': 1, 'world_rank': 1},
            {'player_name': 'Rory McIlroy', 'player_id': '28237', 'fedex_rank': 2, 'world_rank': 3},
        ]
        
        return pd.DataFrame(sample_players)
    
    def adjust_for_field_strength(self, predictions_df, field_strength='strong'):
        """Adjust win probabilities based on field strength"""
        
        multipliers = {
            'weak': 1.3,      # Spread out probabilities more
            'average': 1.0,
            'strong': 0.8,    # Compress probabilities
            'elite': 0.6      # Major championship level
        }
        
        multiplier = multipliers.get(field_strength, 1.0)
        
        predictions_df['win_probability'] = predictions_df['win_probability'] * multiplier
        predictions_df['win_probability'] = predictions_df['win_probability'].clip(0.1, 25.0)
        
        return predictions_df
    
    def get_course_fit_players(self, tournament_info, top_n=10):
        """Get players who fit the course well"""
        return []
    
    def get_value_picks(self, predictions_df, min_rank=20, max_rank=60):
        """Get high-value picks (good probability, lower ranked)"""
        value_picks = predictions_df[
            (predictions_df['fedex_rank'] >= min_rank) & 
            (predictions_df['fedex_rank'] <= max_rank) &
            (predictions_df['value_score'] >= 60)
        ].copy()
        
        return value_picks.sort_values('value_score', ascending=False)
