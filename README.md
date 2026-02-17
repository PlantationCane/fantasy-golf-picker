# 🏌️ PGA Fantasy Tracker

A web-based fantasy golf tracker for managing your season-long PGA Tour picks with advanced analytics.

## Features

- **Weekly Tournament View** - See all players ranked by win probability
- **Smart Rankings** - Combines FedEx Cup, World Rankings, Strokes Gained, Recent Form, and Course History
- **Player Tracking** - Automatically greys out used players so you never pick twice
- **Detailed Stats** - View comprehensive stats for any player including:
  - Season rankings (FedEx, World, SG: Total)
  - Season earnings
  - Tournament-by-tournament results
  - Strokes Gained breakdown (OTT, App, ARG, Putting)
  - Course history at current venue
- **Value Picks** - Identifies undervalued players based on probability vs. ranking
- **Portable** - SQLite database travels with the app

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Setup Steps

1. **Download or clone this folder** to your computer

2. **Install dependencies:**
   ```bash
   cd pga_fantasy_tracker
   pip install -r requirements.txt
   ```

3. **Run the setup script:**
   ```bash
   python setup.py
   ```
   This will:
   - Initialize the database
   - Let you add your existing picks from previous weeks
   - Verify everything is working

4. **Start the app:**
   ```bash
   streamlit run app.py
   ```

5. **The app will automatically open in your web browser!**
   - Default URL: http://localhost:8501

## Usage

### Making Your Weekly Picks

1. **View Tournament Field**
   - Players are ranked by win probability
   - Available players show ✅
   - Used players show 🚫 and are greyed out

2. **Select a Player**
   - Click "View Full Stats" to see detailed information
   - Click "Select Player" to make your pick
   - Player is automatically locked for the season

3. **View Your Picks History**
   - See all your picks for the season
   - Track total winnings
   - View average finish position

### Understanding the Rankings

**Win Probability** is calculated from:
- **20%** FedEx Cup Rank
- **15%** World Golf Ranking  
- **25%** Strokes Gained: Total
- **20%** Recent Form (last 5 tournaments)
- **20%** Course History (performance at this venue)

**Value Score** identifies players where win probability is high relative to their ranking (finding gems in the 20-60 rank range)

### Key Features for Winning

1. **Course History Weight** 
   - Players with good course history are heavily favored
   - Look for 🔥 Excellent course history ratings

2. **Recent Form**
   - 🔥 Excellent = averaging top 10 finishes
   - ✅ Good = averaging top 20 finishes
   - Use this to find hot players

3. **Strokes Gained Trends**
   - SG: Total shows overall performance vs. field
   - Positive numbers = gaining strokes
   - Higher is better (top players are +2.0 or more)

4. **Value Picks**
   - Filter by "Value Score" to find undervalued players
   - Great for weeks when top players are used up

## File Structure

```
pga_fantasy_tracker/
├── app.py                      # Main Streamlit application
├── setup.py                    # Initial setup script
├── requirements.txt            # Python dependencies
├── pga_fantasy.db             # SQLite database (created on first run)
├── utils/
│   ├── __init__.py
│   ├── database.py            # Database operations
│   ├── data_fetcher.py        # PGA Tour data scraping
│   └── predictor.py           # Win probability calculations
└── README.md                  # This file
```

## Transferring to Another Computer

To move your app to another computer:

1. **Copy the entire folder** including:
   - All Python files
   - `pga_fantasy.db` (contains your picks!)
   - `requirements.txt`

2. **On the new computer:**
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

3. **Your picks and history will be intact!**

## Data Sources

Currently uses:
- **PGA Tour Official Stats** - Free, publicly available
- Sample data for development (will be replaced with live scraping)

### Upgrading to Live Data (Optional)

For the most accurate predictions, consider:

1. **Data Golf API** ($10-30/month)
   - Best win probability predictions
   - Advanced strokes gained data
   - Sign up at: https://datagolf.com/api-access

2. **Implementation:**
   - Add API key to environment variable
   - Uncomment API calls in `data_fetcher.py`
   - Update `predictor.py` to use API probabilities

## Troubleshooting

### App won't start
```bash
# Make sure you're in the right directory
cd pga_fantasy_tracker

# Verify Python version
python --version  # Should be 3.8+

# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Try running again
streamlit run app.py
```

### Database errors
```bash
# Reset database (WARNING: Deletes all picks!)
python
>>> from utils.database import DatabaseManager
>>> db = DatabaseManager()
>>> db.clear_season_data()
>>> exit()
```

### Port already in use
```bash
# Use a different port
streamlit run app.py --server.port 8502
```

## Updating Data

**Automatic (Coming Soon):**
- Weekly auto-refresh of tournament data
- Nightly updates of player stats

**Manual:**
- Click "🔄 Refresh Tournament Data" in the sidebar
- Clears cache and fetches latest information

## Tips for Success

1. **Check Course History First** - This is the #1 predictor
2. **Monitor Recent Form** - Hot players stay hot
3. **Don't Always Pick #1** - Value picks can outscore favorites
4. **Track Your Picks** - Review what's working in Picks History
5. **Save Top Tier Players** - Don't waste Scheffler early!

## Contest Rules Reminder

- **2 picks per week**
- **Each player can only be used once per season**
- **Winnings = Player's tournament earnings**
- **Most total winnings at end of season wins**

## Future Enhancements

- [ ] Automatic weekly data refresh
- [ ] Live tournament scoring updates
- [ ] Export picks to CSV/Excel
- [ ] Multi-user support (track competitors)
- [ ] Mobile app version
- [ ] Historical performance analytics
- [ ] Data Golf API integration
- [ ] Push notifications for tournament results

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review the setup steps
3. Ensure all dependencies are installed

## License

Personal use only. PGA Tour data is property of the PGA Tour.

---

**Good luck with your picks!** ⛳🏆
