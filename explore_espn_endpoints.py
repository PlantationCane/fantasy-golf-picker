"""
Explore ESPN's Golf API endpoints to find rankings and statistics
Run this on your machine to discover what endpoints are available
"""
import requests
import json

def test_endpoint(url, description):
    """Test an endpoint and show what it returns"""
    print(f"\n📍 {description}")
    print(f"   URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ SUCCESS!")
            print(f"   Top-level keys: {list(data.keys())}")
            
            # Look for interesting data
            if 'leaders' in data:
                print(f"   📊 Has 'leaders' - {len(data['leaders'])} items")
            if 'statistics' in data:
                print(f"   📊 Has 'statistics' - {len(data['statistics'])} items")
            if 'standings' in data:
                print(f"   📊 Has 'standings'")
            if 'rankings' in data:
                print(f"   📊 Has 'rankings'")
            if 'events' in data:
                print(f"   📊 Has 'events' - {len(data['events'])} events")
                if len(data['events']) > 0:
                    event = data['events'][0]
                    print(f"      Event: {event.get('name')}")
                    print(f"      Event ID: {event.get('id')}")
                    
                    # Check competitions
                    if 'competitions' in event:
                        comp = event['competitions'][0]
                        if 'competitors' in comp and len(comp['competitors']) > 0:
                            first = comp['competitors'][0]
                            print(f"      First competitor keys: {list(first.keys())}")
            
            # Save full response for inspection
            filename = url.split('/')[-1].split('?')[0] + '_response.json'
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"   💾 Saved full response to: {filename}")
            
            return True
        else:
            print(f"   ❌ HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("="*70)
    print("🔍 ESPN GOLF API ENDPOINT EXPLORER")
    print("="*70)
    
    base_url = "https://site.api.espn.com/apis/site/v2/sports/golf/pga"
    test_date = "20260130"  # Farmers Insurance Open
    
    # 1. Get event ID from scoreboard
    print("\n" + "="*70)
    print("STEP 1: Get Event ID from Scoreboard")
    print("="*70)
    
    scoreboard_url = f"{base_url}/scoreboard?dates={test_date}"
    test_endpoint(scoreboard_url, "Scoreboard (leaderboard)")
    
    try:
        response = requests.get(scoreboard_url)
        data = response.json()
        event_id = data['events'][0]['id']
        event_name = data['events'][0]['name']
        
        print(f"\n✅ Found event: {event_name} (ID: {event_id})")
        
        # 2. Try event-specific endpoints
        print("\n" + "="*70)
        print("STEP 2: Try Event-Specific Endpoints")
        print("="*70)
        
        event_endpoints = [
            (f"{base_url}/summary?event={event_id}", "Event Summary"),
            (f"{base_url}/leaderboard?event={event_id}", "Leaderboard"),
            (f"{base_url}/statistics?event={event_id}", "Statistics"),
            (f"{base_url}/rankings?event={event_id}", "Rankings"),
            (f"{base_url}/leaders?event={event_id}", "Leaders"),
        ]
        
        for url, desc in event_endpoints:
            test_endpoint(url, desc)
        
        # 3. Try season-wide endpoints
        print("\n" + "="*70)
        print("STEP 3: Try Season-Wide Endpoints")
        print("="*70)
        
        season_endpoints = [
            (f"{base_url}/standings", "Season Standings"),
            (f"{base_url}/rankings", "Season Rankings"),
            (f"{base_url}/leaders", "Season Leaders"),
            (f"{base_url}/statistics", "Season Statistics"),
        ]
        
        for url, desc in season_endpoints:
            test_endpoint(url, desc)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("\n" + "="*70)
    print("✅ EXPLORATION COMPLETE!")
    print("="*70)
    print("\nCheck the *_response.json files to see what data is available")
    print("Look for 'earnings', 'fedexPoints', 'money', 'points', etc.")

if __name__ == "__main__":
    main()
