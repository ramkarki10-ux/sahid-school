from pathlib import Path
from fastapi.templating import Jinja2Templates

# Robust absolute resolution of the templates directory
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
if not TEMPLATES_DIR.exists():
    TEMPLATES_DIR = Path.cwd() / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

