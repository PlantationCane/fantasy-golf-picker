"""
Diagnostic script to check what data the app sees
"""
import sqlite3

db_path = "pga_fantasy.db"

print("="*60)
print("DIAGNOSTIC: PLAYER STATS CHECK")
print("="*60)

with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()
    
    # Check player_stats table
    print("\n1. Player Stats Table (first 10 rows):")
    cursor.execute("""
        SELECT player_name, fedex_rank, season_money 
        FROM player_stats 
        WHERE player_name IS NOT NULL AND player_name != ''
        ORDER BY CAST(fedex_rank AS INTEGER)
        LIMIT 10
    """)
    
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"   {i}. {row[0]}: Rank {row[1]}, ${row[2]:,.0f}" if row[2] else f"   {i}. {row[0]}: Rank {row[1]}, $0")
    
    # Check Riviera course history
    print("\n2. Riviera Course History (sample):")
    cursor.execute("""
        SELECT player_name, COUNT(*) as rounds, AVG(score_to_par) as avg_score
        FROM course_history 
        WHERE course_name LIKE '%Riviera%'
        GROUP BY player_name
        ORDER BY rounds DESC
        LIMIT 10
    """)
    
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"   {i}. {row[0]}: {row[1]} rounds, Avg: {row[2]:.1f}")
    
    # Check your 4 picks
    print("\n3. Your 4 Picks in 2026:")
    picks = ['Chris Gotterup', 'Maverick McNealy', 'Patrick Rodgers', 'Sam Stevens']
    
    for pick in picks:
        cursor.execute("""
            SELECT player_name, COUNT(*) as events, 
                   AVG(CAST(finish_position AS INTEGER)) as avg_finish,
                   MIN(CAST(finish_position AS INTEGER)) as best_finish
            FROM tournament_results_2026
            WHERE player_name = ? 
                AND finish_position NOT IN ('MC', 'CUT', 'WD', 'DQ')
                AND CAST(finish_position AS INTEGER) > 0
        """, (pick,))
        
        result = cursor.fetchone()
        if result and result[1] and result[1] > 0:
            print(f"   {result[0]}: {result[1]} events, Best: {result[3]}, Avg: {result[2]:.1f}")
        else:
            print(f"   {pick}: No 2026 data")
    
    # Check total players available
    print("\n4. Database Counts:")
    cursor.execute("SELECT COUNT(DISTINCT player_name) FROM player_stats WHERE player_name IS NOT NULL")
    print(f"   Players in stats: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(DISTINCT player_name) FROM tournament_results_2026")
    print(f"   Players in 2026 results: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(DISTINCT player_name) FROM course_history WHERE course_name LIKE '%Riviera%'")
    print(f"   Players with Riviera history: {cursor.fetchone()[0]}")

print("\n" + "="*60)
