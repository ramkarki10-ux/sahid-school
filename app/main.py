from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import os

from app.database import init_db
from app.routers import (
    public,
    admin,
    teacher,
    parent,
    api_auth,
    api_students,
    api_promotions,
    api_attendance,
    api_teachers,
    api_staff,
    api_committees,
    api_content,
    api_misc,
    api_documents,
    api_homework,
    api_sms,
    api_leave,
    api_calendar,
    api_parent,
    api_results
)

app = FastAPI(
    title="Shahid Smriti Residential Secondary School - System",
    description="Complete School Website & School Management System for सहिद स्मृति आवासीय माध्यमिक विद्यालय, Itahari-19, Sunsari, Nepal",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vercel Serverless Path Normalization Middleware
@app.middleware("http")
async def vercel_routing_middleware(request: Request, call_next):
    matched_path = request.headers.get("x-matched-path")
    if matched_path and not matched_path.startswith("/api/index.py"):
        request.scope["path"] = matched_path
    elif request.scope["path"] == "/api/index.py":
        request.scope["path"] = "/"
    elif request.scope["path"].startswith("/api/index.py/"):
        request.scope["path"] = request.scope["path"][len("/api/index.py"):]
    
    return await call_next(request)

# Static Files
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
static_dir = BASE_DIR / "static"
if not static_dir.exists():
    static_dir = Path.cwd() / "static"
if not static_dir.exists():
    try:
        static_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Include View Routers
app.include_router(public.router)
app.include_router(admin.router)
app.include_router(teacher.router)
app.include_router(parent.router)

# Include API Routers
app.include_router(api_auth.router)
app.include_router(api_students.router)
app.include_router(api_promotions.router)
app.include_router(api_attendance.router)
app.include_router(api_teachers.router)
app.include_router(api_staff.router)
app.include_router(api_committees.router)
app.include_router(api_content.router)
app.include_router(api_misc.router)
app.include_router(api_documents.router)
app.include_router(api_homework.router)
app.include_router(api_sms.router)
app.include_router(api_leave.router)
app.include_router(api_calendar.router)
app.include_router(api_parent.router)
app.include_router(api_results.router)

@app.on_event("startup")
def on_startup():
    init_db()

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    # If API call, return JSON
    if request.url.path.startswith("/api/"):
        return HTMLResponse(content='{"detail": "Not Found"}', status_code=404, media_type="application/json")
    # If view call, redirect to home or render error
    return RedirectResponse(url="/", status_code=303)
