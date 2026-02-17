# 📊 Data Integration Guide

This guide explains how to integrate real PGA Tour data into your app.

## Current Status

The app is built with **placeholder data** that demonstrates all functionality. To get real-time data, you'll need to integrate with actual data sources.

## Data Source Options

### Option 1: PGA Tour Website (Free)

**Pros:**
- Free
- Official data
- Comprehensive stats

**Cons:**
- Requires web scraping
- Rate limiting needed
- HTML structure may change

**Implementation Steps:**

1. **Identify the URLs:**
   - Tournament schedule: `https://www.pgatour.com/schedule`
   - Leaderboards: `https://www.pgatour.com/leaderboard`
   - Player stats: `https://www.pgatour.com/players/player.{player_id}.html`
   - Strokes gained: `https://www.pgatour.com/stats/stat.{stat_code}.html`

2. **Update `data_fetcher.py`:**

```python
def get_tournament_field(self, tournament_id):
    """Scrape current tournament field"""
    url = f"{self.base_url}/tournaments/{tournament_id}/field"
    response = self.session.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Parse player list
    players = []
    for player_row in soup.select('.player-row'):  # Adjust selector
        name = player_row.select_one('.player-name').text.strip()
        player_id = player_row.get('data-player-id')
        
        players.append({
            'player_name': name,
            'player_id': player_id
        })
    
    return pd.DataFrame(players)
```

3. **Rate Limiting:**
```python
import time

def _fetch_with_delay(self, url):
    """Fetch URL with rate limiting"""
    time.sleep(2)  # 2 second delay between requests
    return self.session.get(url)
```

### Option 2: Data Golf API (Recommended - $10-30/month)

**Pros:**
- Best win probability predictions
- Clean API interface
- No scraping needed
- Advanced analytics

**Cons:**
- Costs money
- Requires API key management

**Setup:**

1. **Sign up:** https://datagolf.com/api-access

2. **Add API key to config.py:**
```python
USE_DATAGOLF_API = True
DATAGOLF_API_KEY = 'your_api_key_here'
```

3. **Update `data_fetcher.py`:**
```python
def get_tournament_predictions(self, tournament_id):
    """Get predictions from Data Golf"""
    if not config.USE_DATAGOLF_API:
        return None
    
    url = "https://feeds.datagolf.com/preds/pre-tournament"
    params = {
        'tour': 'pga',
        'key': config.DATAGOLF_API_KEY,
        'file_format': 'json'
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    
    return None
```

### Option 3: SportsDataIO API (Professional - $$)

**Pros:**
- Enterprise-grade
- Real-time updates
- Historical data warehouse

**Cons:**
- Expensive
- Overkill for personal use

## Specific Data Needs

### 1. Tournament Schedule & Field

**What you need:**
- Current/upcoming tournament name
- Tournament dates
- Course name
- Purse amount
- Field list (players entered)

**PGA Tour URL:**
```
https://www.pgatour.com/tournaments/schedule.html
```

**Scraping approach:**
```python
def get_current_tournament(self):
    response = self.session.get(f"{self.base_url}/tournaments/schedule.html")
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find "THIS WEEK" section
    current = soup.find('div', class_='this-week-tournament')
    
    return {
        'name': current.find('h3').text.strip(),
        'dates': current.find('span', class_='dates').text.strip(),
        'course': current.find('span', class_='course').text.strip()
    }
```

### 2. Player Statistics

**What you need:**
- FedEx Cup rank
- World Golf Ranking
- Season earnings
- Strokes gained (all categories)
- Recent tournament results

**PGA Tour URLs:**
```
Stats: https://www.pgatour.com/stats/stat.{code}.html
Player: https://www.pgatour.com/players/player.{id}.html

Stat Codes:
- 02671: FedEx Cup
- 02675: SG: Total
- 02567: SG: Off-the-Tee
- 02568: SG: Approach
- 02569: SG: Around Green
- 02564: SG: Putting
```

### 3. Course History

**What you need:**
- Player's finish at this course (last 3-5 years)
- Scoring relative to field
- Make/miss cut history

