"""Simple server startup"""
import sys
import os
import traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

try:
    from app.main import app
    import uvicorn
    print("App loaded successfully")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
    sys.exit(1)
