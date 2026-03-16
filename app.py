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

    # Apply sorting
    if sort_by == 'Value Score':
        field_df = field_df.sort_values('value_score', ascending=False).reset_index(drop=True)
    elif sort_by == 'FedEx Rank':
        field_df = field_df.sort_values('fedex_rank', ascending=True, na_position='last').reset_index(drop=True)
    elif sort_by == 'Recent Form':
        form_order = {'🔥 Excellent': 0, '✅ Good': 1, '🔶 Average': 2, '🔻 Poor': 3, 'N/A': 4}
        field_df['form_sort'] = field_df['recent_form'].apply(lambda x: next((v for k, v in form_order.items() if k in str(x)), 4))
        field_df = field_df.sort_values('form_sort').reset_index(drop=True)
    field_df['rank'] = range(1, len(field_df) + 1)

    # Don't filter out used players - they'll show greyed out in their proper rank

    # Tournament course fit insights
    tournament_name = tournament_info.get('name', '')
    course_insights = {
        # ── SIGNATURE EVENTS ──────────────────────────────────────────────────
        'Pebble Beach': (
            '🎯 **Pebble Beach (AT&T Pro-Am) — What to look for:**\n\n'
            'Three-course rotation (Pebble Beach, Spyglass Hill, Monterey Peninsula) rewards consistency across very different layouts. '
            'Wind off the Pacific is a huge factor — favor players with links experience or wind-management skills. '
            'Scrambling and creativity around greens matter more than raw stats here.\n\n'
            '🏌️ Wind management & patience | 🎯 All-around game | 🏆 Multiple prior starts at Pebble | '
            '💪 Players who thrive in cold, wet conditions'
        ),
        'Genesis': (
            '🎯 **Riviera CC (Genesis Invitational) — What to look for:**\n\n'
            'Kikuyu rough grabs club heads and requires exceptional short-game creativity. Bombers have zero advantage — '
            'Riviera is a precision test from tee to green. GIR% and scrambling are the top predictors. '
            'Course history is heavily predictive; past Riviera winners/contenders deserve a major boost.\n\n'
            '🎯 Driving accuracy | 🏌️ Elite iron play & GIR% | ✂️ Creative short game | '
            '🏆 Strong course history at Riviera'
        ),
        'Arnold Palmer': (
            '🎯 **Bay Hill (Arnold Palmer Invitational) — What to look for:**\n\n'
            'Long, demanding par-70 with one of the toughest closing stretches on tour (holes 16–18). '
            'The par-4 18th over water rewards confident, long hitters. Winning scores ~-10 to -15.\n\n'
            '🏌️ Driving distance advantage | 🎯 Elite approach play / GIR% | '
            '🏆 Strong Bay Hill course history (3+ starts) | 💪 Closing ability under pressure | '
            '🌊 Comfort on risk/reward finishing holes\n\n'
            'Winner profile: Top-30 world ranking, 3+ prior Bay Hill starts, top-25 in both driving distance and approach. '
            'Rory McIlroy (3× winner) and Scheffler are the prototypes. Fade first/second-timers here.'
        ),
        'RBC Heritage': (
            '🎯 **Harbour Town (RBC Heritage) — What to look for:**\n\n'
            'One of the most accuracy-dependent courses on tour. Pete Dye design with tiny greens, tree-lined fairways, '
            'and a lighthouse finishing hole. Driving distance is nearly irrelevant — precision and touch win here. '
            'Smaller, accurate players historically outperform bombers every year.\n\n'
            '🎯 Driving accuracy (top priority) | ✂️ Precision wedge play | 🏌️ Small green management | '
            '📏 Shorter accurate hitters over big bombers | 🏆 Repeat Harbour Town contenders'
        ),
        'Cadillac': (
            '🎯 **Trump National Doral — Blue Monster (Cadillac Championship) — What to look for:**\n\n'
            'The Blue Monster rewards long hitters who can handle firm, fast conditions and the famous water-lined 18th. '
            'A new Signature Event in 2026 — expect elite fields and scoring pressure from the start. '
            'Players comfortable in South Florida heat/humidity with strong par-5 scoring have a big edge.\n\n'
            '🏌️ Driving distance | 🎯 Par-5 scoring efficiency | 💧 Comfort on risk/reward water holes | '
            '🌡️ Experienced in warm, humid conditions | 🏆 Top-30 world ranking'
        ),
        'Truist': (
            '🎯 **Quail Hollow (Truist Championship) — What to look for:**\n\n'
            'Home of the infamous "Green Mile" (holes 16–18), one of the hardest closing stretches in golf. '
            'Long, tree-lined track that demands both power and precision. Par-3 17th over water is pivotal. '
            'Players must be long AND accurate — no shortcuts here.\n\n'
            '🏌️ Driving distance + accuracy combo | 🎯 Elite iron play | 💪 Green Mile toughness | '
            '🏆 Strong Quail Hollow history | Top-20 world-ranked players dominate here'
        ),
        'Travelers': (
            '🎯 **TPC River Highlands (Travelers Championship) — What to look for:**\n\n'
            'A scoring fest — one of the lowest-scoring events of the year. Relatively open layout rewards bombers '
            'who can also putt. Birdie rate is the single best predictor of success here. '
            'Look for players coming in with hot recent form and a hot putter.\n\n'
            '🏌️ Driving distance | 🐦 Elite birdie rate | 🏌️ Hot putting form | '
            '📈 Players on recent winning streaks | 💰 Good value week for high-upside picks'
        ),
        'Memorial': (
            '🎯 **Muirfield Village (Memorial Tournament) — What to look for:**\n\n'
            'Jack Nicklaus\'s demanding design celebrates its 50th anniversary in 2026. Positioning off the tee '
            'matters more than distance — narrow fairways and deep rough punish inaccuracy. '
            'Bentgrass greens reward elite putters. This event reliably crowns the best player that week.\n\n'
            '🎯 Driving accuracy + positioning | 🏌️ Elite iron play to protected greens | '
            '⛳ Strong putting on bentgrass | 🏆 Top-20 world ranking almost always wins here | '
            'Course history is a strong predictor'
        ),
        # ── MAJORS ────────────────────────────────────────────────────────────
        'Masters': (
            '🎯 **Augusta National (The Masters) — What to look for:**\n\n'
            'Augusta rewards right-to-left ball flight, long hitters who can reach all four par-5s in two, '
            'and elite putters on the fastest bentgrass in the world. Familiarity is critical — '
            'players with multiple top-10s here have a massive edge over first-timers.\n\n'
            '🏌️ Distance + draw ball flight | 🎯 Elite iron play to large sloped greens | '
            '⛳ Superior putting on ultra-fast bentgrass | 🏆 Par-5 birdie efficiency | '
            'Multiple prior Augusta top-10s — this course rewards experience above almost all else'
        ),
        'PGA Championship': (
            '🎯 **Aronimink GC (PGA Championship 2026) — What to look for:**\n\n'
            'A classic Donald Ross design making its first major appearance. Ross courses reward precise iron play '
            'into crowned, runoff greens — missing the green in the wrong spot leads to bogeys. '
            'Scrambling and creativity around the greens will be at a premium. '
            'Expect scoring to be tougher than typical modern majors.\n\n'
            '🎯 Precise iron play to crowned greens | ✂️ Elite scrambling | '
            '🏌️ Controlled ball flight (not just pure distance) | '
            '🏆 Players who have excelled at classic/traditional parkland setups | '
            'Adaptability to an unfamiliar course — prior Ross design experience helps'
        ),
        'U.S. Open': (
            '🎯 **U.S. Open — What to look for:**\n\n'
            'USGA setup: thick rough, firm fast greens, narrow fairways. Par is the goal — '
            'avoiding bogeys matters more than making birdies. Mental toughness and patience under extreme difficulty '
            'are the #1 predictors. Bombers who can also find fairways have an advantage in the rough.\n\n'
            '🎯 Driving accuracy under pressure | 🏌️ Iron play from thick rough | '
            '⛳ Exceptional putting on firm, fast greens | 💪 Mental toughness / patience | '
            '🏆 Prior major experience and top-20 world ranking — U.S. Opens rarely produce surprise winners'
        ),
        'The Open': (
            '🎯 **The Open Championship — What to look for:**\n\n'
            'Links golf demands creativity, wind management, and ground game skills most tour players rarely use. '
            'Running shots into greens, bump-and-runs, and managing pot bunkers are essential. '
            'Distance matters less than adaptability. '
            'Players with links experience (European Tour, Scottish/Irish Open) have a huge edge.\n\n'
            '🌬️ Wind management (top priority) | 🏌️ Creative low ball flight | '
            '✂️ Ground game & links-style short game | '
            '🏆 Strong European Tour / links course history | '
            'Avoid one-trick bombers with no links experience'
        ),
        # ── THE PLAYERS ───────────────────────────────────────────────────────
        'Players': (
            '🎯 **TPC Sawgrass (The Players Championship) — What to look for:**\n\n'
            'The "fifth major" demands accuracy above all. Island green 17th is the most famous hole in golf and '
            'can end a tournament in one swing. Small, firm greens require precise iron play — '
            'bombers who spray it get eaten alive by water and OB.\n\n'
            '🎯 Driving accuracy (critical) | 🏌️ Elite iron play to small greens | '
            '💪 Mental steadiness on 17 | ⛳ Solid putting on Bermuda | '
            '🏆 Multiple prior Players starts — water avoidance improves with experience here'
        ),
        # ── REGULAR EVENTS ────────────────────────────────────────────────────
        'Phoenix': (
            '🎯 **TPC Scottsdale (WM Phoenix Open) — What to look for:**\n\n'
            'One of the lowest-scoring events of the year. Par-5 dominance is king — players who birdie '
            'all four par-5s consistently are in great shape. Stadium atmosphere on 16 rewards fearless players. '
            'Look for players ranked near the top in birdie average.\n\n'
            '🏌️ Driving distance for par-5 access | 🐦 Elite birdie rate | '
            '⛳ Hot putter | 📈 Recent scoring momentum | '
            'Prior TPC Scottsdale performance is highly predictive'
        ),
        'Cognizant': (
            '🎯 **PGA National (Cognizant Classic) — What to look for:**\n\n'
            '"The Bear Trap" (holes 15–17) decides more tournaments than any other stretch on tour. '
            'Accuracy off the tee trumps distance. Wind off the Florida water is a constant factor. '
            'Look for grinders who make pars under pressure and elite putters.\n\n'
            '🎯 Driving accuracy | ⛳ Elite putting under pressure | '
            '✂️ Scrambling ability | 🌊 Wind management | '
            '💪 Mental toughness on The Bear Trap finishing holes'
        ),
        'Valspar': (
            '🎯 **Innisbrook — Copperhead (Valspar Championship) — What to look for:**\n\n'
            'Some of the toughest rough conditions on tour. Miss the fairway and you\'re grinding for bogey. '
            'Driving accuracy is the single most important stat here. GIR% and scrambling follow closely. '
            'Mid-ranked accurate players routinely outperform big-name bombers.\n\n'
            '🎯 Driving accuracy (top priority) | 🏌️ GIR% from tight lies | '
            '✂️ Scrambling from deep rough | '
            'Fade distance-only players | 🏆 Value picks — upsets are common here'
        ),
        'Houston': (
            '🎯 **Memorial Park (Texas Children\'s Houston Open) — What to look for:**\n\n'
            'Memorial Park was redesigned by Tom Doak and rewards precision over power. '
            'The Bermuda rough can be punishing, and approach play to firm greens is critical. '
            'A good tune-up week before the Masters — look for Augusta-style players (ball strikers, good putters).\n\n'
            '🎯 Precision iron play | ⛳ Putting on Bermuda | '
            '🏌️ Controlled ball flight | 🏆 Players peaking heading into Masters prep | '
            'Good week to target world top-50 players who skip this to rest'
        ),
        'Valero': (
            '🎯 **TPC San Antonio — AT&T Oaks (Valero Texas Open) — What to look for:**\n\n'
            'Final warm-up before the Masters draws a motivated field — players who need a win to get into Augusta '
            'are playing for their season. Bermuda rough, warm weather, and a long layout favor bombers '
            'who can also putt on grainy greens. Motivation factor is huge here.\n\n'
            '🏌️ Driving distance | ⛳ Putting on Bermuda greens | '
            '💪 High-motivation players chasing Masters spots | '
            '🎯 Solid all-around game | Watch for hungry bubble players'
        ),
        'Zurich': (
            '🎯 **TPC Louisiana (Zurich Classic — Team Event) — What to look for:**\n\n'
            'Unique two-man team format (foursomes & fourball) changes everything. '
            'Complementary pairings are more important than individual rankings. '
            'Look for teams where one player is an aggressive birdie-hunter and the other is a consistent ball-striker. '
            'Scrambling teams with elite putters dominate fourball format.\n\n'
            '👥 Team chemistry and complementary styles | 🐦 Birdie-hunting in fourball | '
            '🎯 Accuracy and consistency in foursomes | '
            '⛳ Elite putting | Past Zurich team performance is the best predictor'
        ),
        'Byron Nelson': (
            '🎯 **TPC Craig Ranch (CJ Cup Byron Nelson) — What to look for:**\n\n'
            'One of the most birdie-friendly courses on tour. Long but wide open — bombers thrive. '
            'Scoring in the 20s-under is common. Hot putters and aggressive players who go for flags do best. '
            'Field is typically weakened by European Tour conflicts — value picks abound.\n\n'
            '🏌️ Driving distance | 🐦 Birdie rate | '
            '⛳ Hot putter | 📈 Recent low-scoring form | '
            '💰 Great week for mid-ranked value picks with strong distance stats'
        ),
        'Schwab': (
            '🎯 **Colonial CC (Charles Schwab Challenge) — What to look for:**\n\n'
            '"Hogan\'s Alley" demands relentless precision. One of the tightest driving corridors on tour — '
            'Colonial punishes wild drivers harshly. Short but demanding, with small bentgrass greens '
            'that require soft, precise iron shots. Accuracy players dominate every year.\n\n'
            '🎯 Driving accuracy (critical) | 🏌️ Precise iron play to small greens | '
            '⛳ Putting on bentgrass | '
            'Fade long/wild hitters completely | 🏆 Strong Colonial history — Hogan\'s Alley favors familiarity'
        ),
        'Canadian Open': (
            '🎯 **TPC Toronto at Osprey Valley (RBC Canadian Open) — What to look for:**\n\n'
            'A relatively new venue on tour. The North Course is a classic parkland layout where '
            'driving accuracy and iron play are both important. Canadian weather (wind, potential rain) '
            'can affect scoring. Look for all-around ball strikers with experience in variable conditions.\n\n'
            '🎯 Driving accuracy | 🏌️ Consistent iron play | '
            '🌬️ Wind/weather management | '
            '⛳ Solid putting | All-around players over one-dimensional specialists'
        ),
        'Puntacana': (
            '🎯 **Corales GC (Corales Puntacana Championship) — What to look for:**\n\n'
            'Opposite-field event played the same week as a Signature Event — the field is weaker. '
            'Corales is a stunning cliff-top course with ocean wind as a constant factor. '
            'Distance helps on wide oceanside holes, but wind management is crucial. '
            'Great week to target value picks not playing the marquee event.\n\n'
            '🌬️ Wind management | 🏌️ Driving distance on wide holes | '
            '⛳ Solid putting | 💰 Prime value pick week | '
            'Players who chose this over larger event are usually motivated to compete'
        ),
        '3M Open': (
            '🎯 **TPC Twin Cities (3M Open) — What to look for:**\n\n'
            'A bomber\'s paradise. Wide fairways and reachable par-5s make this one of the highest-scoring '
            'events of the summer. Winning scores can reach -25 or lower. '
            'Distance off the tee is the single best predictor — elite putters who can also bomb it thrive.\n\n'
            '🏌️ Driving distance (top priority) | 🐦 Par-5 birdie efficiency | '
            '⛳ Hot putter | 📈 Players in peak summer form | '
            '💰 Good week to target long-hitting value players'
        ),
        'Rocket': (
            '🎯 **Detroit Golf Club (Rocket Classic) — What to look for:**\n\n'
            'A classic parkland course with tree-lined fairways that demand accuracy. '
            'Low scoring is typical, but unlike TPC Twin Cities, precision matters more than pure length. '
            'GIR% and approach play are top predictors. Hot putters in warm summer conditions do well.\n\n'
            '🎯 Driving accuracy | 🏌️ GIR% & approach play | '
            '⛳ Putting in warm conditions | '
            '📈 Players with strong summer form | '
            'All-around ball strikers over pure bombers'
        ),
        'Wyndham': (
            '🎯 **Sedgefield CC (Wyndham Championship) — What to look for:**\n\n'
            'Final event before FedEx Cup Playoffs — bubble players are incredibly motivated. '
            'Classic, shorter parkland where accurate shorter hitters can absolutely compete with bombers. '
            'One of the few events where putting and accuracy alone can win.\n\n'
            '🎯 Driving accuracy | ⛳ Elite putting | '
            '✂️ Scrambling from short rough | '
            '💪 High-motivation bubble players fighting for playoff spots | '
            'Check FedEx Cup standings — position 70-125 players are playing for their season'
        ),
        # ── FEDEX CUP PLAYOFFS ────────────────────────────────────────────────
        'St. Jude': (
            '🎯 **TPC Southwind (FedEx St. Jude Championship) — What to look for:**\n\n'
            'First FedEx Playoff event — Bermuda rough and tight Bermuda fairways in Memphis heat. '
            'TPC Southwind is a grinder\'s course that rewards accuracy over distance. '
            'Players who have struggled with Bermuda grass all season are a fade. '
            'Playoff pressure separates the mentally strong from the rest.\n\n'
            '🎯 Driving accuracy on Bermuda | 🏌️ Iron play to fast greens | '
            '⛳ Putting on Bermuda | 💪 Playoff experience & mental fortitude | '
            'Eliminate players with poor Bermuda track records'
        ),
        'BMW Championship': (
            '🎯 **Bellerive CC (BMW Championship) — What to look for:**\n\n'
            'Second FedEx Playoff event — only top 50 in FedEx points remain. '
            'Bellerive is a long, demanding layout where the best players in the world rise to the top. '
            'No significant course-specific biases — just pick the elite players in the hottest form. '
            'Momentum from St. Jude carries over heavily.\n\n'
            '🏆 World ranking & FedEx standing | 📈 Recent form / momentum | '
            '🏌️ Long game under pressure | '
            '💪 Playoff experience | At this point just pick Scheffler and the next hottest player'
        ),
        'Tour Championship': (
            '🎯 **East Lake GC (Tour Championship) — What to look for:**\n\n'
            'Only the top 30 in FedEx Cup compete with a staggered starting score format — '
            'the FedEx leader starts at -10, creating a realistic chance for anyone in the top 10. '
            'East Lake rewards all-around excellence. The stagger means the #1 seed has a massive advantage.\n\n'
            '🏆 FedEx Cup standing (the stagger is everything) | '
            '📈 Momentum through the playoffs | '
            '🏌️ Elite all-around game | ⛳ Clutch putting in pressure situations | '
            'Target the top-3 FedEx seeds — they win ~60% of the time'
        ),
        # ── FALL EVENTS ───────────────────────────────────────────────────────
        'Sanderson': (
            '🎯 **Country Club of Jackson (Sanderson Farms Championship) — What to look for:**\n\n'
            'Fall FedEx season opener. Softer field of players rebuilding points. '
            'Traditional parkland layout rewards accurate iron play and putting. '
            'Great week to target young players and recent Korn Ferry graduates hungry to prove themselves.\n\n'
            '🎯 Iron play & accuracy | ⛳ Putting | '
            '🌱 Young/hungry players on the rise | '
            '💰 Excellent value pick week — field is weak and motivated mid-tier players can win'
        ),
        'Shriners': (
            '🎯 **TPC Summerlin (Shriners Children\'s Open) — What to look for:**\n\n'
            'One of the lowest-scoring events of the entire year. Wide-open desert layout with '
            'reachable par-5s and very little rough. Scoring regularly reaches -25 or lower. '
            'Elite distance + elite putting = winner. Scrambling matters very little here.\n\n'
            '🏌️ Driving distance | 🐦 Birdie rate | ⛳ Elite putter | '
            '📈 Players with hot scoring form | '
            'Fade all accuracy-first players — this course rewards aggressive attack'
        ),
        'Zozo': (
            '🎯 **Accordia Golf Narashino CC (ZOZO Championship) — What to look for:**\n\n'
            'Played in Japan — flat, parkland layout where ball striking and iron play are paramount. '
            'Jet lag and travel are real factors; favor players with Japan experience or who arrived early. '
            'Low scoring typical. Historical winners have been elite world-ranked players.\n\n'
            '✈️ Travel/jet lag management | 🎯 Consistent iron play | '
            '⛳ Putting on Bermuda | '
            '🏆 Top-20 world ranking | Prior Japan tournament experience a plus'
        ),
        'Bermuda': (
            '🎯 **Port Royal GC (Butterfield Bermuda Championship) — What to look for:**\n\n'
            'Opposite-field event on a unique island course. Ocean wind is the defining factor — '
            'creative wind management separates contenders. Soft field with motivated players '
            'who didn\'t qualify for elite events.\n\n'
            '🌬️ Wind management (critical) | 🎯 Accuracy in gusty conditions | '
            '💰 Strong value pick week | '
            'Players with links/coastal experience | Look for motivated mid-tier players'
        ),
        'World Wide Technology': (
            '🎯 **El Cardonal at Diamante (World Wide Technology Championship) — What to look for:**\n\n'
            'Stunning Pacific coast course in Cabo San Lucas. Tiger Woods design with wide corridors '
            'but demanding approach angles into greens. Ocean wind is always a factor. '
            'Low scoring typical in the warm Mexican climate.\n\n'
            '🏌️ Driving distance on wide corridors | 🎯 Approach play to elevated/sloped greens | '
            '🌬️ Wind management | ⛳ Putting | '
            '📈 Recent form — players coming in hot dominate here'
        ),
        'Myrtle Beach': (
            '🎯 **Dunes Golf and Beach Club (ONEflight Myrtle Beach Classic) — What to look for:**\n\n'
            'Classic coastal layout where wind off the Atlantic creates variable conditions. '
            'Opposite-field event allows for great value picks. Dunes rewards all-around play '
            'with a premium on accuracy into small greens. Motivated mid-tier players often excel.\n\n'
            '🌬️ Wind management | 🎯 Accuracy into small greens | '
            '⛳ Putting | 💰 Strong value pick week | '
            'Players not competing in the concurrent Truist Championship'
        ),
    }
    insight = next((v for k, v in course_insights.items() if k.lower() in tournament_name.lower()), None)
    if insight:
        st.info(insight)

    # Display player grid
    st.subheader("Tournament Field")
    st.caption("💡 To make your pick: expand a player card below and click ✅ Select Player")
    
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
            perf_conn = sqlite3.connect(str(st.session_state.db_manager.db_path))
            perf_cursor = perf_conn.cursor()
            perf_cursor.execute(
                "SELECT scoring_avg, driving_distance, driving_accuracy, gir_pct, putts_per_hole, birdies_per_round, scoring_avg_rank, driving_distance_rank, driving_accuracy_rank, gir_pct_rank, putts_per_hole_rank, birdies_per_round_rank, composite_score FROM player_performance_stats WHERE player_name = ?",
                (perf_name,)
            )
            perf_row = perf_cursor.fetchone()
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
        except Exception as e:
            st.warning(f"Perf stats error: {e}")

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
