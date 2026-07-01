"""Debug mode - capture all errors"""
import sys
import os
import traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

from app.main import app
import uvicorn
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="debug")
