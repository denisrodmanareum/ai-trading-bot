import requests

try:
    response = requests.get("http://localhost:8000/api/trading/auto/status", timeout=5)
    if response.status_code == 200:
        print("Status Check Success:")
        print(response.json())
    else:
        print(f"Status Check Failed: {response.status_code}")
except Exception as e:
    print(f"Connection Failed: {e}")
