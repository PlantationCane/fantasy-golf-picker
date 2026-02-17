# 🚀 Quick Start Guide

Get up and running in 5 minutes!

## Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed streamlit-1.31.0 pandas-2.2.0 ...
```

## Step 2: Run Setup

```bash
python setup.py
```

**What it does:**
- Creates database
- Asks about your existing picks
- Verifies setup

**Example interaction:**
```
🔧 Initializing database...
✅ Database initialized successfully!

Have you already made picks in previous weeks? (y/n): y

--- WEEK 1 (Last Week) ---
Enter player #1 name: Scottie Scheffler
Tournament name: The American Express
Enter player #2 name: Rory McIlroy  
Tournament name: The American Express

--- WEEK 2 (This Week) ---
Enter player #1 name: Xander Schauffele
Tournament name: Farmers Insurance Open
Enter player #2 name: (press Enter to skip)

✅ All picks added successfully!
```

## Step 3: Start the App

```bash
streamlit run app.py
```

**What happens:**
- App starts on http://localhost:8501
- Browser opens automatically
- You see the tournament view

## Step 4: Make Your First Pick

1. **View the tournament field** - Players ranked by win probability
2. **Click on a player** to expand their card
3. **Click "View Full Stats"** to see detailed information
4. **Click "Select Player"** to make your pick
5. **Player is now locked** for the rest of the season!

## Common First-Time Issues

### Issue: "streamlit: command not found"
**Fix:**
```bash
pip install streamlit --upgrade
```

### Issue: "ModuleNotFoundError: No module named 'utils'"
**Fix:** Make sure you're in the right directory
```bash
cd pga_fantasy_tracker
python setup.py
```

### Issue: Port 8501 already in use
**Fix:** Use a different port
```bash
streamlit run app.py --server.port 8502
```

## Next Steps

- **Explore player stats** - Click around and familiarize yourself
- **Check course history** - Look for 🔥 Excellent ratings
- **Review value picks** - Filter by "Value Score"
- **Set up automatic updates** - Edit `config.py`

## Need Help?

1. Check the main README.md
2. Run the test script: `python test_setup.py`
3. Review the troubleshooting section

---

**You're all set! Good luck with your picks!** 🏌️⛳
