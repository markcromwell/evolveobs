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
            timeout=settings.request_timeout,
        )
        response.raise_for_status()
        data = response.json()
        samples = data["samples"] if isinstance(data, dict) and "samples" in data else []
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


