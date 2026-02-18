import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from utils.data_fetcher import PGADataFetcher
from utils.database import DatabaseManager
from utils.predictor import WinPredictor

# Page configuration
st.set_page_config(
    page_title="PGA Fantasy Tracker",
    page_icon="⛳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .used-player {
        opacity: 0.3;
        background-color: #f0f0f0;
        pointer-events: none;
    }
    .available-player {
        cursor: pointer;
    }
    .player-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .stat-box {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 10px;
        margin: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'db_manager' not in st.session_state:
    st.session_state.db_manager = DatabaseManager()
if 'data_fetcher' not in st.session_state:
    st.session_state.data_fetcher = PGADataFetcher()
if 'predictor' not in st.session_state:
    st.session_state.predictor = WinPredictor()

def main():
    st.title("⛳ PGA Fantasy Tracker 2026")
    
    # Sidebar
    with st.sidebar:
        st.header("Season Overview")
        
        # Display current picks count
        picks_used = st.session_state.db_manager.get_picks_count()
        st.metric("Players Used", f"{picks_used}")
        st.metric("Players Remaining", f"{200 - picks_used}")  # Approximate PGA Tour field
        
        st.divider()
        
        # Refresh data button
        if st.button("🔄 Refresh Tournament Data", use_container_width=True):
            with st.spinner("Fetching latest data..."):
                st.session_state.data_fetcher.refresh_data()
            st.success("Data refreshed!")
            st.rerun()
        
        st.divider()
        
        # View mode selection
        view_mode = st.radio(
            "View Mode",
            ["This Week's Tournament", "Season Picks History", "Player Search"]
        )
    
    # Main content area
    if view_mode == "This Week's Tournament":
        show_tournament_view()
    elif view_mode == "Season Picks History":
        show_picks_history()
    else:
        show_player_search()

def show_tournament_view():
    """Display current week's tournament with player rankings"""
    st.header("This Week's Tournament")
    
    # Get current tournament info
    tournament_info = st.session_state.data_fetcher.get_current_tournament()
    
    if not tournament_info:
        st.warning("No tournament data available. Click 'Refresh Tournament Data' to fetch latest information.")
        return
    
    # Tournament header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader(f"🏆 {tournament_info.get('name', 'Tournament')}")
    with col2:
        st.write(f"**Dates:** {tournament_info.get('dates', 'TBD')}")
    with col3:
        st.write(f"**Purse:** ${tournament_info.get('purse', 'TBD')}")
    
    st.write(f"**Course:** {tournament_info.get('course', 'TBD')}")
    
    st.divider()
    
    # Get field with predictions
    field_df = st.session_state.predictor.get_ranked_field(tournament_info)
    
    if field_df.empty:
        st.info("Field not yet available for this tournament.")
        return
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        prioritize_available = st.checkbox("Prioritize Available Players", value=True)
    with col2:
        min_win_prob = st.slider("Min Win Probability %", 0, 100, 0)
    with col3:
        sort_by = st.selectbox("Sort By", ["Win Probability", "Value Score", "FedEx Rank", "Recent Form"])
    
    # Apply filters
    if min_win_prob > 0:
        field_df = field_df[field_df['win_probability'] >= min_win_prob]
    
    # Don't filter out used players - they'll show greyed out in their proper rank
    
    # Display player grid
    st.subheader("Tournament Field")
    
    # Create columns for player cards
    for idx, row in field_df.iterrows():
        player_card(row, tournament_info)

def player_card(player_data, tournament_info):
    """Display individual player card"""
    is_used = st.session_state.db_manager.is_player_used(player_data['player_name'])
    
    # Create expandable player card
    card_class = "used-player" if is_used else "available-player"
    
    with st.expander(
        f"{'🚫' if is_used else '✅'} #{player_data.get('rank', 'N/A')} {player_data['player_name']} - "
        f"Win Prob: {player_data.get('win_probability', 0):.1f}% | "
        f"Value: {player_data.get('value_score', 0):.1f}",
        expanded=False
    ):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("FedEx Rank", player_data.get('fedex_rank', 'N/A'))
            st.metric("World Rank", player_data.get('world_rank', 'N/A'))
        
        with col2:
            st.metric("Season Earnings", f"${player_data.get('season_money', 0):,.0f}")
            st.metric("Recent Form", player_data.get('recent_form', 'N/A'))

        with col3:
            st.metric("Course History", player_data.get('course_history', 'N/A'))
            st.metric("Perf Score", f"{player_data.get('composite_score', 0):.1f}")

        with col4:
            st.metric("Scoring Avg", player_data.get('scoring_avg') or 'N/A')
            st.metric("GIR %", player_data.get('gir_pct') or 'N/A')

        # ESPN Performance Stats
        perf_name = player_data.get('player_name', '')
        try:
            import sqlite3
            perf_conn = st.session_state.db_manager._get_conn()
            perf_row = perf_conn.execute(
                "SELECT scoring_avg, driving_distance, driving_accuracy, gir_pct, putts_per_hole, birdies_per_round, scoring_avg_rank, driving_distance_rank, driving_accuracy_rank, gir_pct_rank, putts_per_hole_rank, birdies_per_round_rank, composite_score FROM player_performance_stats WHERE player_name = ?",
                (perf_name,)
            ).fetchone()
            perf_conn.close()
            if perf_row:
                st.subheader("📈 Season Performance Stats")
                pc1, pc2, pc3, pc4, pc5, pc6 = st.columns(6)
                with pc1:
                    val = f"{perf_row[0]:.1f}" if perf_row[0] else "N/A"
                    rnk = f"#{perf_row[6]}" if perf_row[6] else ""
                    st.metric("Scoring Avg", val, rnk)
                with pc2:
                    val = f"{perf_row[1]:.1f}" if perf_row[1] else "N/A"
                    rnk = f"#{perf_row[7]}" if perf_row[7] else ""
                    st.metric("Drive Dist", val, rnk)
                with pc3:
                    val = f"{perf_row[2]:.1f}%" if perf_row[2] else "N/A"
                    rnk = f"#{perf_row[8]}" if perf_row[8] else ""
                    st.metric("Drive Acc", val, rnk)
                with pc4:
                    val = f"{perf_row[3]:.1f}%" if perf_row[3] else "N/A"
                    rnk = f"#{perf_row[9]}" if perf_row[9] else ""
                    st.metric("GIR %", val, rnk)
                with pc5:
                    val = f"{perf_row[4]:.3f}" if perf_row[4] else "N/A"
                    rnk = f"#{perf_row[10]}" if perf_row[10] else ""
                    st.metric("Putts/Hole", val, rnk)
                with pc6:
                    val = f"{perf_row[5]:.2f}" if perf_row[5] else "N/A"
                    rnk = f"#{perf_row[11]}" if perf_row[11] else ""
                    st.metric("Birdies/Rd", val, rnk)
        except Exception:
            pass

        # Detailed stats sections
        st.divider()
        
        # Recent tournament results
        st.subheader("📊 Recent 2026 Results")
        player_name = player_data['player_name']
        tournament_name = tournament_info.get('name', '')
        player_stats = st.session_state.data_fetcher.get_player_stats(player_name, tournament_name=tournament_name)
        tournament_results = player_stats.get('tournament_results', pd.DataFrame())
        
        if not tournament_results.empty:
            st.dataframe(tournament_results, use_container_width=True, hide_index=True)
        else:
            st.info("No 2026 tournament data available")
        
        # Tournament history details
        st.subheader(f"🏆 {tournament_name} History")
        
        # Show aggregated summary first
        course_history = player_stats.get('course_history', pd.DataFrame())
        if not course_history.empty:
            st.write(f"**Career Summary at {tournament_name}:**")
            st.dataframe(course_history, use_container_width=True, hide_index=True)
        
        # Show detailed year-by-year history
        detailed_history = player_stats.get('detailed_course_history', pd.DataFrame())
        if not detailed_history.empty:
            st.write("**Year-by-Year Results:**")
            st.dataframe(detailed_history, use_container_width=True, hide_index=True)
        elif course_history.empty:
            st.info(f"No history at {tournament_name}")
        
        # Action buttons
        if not is_used:
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"📋 View Full Stats", key=f"view_{player_data['player_name']}"):
                    show_player_details(player_data['player_name'])
            with col2:
                if st.button(f"✅ Select Player", key=f"select_{player_data['player_name']}", type="primary"):
                    select_player(player_data['player_name'])
        else:
            used_week = st.session_state.db_manager.get_player_used_week(player_data['player_name'])
            st.warning(f"⚠️ Player used in {used_week}")

