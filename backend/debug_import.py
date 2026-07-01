import sys
import os
import traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

results = []

def step(name, func):
    try:
        func()
        results.append(f"OK: {name}")
    except Exception as e:
        results.append(f"FAIL: {name} -> {type(e).__name__}: {e}")
        results.append(traceback.format_exc())

step("config", lambda: __import__('app.config'))
step("database", lambda: __import__('app.database'))
step("core.cache", lambda: __import__('app.core.cache'))
step("core.exceptions", lambda: __import__('app.core.exceptions'))
step("core.logging", lambda: __import__('app.core.logging'))
step("core.rate_limiter", lambda: __import__('app.core.rate_limiter'))
step("core.ssrf", lambda: __import__('app.core.ssrf'))
step("schemas.query", lambda: __import__('app.schemas.query'))
step("schemas.paper", lambda: __import__('app.schemas.paper'))
step("schemas.search", lambda: __import__('app.schemas.search'))
step("models.search_run", lambda: __import__('app.models.search_run'))
step("models.paper", lambda: __import__('app.models.paper'))
step("services.sources.base", lambda: __import__('app.services.sources.base'))
step("services.llm.gateway", lambda: __import__('app.services.llm.gateway'))
step("services.search.query_planner", lambda: __import__('app.services.search.query_planner'))
step("api.v1.router", lambda: __import__('app.api.v1.router'))
step("main", lambda: __import__('app.main'))

with open("debug_output.txt", "w", encoding="utf-8") as f:
    for r in results:
        f.write(r + "\n")

print("Done - check debug_output.txt")
