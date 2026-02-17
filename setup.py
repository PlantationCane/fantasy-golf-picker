"""
Setup script for PGA Fantasy Tracker

This script helps you:
1. Initialize the database
2. Add your existing picks from previous weeks
3. Verify the setup
"""

from utils.database import DatabaseManager
from datetime import datetime

def setup_database():
    """Initialize the database"""
    print("🔧 Initializing database...")
    db = DatabaseManager()
    print("✅ Database initialized successfully!")
    return db

def add_existing_picks(db):
    """Add picks from previous weeks"""
    print("\n📝 Let's add your existing picks from previous tournaments")
    print("=" * 60)
    
    existing_picks = []
    
    # Week 1 - Last Week
    print("\n--- WEEK 1 (Last Week) ---")
    for i in range(2):
        player = input(f"Enter player #{i+1} name (or press Enter to skip): ").strip()
        if player:
            tournament = input(f"Tournament name for {player}: ").strip()
            existing_picks.append({
                'player_name': player,
                'tournament_name': tournament or 'Week 1 Tournament',
                'tournament_date': '2026-01-30',  # Adjust as needed
                'week_used': '2026-W05'
            })
    
    # Week 2 - This Week  
    print("\n--- WEEK 2 (This Week) ---")
    for i in range(2):
        player = input(f"Enter player #{i+1} name (or press Enter to skip): ").strip()
        if player:
            tournament = input(f"Tournament name for {player}: ").strip()
            existing_picks.append({
                'player_name': player,
                'tournament_name': tournament or 'Week 2 Tournament',
                'tournament_date': '2026-02-06',  # Adjust as needed
                'week_used': '2026-W06'
            })
    
    if existing_picks:
        print(f"\n📊 Adding {len(existing_picks)} picks to database...")
        if db.add_historical_picks(existing_picks):
            print("✅ All picks added successfully!")
            
            # Display summary
            print("\n📋 Summary of your picks:")
            print("-" * 60)
            for pick in existing_picks:
                print(f"  • {pick['player_name']} - {pick['tournament_name']}")
        else:
            print("❌ Error adding picks. Please try again.")
    else:
        print("No picks to add.")
    
    return existing_picks

def verify_setup(db):
    """Verify the setup"""
    print("\n🔍 Verifying setup...")
    print("=" * 60)
    
    picks_count = db.get_picks_count()
    used_players = db.get_used_players()
    
    print(f"Total picks in database: {picks_count}")
    print(f"Players used: {len(used_players)}")
    
    if used_players:
        print("\nUsed players:")
        for player in used_players:
            week = db.get_player_used_week(player)
            print(f"  • {player} ({week})")
    
    print("\n✅ Setup verification complete!")

def main():
    print("=" * 60)
    print("🏌️ PGA FANTASY TRACKER - SETUP")
    print("=" * 60)
    
    # Initialize database
    db = setup_database()
    
    # Ask if they want to add existing picks
    print("\nHave you already made picks in previous weeks? (y/n): ", end="")
    add_picks = input().strip().lower()
    
    if add_picks == 'y':
        add_existing_picks(db)
    else:
        print("\n✅ No existing picks to add. Starting fresh!")
    
    # Verify
    verify_setup(db)
    
    print("\n" + "=" * 60)
    print("🎉 Setup complete! You're ready to use the app.")
    print("=" * 60)
    print("\nTo start the app, run:")
    print("  streamlit run app.py")
    print("\nThe app will open in your web browser automatically.")
    print("=" * 60)

if __name__ == "__main__":
    main()
