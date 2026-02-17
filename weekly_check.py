"""
Weekly tournament update reminder
Run this script on Mondays to check for tournaments to update
"""
from datetime import datetime, timedelta
import sqlite3

def check_weekly_update():
    print("=" * 60)
    print("📅 WEEKLY TOURNAMENT UPDATE CHECK")
    print("=" * 60)
    print(f"Today: {datetime.now().strftime('%A, %B %d, %Y')}\n")
    
    # Check last tournament update
    db_path = "pga_fantasy.db"
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Get most recent tournament in database
        cursor.execute("""
            SELECT tournament_name, tournament_date, COUNT(*) as players
            FROM tournament_results_2026
            GROUP BY tournament_name, tournament_date
            ORDER BY tournament_date DESC
            LIMIT 1
        """)
        
        last_tournament = cursor.fetchone()
        
        if last_tournament:
            name, date, player_count = last_tournament
            print(f"✅ Last updated tournament:")
            print(f"   {name}")
            print(f"   Date: {date}")
            print(f"   Players: {player_count}\n")
            
            # Check if it's been more than 7 days
            last_date = datetime.strptime(date, "%Y-%m-%d")
            days_ago = (datetime.now() - last_date).days
            
            if days_ago > 7:
                print(f"⚠️  WARNING: Last update was {days_ago} days ago!")
                print(f"   Tournament results may be missing.\n")
            else:
                print(f"   Updated {days_ago} days ago\n")
        
        # Get total picks
        cursor.execute("SELECT COUNT(*) FROM picks")
        picks_count = cursor.fetchone()[0]
        
        print(f"📊 Season Status:")
        print(f"   Picks used: {picks_count}/200")
        print(f"   Picks remaining: {200 - picks_count}\n")
    
    print("=" * 60)
    print("🔄 TO UPDATE:")
    print("   python scrape_espn_json_api.py")
    print("\n📝 TO ADD PICK:")
    print("   python add_pick.py")
    print("=" * 60)

if __name__ == "__main__":
    check_weekly_update()
