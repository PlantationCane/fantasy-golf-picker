"""
Quick script to add your weekly pick with player selection
"""
from utils.database import DatabaseManager
from datetime import datetime
import sqlite3
import requests

def get_next_tournament():
    """Try to fetch next tournament from ESPN"""
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/golf/pga/scoreboard"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        events = data.get('events', [])
        for event in events:
            status = event.get('status', {}).get('type', {}).get('name', '')
            if status in ['STATUS_SCHEDULED', 'STATUS_IN_PROGRESS']:
                name = event.get('name', '')
                date = event.get('date', '')
                if name and date:
                    # Parse date
                    try:
                        event_date = datetime.strptime(date[:10], '%Y-%m-%d')
                        return name, event_date.strftime('%Y-%m-%d')
                    except:
                        return name, datetime.now().strftime('%Y-%m-%d')
    except:
        pass
    
    return None, None

def get_available_players():
    """Get list of players with 2026 data"""
    db_path = "pga_fantasy.db"
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT player_name 
            FROM tournament_results_2026 
            ORDER BY player_name
        """)
        
        return [row[0] for row in cursor.fetchall()]

def get_used_players():
    """Get list of already used players"""
    db_path = "pga_fantasy.db"
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT player_name FROM used_players ORDER BY player_name")
        return [row[0] for row in cursor.fetchall()]

def select_player(players, used_players):
    """Let user select a player from numbered list"""
    print("=" * 60)
    print("SELECT PLAYER")
    print("=" * 60)
    
    # Filter out used players but show them greyed
    available = []
    
    print("\n📋 AVAILABLE PLAYERS:\n")
    
    idx = 1
    for player in players:
        if player not in used_players:
            print(f"  {idx:3d}. {player}")
            available.append((idx, player))
            idx += 1
    
    if used_players:
        print(f"\n⚠️  {len(used_players)} players already used (not shown)")
    
    print(f"\n{len(available)} players available")
    print("=" * 60)
    
    # Get selection
    while True:
        try:
            choice = input("\nEnter player number (or 's' to search, 'q' to quit): ").strip().lower()
            
            if choice == 'q':
                return None
            
            if choice == 's':
                return search_player(players, used_players)
            
            choice_num = int(choice)
            
            # Find the player
            for num, player_name in available:
                if num == choice_num:
                    return player_name
            
            print("❌ Invalid number. Try again.")
        except ValueError:
            print("❌ Please enter a number, 's' to search, or 'q' to quit")

def search_player(players, used_players):
    """Search for a player by name"""
    search_term = input("\nEnter player name (partial match OK): ").strip().lower()
    
    if not search_term:
        return None
    
    # Find matches
    matches = [p for p in players if search_term in p.lower()]
    
    if not matches:
        print(f"❌ No players found matching '{search_term}'")
        return None
    
    if len(matches) == 1:
        player = matches[0]
        if player in used_players:
            print(f"\n⚠️  {player} has already been used!")
            confirm = input("Add anyway? (y/N): ").strip().lower()
            if confirm != 'y':
                return None
        return player
    
    # Multiple matches
    print(f"\nFound {len(matches)} matches:")
    for i, player in enumerate(matches, 1):
        status = "❌ USED" if player in used_players else "✅"
        print(f"  {i}. {player} {status}")
    
    try:
        choice = int(input(f"\nSelect player (1-{len(matches)}): "))
        if 1 <= choice <= len(matches):
            player = matches[choice - 1]
            if player in used_players:
                print(f"\n⚠️  {player} has already been used!")
                confirm = input("Add anyway? (y/N): ").strip().lower()
                if confirm != 'y':
                    return None
            return player
    except ValueError:
        pass
    
    print("❌ Invalid selection")
    return None

def add_weekly_pick():
    db = DatabaseManager()
    
    print("\n" * 2)
    print("=" * 60)
    print("           ADD WEEKLY PICKS")
    print("=" * 60)
    
    # Get next tournament
    tournament_name, tournament_date = get_next_tournament()
    
    if tournament_name:
        print(f"\n📅 Next Tournament: {tournament_name}")
        print(f"   Date: {tournament_date}")
        
        use_this = input("\nUse this tournament? (Y/n): ").strip().lower()
        if use_this == 'n':
            tournament_name = input("Enter tournament name: ").strip()
            tournament_date = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
            if not tournament_date:
                tournament_date = datetime.now().strftime("%Y-%m-%d")
    else:
        print("\n⚠️  Could not auto-detect next tournament")
        tournament_name = input("Enter tournament name: ").strip()
        tournament_date = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
        if not tournament_date:
            tournament_date = datetime.now().strftime("%Y-%m-%d")
    
    if not tournament_name:
        print("❌ Tournament name required")
        return
    
    # Track picks made this session
    picks_this_session = []
    
    # Loop to allow multiple picks
    while True:
        # Get players
        print("\n📊 Loading players from database...")
        all_players = get_available_players()
        used_players = get_used_players()
        
        if not all_players:
            print("❌ No players found in database. Run tournament update first.")
            return
        
        print(f"   Found {len(all_players)} total players")
        print(f"   {len(used_players)} already used")
        print(f"   {len(all_players) - len(used_players)} available")
        
        if picks_this_session:
            print(f"\n✅ Picks this session: {len(picks_this_session)}")
            for p in picks_this_session:
                print(f"   • {p}")
        
        # Select player
        player_name = select_player(all_players, used_players)
        
        if not player_name:
            print("\n❌ Cancelled")
            break
        
        # Confirm
        print("\n" + "=" * 60)
        print("CONFIRM PICK")
        print("=" * 60)
        print(f"Player:     {player_name}")
        print(f"Tournament: {tournament_name}")
        print(f"Date:       {tournament_date}")
        print("=" * 60)
        
        confirm = input("\nAdd this pick? (Y/n): ").strip().lower()
        if confirm == 'n':
            print("❌ Skipped")
            continue
        
        # Add the pick
        success = db.add_pick(player_name, tournament_name, tournament_date)
        
        if success:
            print(f"\n✅ SUCCESS! {player_name} added for {tournament_name}")
            picks_this_session.append(player_name)
            
            # Show current picks count
            count = db.get_picks_count()
            print(f"\n📊 Total picks used: {count}/200")
            print(f"   Picks remaining: {200 - count}")
        else:
            print(f"\n❌ ERROR: Could not add pick (player may already be used)")
        
        # Ask if they want to add another
        print("\n" + "=" * 60)
        add_another = input("Add another pick for this tournament? (Y/n): ").strip().lower()
        
        if add_another == 'n':
            break
    
    # Summary
    if picks_this_session:
        print("\n" + "=" * 60)
        print(f"✅ SESSION COMPLETE - Added {len(picks_this_session)} pick(s):")
        print("=" * 60)
        for i, player in enumerate(picks_this_session, 1):
            print(f"  {i}. {player}")
        print("=" * 60)

if __name__ == "__main__":
    try:
        add_weekly_pick()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
    
    input("\nPress Enter to exit...")
