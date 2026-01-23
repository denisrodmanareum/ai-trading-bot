import os
import glob

def cleanup_models(directory="data/models", keep=20):  # 20개로 증가
    # Get all .zip files
    files = glob.glob(os.path.join(directory, "*.zip"))
    
    # Sort by modification time (newest first)
    files.sort(key=os.path.getmtime, reverse=True)
    
    if len(files) <= keep:
        print(f"Only {len(files)} models found. No cleanup needed.")
        return

    to_delete = files[keep:]
    print(f"Found {len(files)} models. Deleting {len(to_delete)} old files...")
    
    count = 0
    for f in to_delete:
        try:
            os.remove(f)
            # Also try to remove associated history file if exists
            hist = f.replace('.zip', '_history.json')
            if os.path.exists(hist):
                os.remove(hist)
            count += 1
        except Exception as e:
            print(f"Error deleting {f}: {e}")
            
    print(f"Successfully deleted {count} old models + associated histories.")
    print(f"Kept these {keep} models:")
    for f in files[:keep]:
        print(f" - {os.path.basename(f)}")

if __name__ == "__main__":
    # Adjust path if running not from backend root
    cleanup_models()
