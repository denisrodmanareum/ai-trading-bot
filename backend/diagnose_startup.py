import sys
import os
import traceback

# Add current directory to path so imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

print(f"Diagnosing Backend Startup...")
print(f"Working Directory: {current_dir}")
print(f"Python Path: {sys.path}")

try:
    print("Attempting to import app.main...")
    import app.main
    print("✅ SUCCESS: app.main imported successfully!")
    print("Startup Logic seems fine. The issue is likely environment or port conflict.")
except Exception as e:
    print("\n❌ CRITICAL ERROR: Backend failed to start/import!")
    print("="*60)
    traceback.print_exc()
    print("="*60)
    print(f"Error Message: {e}")
