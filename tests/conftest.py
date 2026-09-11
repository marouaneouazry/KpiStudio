import sys
import os

# Ensure the app directory is in the Python path so tests can import from it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app")))
