"""Fresh-install functional check of a packaged backend; never uses private keys.

Usage: python scripts/packaging/smoke_backend.py <executable> [--live-search]
The optional search makes a real Crossref request, not an LLM request.
"""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request


def main():
    executable = Path(sys.argv[1]).resolve()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    checks = []
    with tempfile.TemporaryDirectory(prefix="scholarnova-backend-qa-") as directory:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        token = secrets.token_hex(32)
        env = {k: v for k, v in os.environ.items()
               if not any(word in k.upper() for word in ("API_KEY", "TOKEN", "DATABASE_URL", "RUNTIME_DIR"))}
        env.update(APP_ENV="desktop", DEBUG="false", HOST="127.0.0.1", PORT=str(port),
                   RUNTIME_DIR=directory, REDIS_URL="",
                   DATABASE_URL=f"sqlite+aiosqlite:///{Path(directory).as_posix()}/qa.db",
                   SCHOLARNOVA_DESKTOP_TOKEN=token)
        base = f"http://127.0.0.1:{port}/api/v1"

        def request(path, data=None, method=None, authenticated=True):
            headers = {"Content-Type": "application/json"}
            if authenticated:
                headers["x-scholarnova-session"] = token
            req = urllib.request.Request(base + path, headers=headers, method=method,
                                         data=json.dumps(data).encode() if data is not None else None)
            with opener.open(req, timeout=20) as response:
                body = response.read()
                return json.loads(body) if body else None

        process = None
        log_path = Path(directory) / "backend.log"
        with log_path.open("ab") as log:
            def start():
                process = subprocess.Popen([str(executable)], cwd=directory, env=env,
                                           stdout=log, stderr=log,
                                           creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0)
                deadline = time.monotonic() + 45
                while time.monotonic() < deadline:
                    try:
                        if request("/health/live")["status"] == "ok":
                            return process
                    except (urllib.error.URLError, TimeoutError):
                        if process.poll() is not None:
                            break
                    time.sleep(.3)
                process.terminate()
                process.wait(timeout=10)
                raise RuntimeError("Packaged backend startup failed")

            try:
                process = start()
                try:
                    request("/health/live", authenticated=False)
                    raise AssertionError("Unauthenticated backend access was accepted")
                except urllib.error.HTTPError as error:
                    assert error.code == 403
                checks.append("private desktop session enforced")
                for question in ("目前这个智能体怎么使用？", "介绍一下你自己", "你是谁", "What can you do?", "你可以做什么？"):
                    help_result = request("/agent/chat", {"question": question, "use_zotero": False})
                    assert help_result["response_type"] == "product_help", question
                    assert all(help_result[field] == 0 for field in (
                        "prompt_tokens", "completion_tokens", "retrieval_tokens", "total_tokens")), question
                    assert help_result["provider"] is None and help_result["model"] is None, question
                    assert help_result["inference_mode"] == "none" and help_result["model_route"] == "none", question
                    assert help_result["model_attempts"] == [] and help_result["citations"] == [], question
                    assert {step["tool"] for step in help_result["tool_steps"]} == {"product_help"}, question
                checks.append("five bilingual product-help and identity prompts bypass model and research tools")

                # An academic concept is not an application-support request. In
                # this isolated empty library it must abstain without model calls.
                research_result = request("/agent/chat", {"question": "智能体是什么", "use_zotero": False})
                assert research_result["response_type"] == "research"
                assert all(research_result[field] == 0 for field in (
                    "prompt_tokens", "completion_tokens", "retrieval_tokens", "total_tokens"))
                assert research_result["provider"] is None and research_result["model"] is None
                assert research_result["inference_mode"] == "none" and research_result["model_route"] == "none"
                assert research_result["model_attempts"] == [] and research_result["citations"] == []
                steps = {step["tool"]: step for step in research_result["tool_steps"]}
                assert "knowledge_search" in steps and "product_help" not in steps and "answer_generation" not in steps
                assert steps["knowledge_search"]["count"] == 0 and steps["evidence_pack"]["count"] == 0
                checks.append("generic agent concept stays research and abstains without evidence or model calls")
                item = request("/knowledge", {"title": "QA citation fixture", "category": "QA isolated",
                               "content": "Graph models represent road-network dependencies. This is synthetic QA content.",
                               "auto_polish": False})
                item_id = item["id"]
                assert request(f"/knowledge/{item_id}")["title"] == "QA citation fixture"
                request(f"/knowledge/{item_id}", {"notes": "Saved locally"}, "PUT")
                checks.append("knowledge create, retrieve and update")

                if "--live-search" in sys.argv:
                    started = time.monotonic()
                    run = request("/search", {"query": "traffic flow prediction graph neural networks",
                                  "max_results": 5, "sources": ["crossref"],
                                  "preferences": {"iterative_search": False}})
                    deadline = started + 100
                    while time.monotonic() < deadline:
                        result = request("/search/" + run["run_id"])
                        if result["status"] in ("completed", "failed"):
                            break
                        time.sleep(1)
                    assert result["status"] == "completed" and result.get("results"), "Live search did not return papers"
                    checks.append({"live_crossref_papers": len(result["results"]),
                                   "elapsed_seconds": round(time.monotonic() - started, 2)})

                process.terminate()
                process.wait(timeout=15)
                process = start()
                assert request(f"/knowledge/{item_id}")["notes"] == "Saved locally"
                request(f"/knowledge/{item_id}", method="DELETE")
                checks.append("knowledge survives backend restart and can be deleted")
                print(json.dumps({"success": True, "checks": checks, "llm_calls": 0}, ensure_ascii=True))
            except Exception:
                print(log_path.read_text(encoding="utf-8", errors="replace")[-3000:])
                raise
            finally:
                if process and process.poll() is None:
                    process.terminate()
                    process.wait(timeout=15)


if __name__ == "__main__":
    main()
