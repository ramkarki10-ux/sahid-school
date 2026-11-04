import sys
import os
from pathlib import Path

# Add root directory to sys.path so app modules are discoverable on Vercel
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.main import app

