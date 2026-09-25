import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .api import graph
from .api.auth import router as auth_router
from .api.search import router as search_router
from .api.actors import router as actors_router
from .routers.export import router as export_router
from .routers.ml import router as ml_router
from .routers.attribution import router as attribution_router
from .routers.timeline import router as timeline_router
from .routers.posts import router as posts_router
from .routers.internal import router as internal_router

from .database import engine, Base, init_db


app = FastAPI(
    title="SIH Dark Web Attribution API",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


# Mount Core API Routers with and without /api prefixes
app.include_router(graph.router, prefix="/api")
app.include_router(graph.router)

app.include_router(auth_router)
app.include_router(search_router)
app.include_router(actors_router)

app.include_router(export_router, prefix="/api")
app.include_router(export_router)

app.include_router(ml_router, prefix="/api")
app.include_router(ml_router)

app.include_router(attribution_router, prefix="/api")
app.include_router(attribution_router)

app.include_router(timeline_router, prefix="/api")
app.include_router(timeline_router)

app.include_router(posts_router, prefix="/api")
app.include_router(posts_router)

app.include_router(internal_router, prefix="/api")
app.include_router(internal_router)


@app.get("/health")
@app.get("/api/health")
def health():
    return {"status": "ok", "service": "TraceVeil Core Attribution & Knowledge Graph API"}


# Mount Frontend Static Assets for Direct Serving
candidates = [
    Path(__file__).resolve().parents[2] / "frontend",
    Path(__file__).resolve().parents[1] / "frontend",
    Path("/app/frontend"),
    Path.cwd() / "frontend",
    Path.cwd(),
]
frontend_dir = None
for c in candidates:
    if (c / "index.html").exists():
        frontend_dir = c
        break

if frontend_dir:
    if (frontend_dir / "css").exists():
        app.mount("/css", StaticFiles(directory=str(frontend_dir / "css")), name="css")
    if (frontend_dir / "js").exists():
        app.mount("/js", StaticFiles(directory=str(frontend_dir / "js")), name="js")

    @app.get("/")
    def serve_index():
        return FileResponse(str(frontend_dir / "index.html"))

    @app.get("/index.html")
    def serve_index_html():
        return FileResponse(str(frontend_dir / "index.html"))

    @app.get("/BACKEND_CONNECT.js")
    def serve_backend_connect():
        return FileResponse(str(frontend_dir / "BACKEND_CONNECT.js"))


    
