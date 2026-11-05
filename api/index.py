import sys
import os
import traceback
from pathlib import Path

# Add root directory to sys.path and ensure current working directory is root
root_dir = Path(__file__).resolve().parent.parent
os.chdir(str(root_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    from app.main import app
except Exception as e:
    err_tb = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    def catch_all(path: str = ""):
        return HTMLResponse(
            f"<html><head><title>Application Startup Error</title></head><body style='font-family:sans-serif;padding:24px;line-height:1.6;'>"
            f"<h2 style='color:#e11d48;'>Application Startup Error</h2>"
            f"<p>An error occurred while loading the application on Vercel:</p>"
            f"<pre style='background:#1e293b;color:#f8fafc;padding:16px;border-radius:8px;overflow:auto;font-size:13px;'>{err_tb}</pre>"
            f"</body></html>",
            status_code=500
        )
