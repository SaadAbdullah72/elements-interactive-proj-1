import sys
import os

# Add the backend directory to the python path so it can import its modules
backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.append(backend_dir)

# Import the FastAPI app from backend/main.py
from main import app