def show_player_details(player_name):
    """Show detailed player statistics modal"""
    st.session_state.selected_player = player_name
    st.rerun()

def select_player(player_name):
    """Mark player as selected for this week"""
    tournament_name = st.session_state.data_fetcher.get_current_tournament().get('name', 'Current Tournament')
    
    if st.session_state.db_manager.add_pick(player_name, tournament_name):
        st.success(f"✅ {player_name} selected for {tournament_name}!")
        st.rerun()
    else:
        st.error("Failed to record selection.")

def show_picks_history():
    """Display history of all picks made"""
    st.header("Season Picks History")
    
    picks_df = st.session_state.db_manager.get_all_picks()
    
    if picks_df.empty:
        st.info("No picks made yet this season.")
        return
    
    # Summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Picks", len(picks_df))
    with col2:
        total_winnings = picks_df['money_won'].sum()
        st.metric("Total Winnings", f"${total_winnings:,.2f}")
    with col3:
        avg_finish = picks_df['finish_position'].mean()
        st.metric("Avg Finish", f"{avg_finish:.1f}" if not pd.isna(avg_finish) else "N/A")
    
    st.divider()
    
    # Picks table
    st.dataframe(
        picks_df,
        use_container_width=True,
        hide_index=True
    )

def show_player_search():
    """Search and view any player's stats"""
    st.header("Player Search")
    
    player_name = st.text_input("Enter player name:")
    
    if player_name:
        # Search for player
        player_data = st.session_state.data_fetcher.search_player(player_name)
        
        if player_data:
            display_full_player_stats(player_data)
        else:
            st.warning("Player not found.")

