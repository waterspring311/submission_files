from flask import flash, g, redirect, request, session, url_for

from .routes.responses import fail
from .services.auth_service import home_endpoint_for_role


PUBLIC_ENDPOINTS = {
    "auth.login",
    "auth.logout",
    "main.health",
    "static",
}


ROLE_ENDPOINT_PREFIXES = {
    "candidate": (
        "candidate.",
        "interviews.take_interview",
        "main.api_jobs",
    ),
    "recruiter": (
        "main.",
        "interviews.",
        "hr.",
    ),
    "admin": (
        "admin.",
        "main.resume_detail",
    ),
}


def is_json_request():
    return request.path.startswith("/api/") or request.is_json


def is_endpoint_allowed(endpoint, role):
    if endpoint in PUBLIC_ENDPOINTS:
        return True
    allowed_prefixes = ROLE_ENDPOINT_PREFIXES.get(role, ())
    return any(endpoint == prefix or endpoint.startswith(prefix) for prefix in allowed_prefixes)


def register_auth_middleware(app):
    @app.before_request
    def require_login_and_role():
        endpoint = request.endpoint or ""
        g.current_user = session.get("user")

        if endpoint in PUBLIC_ENDPOINTS or endpoint.startswith("static"):
            return None

        if not g.current_user:
            if is_json_request():
                return fail("login required", status=401)
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))

        role = g.current_user.get("role")
        if not is_endpoint_allowed(endpoint, role):
            if is_json_request():
                return fail("permission denied", status=403)
            flash("当前角色无权访问该功能。", "warning")
            return redirect(url_for(home_endpoint_for_role(role)))

        return None

    @app.context_processor
    def inject_auth_context():
        return {"current_user": session.get("user")}
