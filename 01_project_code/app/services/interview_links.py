import hashlib
import secrets
from datetime import datetime, timedelta

from flask import current_app, has_app_context

from ..config import APP_BASE_URL, INTERVIEW_CONFIG


def create_interview_token(email, resume_name, job_name):
    raw = f"{email}{resume_name}{job_name}{datetime.utcnow().timestamp()}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest() + secrets.token_hex(8)


def get_interview_expired_at(now=None):
    current = now or datetime.utcnow()
    hours = INTERVIEW_CONFIG["token_expire_hours"]
    return current + timedelta(hours=hours)


def build_interview_link(token, base_url=None):
    if base_url is None and has_app_context():
        base_url = current_app.config.get("APP_BASE_URL")
    base_url = base_url or APP_BASE_URL
    return f"{base_url}/interviews/take/{token}"
