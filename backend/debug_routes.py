import sys
import os

# Ensure we can import app
sys.path.append(os.getcwd())

try:
    from app.main import app
    print("\n=== DEBUG ROUTES START ===")
    found = False
    for route in app.routes:
        print(f"Route: {route.path}")
        if "recent" in route.path:
            found = True
    print("=== DEBUG ROUTES END ===")
    
    if found:
        print("\nSUCCESS: Recent trades routes FOUND!")
    else:
        print("\nFAILURE: Recent trades routes NOT found.")

    import app.api.trading
    print(f"Trading file: {app.api.trading.__file__}")

except Exception as e:
    print(f"Error: {e}")
