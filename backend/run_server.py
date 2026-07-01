"""启动后端服务器"""
import sys
import os
import traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

try:
    from app.main import app
    import uvicorn
    if __name__ == "__main__":
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
except Exception as e:
    with open("startup_error.txt", "w", encoding="utf-8") as f:
        traceback.print_exc(file=f)
    print(f"ERROR: {e}")
    sys.exit(1)
