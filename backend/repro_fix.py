import os
import shutil
import time
from loguru import logger

# Mock settings
class MockSettings:
    AI_MODEL_PATH = "data/test_models/"

settings = MockSettings()

def list_models():
    """Simulated list_models with the fix"""
    try:
        model_dir = settings.AI_MODEL_PATH
        if not os.path.exists(model_dir):
            return {"models": []}
        
        models = []
        # Simulate os.listdir
        files = os.listdir(model_dir)
        
        for f in files:
            if f.endswith('.zip'):
                path = os.path.join(model_dir, f)
                
                # SIMULATE DELAY or CONCURRENT DELETION
                if "delete_me" in f:
                    os.remove(path)
                    print(f"Simulated deletion of {path}")
                
                try:
                    stat = os.stat(path)
                    models.append({
                        "name": f,
                        "path": path,
                        "size": stat.st_size,
                        "modified": stat.st_mtime
                    })
                except FileNotFoundError:
                    # Skip files that might have been deleted
                    print(f"Caught expected FileNotFoundError for {path}")
                    continue
        
        models.sort(key=lambda x: x['modified'], reverse=True)
        return {"models": models}
    except Exception as e:
        print(f"Failed to list models: {e}")
        return None

def setup_test():
    os.makedirs(settings.AI_MODEL_PATH, exist_ok=True)
    # Create a normal file
    with open(os.path.join(settings.AI_MODEL_PATH, "good_model.zip"), "w") as f:
        f.write("data")
    # Create a file to be deleted during listing
    with open(os.path.join(settings.AI_MODEL_PATH, "delete_me.zip"), "w") as f:
        f.write("data")

def teardown_test():
    shutil.rmtree(settings.AI_MODEL_PATH)

if __name__ == "__main__":
    setup_test()
    print("Testing robust list_models...")
    result = list_models()
    if result is not None:
        print(f"Success! Found {len(result['models'])} models.")
        for m in result['models']:
            print(f" - {m['name']}")
    else:
        print("Test failed: Exception raised.")
    teardown_test()
