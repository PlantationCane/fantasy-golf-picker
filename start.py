#!/usr/bin/env python3
"""
Simple launcher for PGA Fantasy Tracker

Double-click this file to start the app (after initial setup)
"""

import subprocess
import sys
import webbrowser
import time
from pathlib import Path

def check_dependencies():
    """Check if dependencies are installed"""
    try:
        import streamlit
        import pandas
        import requests
        from bs4 import BeautifulSoup
        return True
    except ImportError:
        return False

def main():
    print("=" * 60)
    print("🏌️ PGA FANTASY TRACKER")
    print("=" * 60)
    
    # Check if in correct directory
    if not Path("app.py").exists():
        print("\n❌ Error: app.py not found!")
        print("Make sure you're running this from the pga_fantasy_tracker directory.")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        print("\n⚠️  Dependencies not installed!")
        print("\nWould you like to install them now? (y/n): ", end="")
        response = input().strip().lower()
        
        if response == 'y':
            print("\n📦 Installing dependencies...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
                print("✅ Dependencies installed!")
            except subprocess.CalledProcessError:
                print("❌ Installation failed. Please run: pip install -r requirements.txt")
                input("\nPress Enter to exit...")
                sys.exit(1)
        else:
            print("\nPlease install dependencies first:")
            print("  pip install -r requirements.txt")
            input("\nPress Enter to exit...")
            sys.exit(1)
    
    # Check if database exists
    if not Path("pga_fantasy.db").exists():
        print("\n⚠️  Database not found!")
        print("\nWould you like to run setup now? (y/n): ", end="")
        response = input().strip().lower()
        
        if response == 'y':
            print("\n🔧 Running setup...")
            try:
                subprocess.run([sys.executable, "setup.py"], check=True)
            except subprocess.CalledProcessError:
                print("❌ Setup failed.")
                input("\nPress Enter to exit...")
                sys.exit(1)
        else:
            print("\nPlease run setup first:")
            print("  python setup.py")
            input("\nPress Enter to exit...")
            sys.exit(1)
    
    # Start the app
    print("\n🚀 Starting PGA Fantasy Tracker...")
    print("\nThe app will open in your browser automatically.")
    print("If it doesn't, go to: http://localhost:8501")
    print("\nTo stop the app, press Ctrl+C in this window.")
    print("=" * 60)
    print()
    
    try:
        # Start Streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down app...")
        print("See you next time!")
    except Exception as e:
        print(f"\n❌ Error starting app: {e}")
        print("\nTry running manually:")
        print("  streamlit run app.py")
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
