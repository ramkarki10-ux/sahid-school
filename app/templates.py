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

def get_navigation_menus():
    """Retrieve active navigation menus with children hierarchy for Jinja templates."""
    try:
        from app.database import get_db
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='header_menus'")
        if not cur.fetchone():
            conn.close()
            return []
        cur.execute("SELECT * FROM header_menus WHERE is_active = 1 ORDER BY order_index ASC, id ASC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        
        top_menus = [m for m in rows if not m.get("parent_id")]
        for tm in top_menus:
            tm["children"] = [sm for sm in rows if sm.get("parent_id") == tm["id"]]
        return top_menus
    except Exception:
        return []

templates.env.globals['get_navigation_menus'] = get_navigation_menus