def display_full_player_stats(player_data):
    """Display comprehensive player statistics"""
    st.subheader(f"📊 {player_data['name']}")
    
    # Rankings row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("FedEx Cup Rank", player_data.get('fedex_rank', 'N/A'))
    with col2:
        st.metric("World Golf Rank", player_data.get('world_rank', 'N/A'))
    with col3:
        st.metric("SG: Total Rank", player_data.get('sg_total_rank', 'N/A'))
    
    st.divider()
    
    # Strokes Gained breakdown
    st.subheader("Strokes Gained Stats")
    sg_col1, sg_col2, sg_col3, sg_col4, sg_col5 = st.columns(5)
    with sg_col1:
        st.metric("Total", f"{player_data.get('sg_total', 0):.2f}")
    with sg_col2:
        st.metric("Off-the-Tee", f"{player_data.get('sg_ott', 0):.2f}")
    with sg_col3:
        st.metric("Approach", f"{player_data.get('sg_app', 0):.2f}")
    with sg_col4:
        st.metric("Around Green", f"{player_data.get('sg_arg', 0):.2f}")
    with sg_col5:
        st.metric("Putting", f"{player_data.get('sg_putt', 0):.2f}")
    
    st.divider()
    
    # Tournament results
    st.subheader("Season Tournament Results")
    results_df = player_data.get('tournament_results', pd.DataFrame())
    if not results_df.empty:
        st.dataframe(results_df, use_container_width=True)
    else:
        st.info("No tournament results available.")
    
    st.divider()
    
    # Course history
    st.subheader("Course History (This Week's Venue)")
    course_history_df = player_data.get('course_history', pd.DataFrame())
    if not course_history_df.empty:
        st.dataframe(course_history_df, use_container_width=True)
    else:
        st.info("No course history available.")

if __name__ == "__main__":
    main()
