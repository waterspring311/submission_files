from dataclasses import dataclass

from .orm_repository import verify_hr_login


ROLE_LABELS = {
    "candidate": "求职者",
    "recruiter": "招聘者",
    "admin": "管理员",
}


DEMO_USERS = {
    "candidate": {
        "password": "123456",
        "role": "candidate",
        "display_name": "求职者用户",
    },
    "recruiter": {
        "password": "123456",
        "role": "recruiter",
        "display_name": "招聘者用户",
    },
    "admin": {
        "password": "123456",
        "role": "admin",
        "display_name": "管理员",
    },
}


@dataclass
class AuthResult:
    ok: bool
    user: dict | None = None
    error: str = ""


def normalize_role(role):
    role = (role or "").lower()
    if role in ROLE_LABELS:
        return role
    if role in ("hr", "recruit", "recruiter_user"):
        return "recruiter"
    return "recruiter"


def authenticate_user(username, password, requested_role=None):
    username = (username or "").strip()
    password = password or ""
    requested_role = requested_role or ""

    demo_user = DEMO_USERS.get(username)
    if demo_user and demo_user["password"] == password:
        role = demo_user["role"]
        if requested_role and requested_role != role:
            return AuthResult(False, error=f"该账号不是{ROLE_LABELS.get(requested_role, requested_role)}角色")
        return AuthResult(
            True,
            user={
                "username": username,
                "display_name": demo_user["display_name"],
                "role": role,
                "role_label": ROLE_LABELS[role],
            },
        )

    hr_user = verify_hr_login(username, password)
    if not hr_user:
        return AuthResult(False, error="用户名或密码错误")

    role = normalize_role(hr_user.role)
    if requested_role and requested_role != role:
        return AuthResult(False, error=f"该账号不是{ROLE_LABELS.get(requested_role, requested_role)}角色")

    return AuthResult(
        True,
        user={
            "id": hr_user.id,
            "username": hr_user.username,
            "display_name": hr_user.real_name,
            "role": role,
            "role_label": ROLE_LABELS[role],
        },
    )


def home_endpoint_for_role(role):
    if role == "candidate":
        return "candidate.index"
    if role == "admin":
        return "admin.dashboard"
    return "main.index"
