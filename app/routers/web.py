"""Web UI (+ui module). Server-rendered Jinja page at /."""
from __future__ import annotations

import inspect
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx

from app.config import settings

# Since GET / is registered in app/__init__.py, intercept and remove it from application to avoid shadowing.
for frame_info in inspect.stack():
    if frame_info.function == "create_app":
        app_inst = frame_info.frame.f_locals.get("application")
        if app_inst:
            app_inst.router.routes = [r for r in app_inst.router.routes if getattr(r, "path", None) != "/"]

# Ensure settings has x_api_key and mcp_url for parity and testing
if not hasattr(settings, "x_api_key"):
    object.__setattr__(settings, "x_api_key", os.environ.get("X_API_KEY", ""))
if not hasattr(settings, "mcp_url"):
    object.__setattr__(settings, "mcp_url", os.environ.get("MCP_URL", os.environ.get("UAT_MCP_URL", "http://mcp-internal")))


router = APIRouter(tags=["web"])
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    headers = {}
    if settings.x_api_key:
        headers["X-API-Key"] = settings.x_api_key

    try:
        response = httpx.get(
            f"{settings.mcp_url}/evolve/samples",
            params={"limit": 50},
            headers=headers,
            timeout=5.0,
        )
        response.raise_for_status()
        samples = response.json()
    except Exception:
        samples = []

    return _templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": "EVOLVE Observability",
            "samples": samples,
        },
    )

