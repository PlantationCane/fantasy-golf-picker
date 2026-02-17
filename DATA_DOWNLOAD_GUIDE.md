# 📥 Weekly Data Download Instructions

## What Changed

Instead of scraping PGA Tour data in real-time (slow, causes timeouts), the app now:

1. ✅ **Downloads data once per week** → Stores locally in database
2. ✅ **Loads from local database** → Super fast!
3. ✅ **Updates on-demand** → Click to refresh

## 🚀 How to Use

### First Time Setup (Download Real Data)

```cmd
cd "C:\Users\vince\Dropbox\Fantasy Golf Picker"
python download_data.py
```

**You'll be asked to enter:**
- Tournament name (e.g., "The Genesis Invitational")
- Dates (e.g., "Feb 13-16, 2026")
- Course name (e.g., "Riviera Country Club")
- Purse (e.g., "$20,000,000")

**Then it automatically downloads:**
- ✅ FedEx Cup standings (Top 100 players)
- ✅ Strokes Gained: Total stats
- ✅ Season money leaders

All data is stored in `pga_fantasy.db` and loads instantly!

### Weekly Refresh (Every Monday)

```cmd
python download_data.py
```

Run this once per week (Monday morning recommended) to get fresh stats.

## 📁 What Gets Downloaded

### FedEx Cup Standings
- Top 100 players
- Current rankings
- Stored in: `tournament_field` table

### Strokes Gained Stats
- SG: Total for all players
- Rankings
- Stored in: `player_stats` table

### Money List
- Season earnings
- Top 100 earners
- Stored in: `player_stats` table

## ✅ After Download

**Restart your app:**
```cmd
streamlit run app.py
```

**You'll now see:**
- ✅ Real PGA Tour players (not sample data)
- ✅ Real FedEx Cup rankings
- ✅ Real Strokes Gained stats
- ✅ Real season earnings
- ✅ All 100+ players in the field!

## 🎯 Updated Files

Replace these 3 files:

1. **download_data.py** → Main folder (new file)
2. **utils/data_fetcher.py** → Replace existing
3. **utils/predictor.py** → Already updated

## 📊 Data Sources

Currently downloads from:
- **FedEx Cup Standings**: https://www.pgatour.com/stats/stat.02671.html
- **SG: Total**: https://www.pgatour.com/stats/stat.02675.html
- **Money List**: https://www.pgatour.com/stats/stat.109.html

## 🔄 How Often to Update

**Recommended schedule:**
- **Monday morning** → Download fresh data for the week
- **During tournament** → No need to update (picks already made)
- **Next Monday** → Download again

## ⚡ Benefits

**Before (Real-time scraping):**
- ❌ Very slow (30+ seconds to load)
- ❌ Times out frequently
- ❌ Only showed 2 players
- ❌ Hammers PGA Tour servers

**After (Weekly download):**
- ✅ Loads instantly (<1 second)
- ✅ Never times out
- ✅ Shows all 100+ players
- ✅ Respects PGA Tour servers (only 3 requests per week)

## 🛠️ Troubleshooting

### "Could not access FedEx standings"
- PGA Tour website might be down
- Try again in a few minutes
- Or manually enter tournament info and skip stats

### "No players showing up"
- Make sure you replaced both files
- Run `python download_data.py` first
- Restart the Streamlit app

### Data looks old
- Check when last updated: Run `download_data.py` (it shows age)
- Download fresh data if > 7 days old

## 🔮 Future Enhancements

**Coming soon:**
- Download SG: Off-the-Tee, Approach, Around Green, Putting
- Download course history
- Download recent tournament results
- Automatic weekly downloads
- World Golf Rankings integration

## 📞 Quick Commands

```cmd
# Download fresh data
python download_data.py

# Start app
streamlit run app.py

# Test everything works
python test_setup.py
```

---

**That's it! Real data, super fast loading!** 🏌️⛳
