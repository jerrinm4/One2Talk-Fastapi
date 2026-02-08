from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from routers import admin, user
from database import engine, Base

# Create Tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# Custom 404 Exception Handler
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)
    # For other HTTP exceptions, return default JSON response
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Mount API Routers
app.include_router(admin.router)
app.include_router(user.router)

# Mount Static Files
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# Mount Uploads
import os
if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Mount Admin Static (We will create this directory)
if not os.path.exists("static/admin"):
    os.makedirs("static/admin")
app.mount("/static/admin", StaticFiles(directory="static/admin"), name="admin_static")

# Serve User UI (Index)
@app.get("/")
async def read_index():
    return FileResponse('index.html')

# Serve Admin Dashboard
@app.get("/admin", response_class=HTMLResponse)
async def read_admin_dashboard(request: Request):
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "active_page": "dashboard"})

# Serve Admin Login
@app.get("/admin/login", response_class=HTMLResponse)
async def read_admin_login(request: Request):
    return templates.TemplateResponse("admin/login.html", {"request": request})

# Serve Admin Manage Page
@app.get("/admin/manage", response_class=HTMLResponse)
async def read_admin_manage(request: Request):
    return templates.TemplateResponse("admin/manage.html", {"request": request, "active_page": "manage"})

# Serve Admin Users Page
@app.get("/admin/users", response_class=HTMLResponse)
async def read_admin_users(request: Request):
    return templates.TemplateResponse("admin/users.html", {"request": request, "active_page": "users"})

# Serve Admin Users Management Page (for managing admin accounts)
@app.get("/admin/admin-users", response_class=HTMLResponse)
async def read_admin_admin_users(request: Request):
    return templates.TemplateResponse("admin/admin-users.html", {"request": request, "active_page": "admin-users"})

# Serve Admin Settings Page
@app.get("/admin/settings", response_class=HTMLResponse)
async def read_admin_settings(request: Request):
    return templates.TemplateResponse("admin/settings.html", {"request": request, "active_page": "settings"})

