"""
Test script to verify PGA Fantasy Tracker installation

Run this after setup to ensure everything is working properly
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        import streamlit
        print("  ✅ streamlit")
    except ImportError:
        print("  ❌ streamlit - Run: pip install streamlit")
        return False
    
    try:
        import pandas
        print("  ✅ pandas")
    except ImportError:
        print("  ❌ pandas - Run: pip install pandas")
        return False
    
    try:
        import requests
        print("  ✅ requests")
    except ImportError:
        print("  ❌ requests - Run: pip install requests")
        return False
    
    try:
        from bs4 import BeautifulSoup
        print("  ✅ beautifulsoup4")
    except ImportError:
        print("  ❌ beautifulsoup4 - Run: pip install beautifulsoup4")
        return False
    
    return True

def test_utils():
    """Test that utils modules can be imported"""
    print("\n🧪 Testing utils modules...")
    
    try:
        from utils.database import DatabaseManager
        print("  ✅ DatabaseManager")
    except ImportError as e:
        print(f"  ❌ DatabaseManager - {e}")
        return False
    
    try:
        from utils.data_fetcher import PGADataFetcher
        print("  ✅ PGADataFetcher")
    except ImportError as e:
        print(f"  ❌ PGADataFetcher - {e}")
        return False
    
    try:
        from utils.predictor import WinPredictor
        print("  ✅ WinPredictor")
    except ImportError as e:
        print(f"  ❌ WinPredictor - {e}")
        return False
    
    return True

def test_database():
    """Test database operations"""
    print("\n🧪 Testing database...")
    
    try:
        from utils.database import DatabaseManager
        
        db = DatabaseManager()
        print("  ✅ Database initialized")
        
        # Test picks count
        count = db.get_picks_count()
        print(f"  ✅ Picks count: {count}")
        
        # Test used players
        used = db.get_used_players()
        print(f"  ✅ Used players: {len(used)}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Database error - {e}")
        return False

def test_data_fetcher():
    """Test data fetching"""
    print("\n🧪 Testing data fetcher...")
    
    try:
        from utils.data_fetcher import PGADataFetcher
        
        fetcher = PGADataFetcher()
        print("  ✅ Data fetcher initialized")
        
        # Test tournament fetch
        tournament = fetcher.get_current_tournament()
        if tournament:
            print(f"  ✅ Current tournament: {tournament.get('name', 'Unknown')}")
        else:
            print("  ⚠️  No current tournament (this is OK)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Data fetcher error - {e}")
        return False

def test_predictor():
    """Test prediction engine"""
    print("\n🧪 Testing predictor...")
    
    try:
        from utils.predictor import WinPredictor
        from utils.data_fetcher import PGADataFetcher
        
        predictor = WinPredictor()
        print("  ✅ Predictor initialized")
        
        # Test with sample tournament
        fetcher = PGADataFetcher()
        tournament = fetcher.get_current_tournament()
        
        field = predictor.get_ranked_field(tournament)
        if not field.empty:
            print(f"  ✅ Generated field rankings: {len(field)} players")
        else:
            print("  ⚠️  No field data (using sample data)")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Predictor error - {e}")
        return False

def test_file_structure():
    """Test that all required files exist"""
    print("\n🧪 Testing file structure...")
    
    required_files = [
        'app.py',
        'setup.py',
        'requirements.txt',
        'config.py',
        'README.md',
        'utils/__init__.py',
        'utils/database.py',
        'utils/data_fetcher.py',
        'utils/predictor.py'
    ]
    
    all_exist = True
    for file in required_files:
        if Path(file).exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - Missing!")
            all_exist = False
    
    return all_exist

def main():
    print("=" * 60)
    print("🏌️ PGA FANTASY TRACKER - INSTALLATION TEST")
    print("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Python Imports", test_imports),
        ("Utils Modules", test_utils),
        ("Database", test_database),
        ("Data Fetcher", test_data_fetcher),
        ("Predictor", test_predictor)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:12} {test_name}")
    
    print("-" * 60)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! You're ready to use the app.")
        print("\nTo start the app, run:")
        print("  streamlit run app.py")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        print("\nCommon fixes:")
        print("  1. pip install -r requirements.txt")
        print("  2. Make sure you're in the pga_fantasy_tracker directory")
        print("  3. Run python setup.py to initialize the database")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
