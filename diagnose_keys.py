import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

try:
    from app.core.config import settings
    
    key = settings.BINANCE_API_KEY
    secret = settings.BINANCE_API_SECRET
    
    def analyze(name, val):
        if not val:
            print(f"{name}: EMPTY")
            return
        
        print(f"{name} Analysis:")
        print(f"  - Length: {len(val)}")
        print(f"  - Starts with space: {val.startswith(' ')}")
        print(f"  - Ends with space: {val.endswith(' ')}")
        print(f"  - Contains whitespace: {any(c.isspace() for c in val)}")
        print(f"  - All ASCII: {all(ord(c) < 128 for c in val)}")
        print(f"  - First 4: {val[:4]}")
        print(f"  - Last 4: {val[-4:]}")
        
    analyze("API_KEY", key)
    analyze("API_SECRET", secret)
    print(f"TESTNET: {settings.BINANCE_TESTNET}")
    print(f"ENV_FILE: {Path(__file__).parent / 'backend' / '.env'}")
    
except Exception as e:
    print(f"Diagnostic Error: {e}")
