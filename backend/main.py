try:
    from app.main import app
except ImportError:
    try:
        from .app.main import app
    except ImportError:
        from backend.app.main import app

__all__ = ["app"]