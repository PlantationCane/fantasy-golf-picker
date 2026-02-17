"""
View your season picks history
"""
import sqlite3
import pandas as pd

def view_picks_history():
    print("=" * 60)
    print("📋 YOUR 2026 PICKS HISTORY")
    print("=" * 60)
    
    db_path = "pga_fantasy.db"
    
    with sqlite3.connect(db_path) as conn:
        # Get all picks with results
        query = """
            SELECT 
                p.player_name as 'Player',
                p.tournament_name as 'Tournament',
                p.tournament_date as 'Date',
                t.finish_position as 'Finish',
                t.earnings as 'Earnings',
                t.fedex_points as 'FedEx Pts'
            FROM picks p
            LEFT JOIN tournament_results_2026 t 
                ON p.player_name = t.player_name 
                AND p.tournament_name = t.tournament_name
            ORDER BY p.tournament_date DESC
        """
        
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            print("No picks recorded yet.\n")
            print("Add your first pick with: python add_pick.py")
        else:
            print(f"\n{len(df)} picks used:\n")
            print(df.to_string(index=False))
            
            # Calculate totals
            total_earnings = df['Earnings'].sum()
            total_fedex = df['FedEx Pts'].sum()
            
            print("\n" + "=" * 60)
            print(f"💰 Total Earnings: ${total_earnings:,.0f}" if total_earnings else "💰 Total Earnings: $0")
            print(f"🏆 Total FedEx Points: {total_fedex:.0f}" if total_fedex else "🏆 Total FedEx Points: 0")
            print(f"📊 Picks Remaining: {200 - len(df)}")
            print("=" * 60)

if __name__ == "__main__":
    view_picks_history()