**Data Golf endpoint (if using):**
```python
url = "https://feeds.datagolf.com/historical-raw-data/rounds"
params = {
    'tour': 'pga',
    'event_id': event_id,
    'year': year,
    'key': API_KEY
}
```

### 4. Recent Form

**What you need:**
- Last 5 tournament results
- Finish positions
- Scoring averages

**Can calculate from tournament results table**

## Implementation Priority

### Phase 1: Essential (Do First)
1. ✅ Current tournament name & dates
2. ✅ Tournament field (player list)
3. ✅ FedEx Cup standings
4. ✅ Season money leaders

### Phase 2: Advanced Analytics
5. ✅ Strokes gained stats
6. ✅ World Golf Rankings
7. ✅ Recent form calculation

### Phase 3: Predictive
8. ✅ Course history
9. ✅ Win probability (if using Data Golf)
10. ✅ Value score calculations

## Sample Implementation

Here's a complete example of scraping FedEx Cup standings:

```python
def get_fedex_cup_standings(self):
    """Scrape current FedEx Cup standings"""
    url = f"{self.base_url}/stats/stat.02671.html"
    
    try:
        response = self.session.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        standings = []
        
        # Find the stats table
        table = soup.find('table', class_='table-stats')
        if not table:
            return pd.DataFrame()
        
        rows = table.find_all('tr')[1:]  # Skip header
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 4:
                continue
            
            rank = cols[0].text.strip()
            player_link = cols[1].find('a')
            player_name = player_link.text.strip() if player_link else ''
            player_id = player_link.get('href', '').split('.')[-2] if player_link else ''
            points = cols[2].text.strip().replace(',', '')
            
            standings.append({
                'rank': int(rank) if rank.isdigit() else None,
                'player_name': player_name,
                'player_id': player_id,
                'points': float(points) if points else 0
            })
        
        return pd.DataFrame(standings)
        
    except Exception as e:
        print(f"Error fetching FedEx standings: {e}")
        return pd.DataFrame()
```

## Testing Your Integration

1. **Start small:**
   - Test with one data source
   - Verify data format
   - Check for errors

2. **Use caching:**
   - Cache responses to avoid repeated requests
   - Use database cache table
   - Set reasonable expiration times

3. **Handle errors gracefully:**
   - Always have fallback data
   - Show user-friendly error messages
   - Log errors for debugging

4. **Test command:**
```bash
python
>>> from utils.data_fetcher import PGADataFetcher
>>> fetcher = PGADataFetcher()
>>> standings = fetcher.get_fedex_cup_standings()
>>> print(standings.head())
```

## Rate Limiting Best Practices

```python
import time
from functools import wraps

def rate_limit(seconds=2):
    """Decorator to rate limit function calls"""
    def decorator(func):
        last_called = [0.0]
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            if elapsed < seconds:
                time.sleep(seconds - elapsed)
            
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        
        return wrapper
    return decorator

# Usage
@rate_limit(seconds=2)
def fetch_url(url):
    return requests.get(url)
```

## Automatic Updates

To enable weekly data refresh:

1. **Update config.py:**
```python
AUTO_REFRESH_ENABLED = True
REFRESH_DAY = 'Monday'
REFRESH_TIME = '06:00'
```

2. **Add scheduler to app.py:**
```python
import schedule

def refresh_job():
    """Background job to refresh data"""
    fetcher = PGADataFetcher()
    fetcher.refresh_data()
    print(f"Data refreshed at {datetime.now()}")

# Schedule weekly refresh
schedule.every().monday.at("06:00").do(refresh_job)

# Run in background thread
import threading
def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()
```

## Need Help?

- **BeautifulSoup docs:** https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- **Requests docs:** https://requests.readthedocs.io/
- **Data Golf API:** https://datagolf.com/api-access
- **PGA Tour stats:** https://www.pgatour.com/stats

## Legal Considerations

- **Respect robots.txt**
- **Rate limit your requests** (2-5 seconds between calls)
- **PGA Tour data is proprietary** - personal use only
- **Consider official APIs** for commercial use

---

**Good luck with your integration!** The app is designed to make adding real data straightforward.
