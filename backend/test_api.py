import requests
import sys

def test_url(url):
    print(f"\nTesting: {url}")
    try:
        resp = requests.get(url, timeout=2)
        print(f"Status: {resp.status_code}")
        if resp.status_code != 200:
            print(f"Response: {resp.text[:200]}")
        else:
            data = resp.json()
            print(f"Success! Data count: {len(data) if isinstance(data, list) else 'Dict'}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    base = "http://127.0.0.1:8000"
    
    # 1. Known Good Endpoint
    test_url(f"{base}/health")
    
    # 2. Existing Endpoint (Likely working?)
    test_url(f"{base}/api/dashboard/overview")
    
    # 3. New Endpoint (The problematic one)
    test_url(f"{base}/api/trading/trades/recent?symbol=BTCUSDT&limit=10")
    
    # 4. Direct Endpoint (Main.py)
    test_url(f"{base}/api/direct/recent-trades?symbol=BTCUSDT&limit=10")
