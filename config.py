"""
Configuration file for PGA Fantasy Tracker

Modify these settings to customize the app behavior
"""

# Database settings
DATABASE_PATH = "pga_fantasy.db"

# Prediction weights (must sum close to 1.0)
PREDICTION_WEIGHTS = {
    'fedex_rank': 0.20,      # FedEx Cup ranking weight
    'world_rank': 0.15,      # World Golf Ranking weight
    'sg_total': 0.25,        # Strokes Gained Total weight
    'recent_form': 0.20,     # Recent form (last 5 tournaments)
    'course_history': 0.20   # Course history weight
}

# Data refresh settings
DATA_CACHE_HOURS = 24        # How long to cache player data
AUTO_REFRESH_ENABLED = False  # Enable automatic weekly refresh
REFRESH_DAY = 'Monday'       # Day of week to refresh (if auto enabled)
REFRESH_TIME = '06:00'       # Time to refresh (24hr format)

# Display settings
DEFAULT_PLAYERS_SHOWN = 50   # Number of players shown by default
MIN_WIN_PROBABILITY = 0.1    # Minimum win probability to display (%)
SHOW_USED_PLAYERS = False    # Show used players by default

# Contest settings
PICKS_PER_WEEK = 2           # Number of picks allowed per week
SEASON_START_DATE = '2026-01-01'
SEASON_END_DATE = '2026-12-31'

# Scoring settings
# Adjust these to match your contest rules
TOURNAMENT_PURSE_DEFAULT = 20000000  # Default purse if unknown
WINNER_PAYOUT_PCT = 0.18    # Typical winner gets 18% of purse
FINISH_2_PCT = 0.108        # 2nd place payout percentage
FINISH_3_PCT = 0.068        # 3rd place payout percentage

# Data sources
USE_DATAGOLF_API = False     # Set to True if you have Data Golf API key
DATAGOLF_API_KEY = ''        # Add your API key here if using

USE_PGA_TOUR_API = True      # Use official PGA Tour data
PGA_TOUR_DELAY_SECONDS = 2   # Delay between requests to be respectful

# Advanced settings
ENABLE_LOGGING = True        # Log data fetching activities
LOG_FILE = 'pga_tracker.log'
ENABLE_CACHE = True          # Cache player data locally

# Course fit analysis (experimental)
ENABLE_COURSE_FIT = True     # Analyze player strengths vs course demands
COURSE_FIT_FACTORS = {
    'driving_distance': True,
    'accuracy': True,
    'approach_precision': True,
    'short_game': True,
    'putting': True
}

# UI customization
APP_TITLE = "PGA Fantasy Tracker"
APP_ICON = "⛳"
THEME_COLOR = "#00a86b"      # PGA Tour green

# Value pick thresholds
VALUE_PICK_MIN_RANK = 20     # Minimum FedEx rank for value consideration
VALUE_PICK_MAX_RANK = 60     # Maximum FedEx rank for value consideration
VALUE_PICK_MIN_SCORE = 60    # Minimum value score to highlight

# Recent form settings
RECENT_FORM_TOURNAMENTS = 5  # Number of recent tournaments to analyze
EXCELLENT_FORM_AVG = 10      # Average finish for "Excellent" rating
GOOD_FORM_AVG = 20          # Average finish for "Good" rating
AVERAGE_FORM_AVG = 40       # Average finish for "Average" rating

# Course history settings
COURSE_HISTORY_YEARS = 3     # Number of years of course history to analyze
MIN_COURSE_HISTORY = 1       # Minimum appearances for course history rating

# Email notifications (optional - not yet implemented)
ENABLE_NOTIFICATIONS = False
NOTIFICATION_EMAIL = ''
NOTIFY_ON_TOURNAMENT_START = False
NOTIFY_ON_PICKS_DUE = False
