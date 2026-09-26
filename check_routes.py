from backend.app.main import app

def walk(routes, indent=0):
    for r in routes:
        type_name = type(r).__name__
        if type_name == "_IncludedRouter":
            sub_router = getattr(r, "original_router", None)
            sub_routes = getattr(sub_router, "routes", [])
            print("  " * indent + f"[included router, prefix={getattr(sub_router, 'prefix', '?')}]")
            walk(sub_routes, indent + 1)
        else:
            path = getattr(r, "path", "?")
            methods = getattr(r, "methods", None)
            print("  " * indent + f"{type_name}: {path} {methods or ''}")

walk(app.routes)