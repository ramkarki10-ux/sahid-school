from pathlib import Path
from fastapi.templating import Jinja2Templates
from jinja2 import FileSystemLoader

base_dir = Path(__file__).resolve().parent.parent
candidate_dirs = [
    base_dir / "templates",
    base_dir / "api" / "templates",
    Path("/var/task/templates"),
    Path("/var/task/api/templates"),
    Path.cwd() / "templates",
    Path.cwd() / "api" / "templates",
]
search_dirs = [str(d) for d in candidate_dirs if d.exists()]
if not search_dirs:
    search_dirs = [str(base_dir / "templates")]

templates = Jinja2Templates(directory=search_dirs[0])
templates.env.loader = FileSystemLoader(search_dirs)
