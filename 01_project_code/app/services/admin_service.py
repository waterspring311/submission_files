from sqlalchemy import inspect

from .. import config as config_module
from ..extensions import db
from ..models import SystemConfig


CONFIG_FIELDS = [
    {"key": "API_KEY", "group": "llm", "group_label": "大模型配置", "label": "API Key", "secret": True},
    {"key": "API_URL", "group": "llm", "group_label": "大模型配置", "label": "接口地址", "secret": False},
    {"key": "API_MODEL", "group": "llm", "group_label": "大模型配置", "label": "模型名称", "secret": False},
    {
        "key": "API_FORMAT",
        "group": "llm",
        "group_label": "大模型配置",
        "label": "请求格式",
        "secret": False,
        "type": "select",
        "options": [
            ("auto", "自动识别"),
            ("openai_chat", "Chat Completions"),
            ("openai_responses", "Responses"),
            ("anthropic_messages", "Messages"),
            ("gemini", "Gemini 原生"),
            ("dashscope", "DashScope 原生"),
        ],
    },
    {"key": "MAIL_SENDER", "group": "email", "group_label": "邮箱配置", "label": "发件邮箱", "secret": False},
    {"key": "MAIL_PASSWORD", "group": "email", "group_label": "邮箱配置", "label": "邮箱授权码", "secret": True},
    {"key": "MAIL_SERVER", "group": "email", "group_label": "邮箱配置", "label": "SMTP服务器", "secret": False},
    {"key": "MAIL_PORT", "group": "email", "group_label": "邮箱配置", "label": "SMTP端口", "secret": False},
    {"key": "HR_EMAIL", "group": "email", "group_label": "邮箱配置", "label": "HR接收邮箱", "secret": False},
    {"key": "APP_BASE_URL", "group": "app", "group_label": "系统配置", "label": "系统访问地址", "secret": False},
]


def _runtime_value(key):
    if key == "API_KEY":
        return config_module.API_CONFIG.get("key") or ""
    if key == "API_URL":
        return config_module.API_CONFIG.get("url") or ""
    if key == "API_MODEL":
        return config_module.API_CONFIG.get("model") or ""
    if key == "API_FORMAT":
        return config_module.API_CONFIG.get("format") or "auto"
    if key == "MAIL_SENDER":
        return config_module.EMAIL_CONFIG.get("sender") or ""
    if key == "MAIL_PASSWORD":
        return config_module.EMAIL_CONFIG.get("password") or ""
    if key == "MAIL_SERVER":
        return config_module.EMAIL_CONFIG.get("server") or ""
    if key == "MAIL_PORT":
        return str(config_module.EMAIL_CONFIG.get("port") or "")
    if key == "HR_EMAIL":
        return config_module.EMAIL_CONFIG.get("hr_email") or ""
    if key == "APP_BASE_URL":
        return config_module.APP_BASE_URL or ""
    return ""


def ensure_admin_schema():
    SystemConfig.__table__.create(db.engine, checkfirst=True)
    inspector = inspect(db.engine)
    table_columns = {
        table_name: {column["name"] for column in inspector.get_columns(table_name)}
        for table_name in ("job_positions", "resume_record")
        if inspector.has_table(table_name)
    }

    with db.engine.begin() as conn:
        job_columns = table_columns.get("job_positions", set())
        added_job_review_status = False
        if "review_status" not in job_columns:
            conn.exec_driver_sql("ALTER TABLE job_positions ADD COLUMN review_status VARCHAR(50) DEFAULT 'pending'")
            added_job_review_status = True
        if "review_notes" not in job_columns:
            conn.exec_driver_sql("ALTER TABLE job_positions ADD COLUMN review_notes TEXT")
        if "reviewed_at" not in job_columns:
            conn.exec_driver_sql("ALTER TABLE job_positions ADD COLUMN reviewed_at DATETIME")
        if added_job_review_status:
            conn.exec_driver_sql("UPDATE job_positions SET review_status = 'approved'")

        resume_columns = table_columns.get("resume_record", set())
        if "review_status" not in resume_columns:
            conn.exec_driver_sql("ALTER TABLE resume_record ADD COLUMN review_status VARCHAR(50) DEFAULT 'pending'")
        if "review_notes" not in resume_columns:
            conn.exec_driver_sql("ALTER TABLE resume_record ADD COLUMN review_notes TEXT")
        if "reviewed_at" not in resume_columns:
            conn.exec_driver_sql("ALTER TABLE resume_record ADD COLUMN reviewed_at DATETIME")


def seed_system_config():
    existing = {item.config_key for item in SystemConfig.query.all()}
    for field in CONFIG_FIELDS:
        if field["key"] in existing:
            continue
        db.session.add(
            SystemConfig(
                config_key=field["key"],
                config_value=_runtime_value(field["key"]),
                config_group=field["group"],
                label=field["label"],
                is_secret=1 if field["secret"] else 0,
            )
        )
    db.session.commit()


def apply_runtime_config(app=None):
    values = {item.config_key: item.config_value or "" for item in SystemConfig.query.all()}
    config_module.API_CONFIG["key"] = values.get("API_KEY", config_module.API_CONFIG.get("key"))
    config_module.API_CONFIG["url"] = values.get("API_URL", config_module.API_CONFIG.get("url"))
    config_module.API_CONFIG["model"] = values.get("API_MODEL", config_module.API_CONFIG.get("model"))
    config_module.API_CONFIG["format"] = values.get("API_FORMAT", config_module.API_CONFIG.get("format", "auto")) or "auto"

    config_module.EMAIL_CONFIG["sender"] = values.get("MAIL_SENDER", config_module.EMAIL_CONFIG.get("sender"))
    config_module.EMAIL_CONFIG["password"] = values.get("MAIL_PASSWORD", config_module.EMAIL_CONFIG.get("password"))
    config_module.EMAIL_CONFIG["server"] = values.get("MAIL_SERVER", config_module.EMAIL_CONFIG.get("server"))
    config_module.EMAIL_CONFIG["hr_email"] = values.get("HR_EMAIL", config_module.EMAIL_CONFIG.get("hr_email"))
    try:
        config_module.EMAIL_CONFIG["port"] = int(values.get("MAIL_PORT") or config_module.EMAIL_CONFIG.get("port"))
    except (TypeError, ValueError):
        config_module.EMAIL_CONFIG["port"] = 465

    app_base_url = values.get("APP_BASE_URL") or config_module.APP_BASE_URL
    config_module.APP_BASE_URL = app_base_url
    if app is not None:
        app.config["APP_BASE_URL"] = app_base_url


def initialize_admin_features(app):
    with app.app_context():
        db.create_all()
        ensure_admin_schema()
        seed_system_config()
        apply_runtime_config(app)


def grouped_config_items():
    items = {item.config_key: item for item in SystemConfig.query.order_by(SystemConfig.config_group, SystemConfig.id).all()}
    grouped = []
    for field in CONFIG_FIELDS:
        group = next((entry for entry in grouped if entry["key"] == field["group"]), None)
        if group is None:
            group = {"key": field["group"], "label": field["group_label"], "fields": []}
            grouped.append(group)
        group["fields"].append({"field": field, "config": items.get(field["key"])})
    return grouped


def save_system_config(form, app=None):
    items = {item.config_key: item for item in SystemConfig.query.all()}
    for field in CONFIG_FIELDS:
        key = field["key"]
        item = items.get(key)
        if item is None:
            item = SystemConfig(
                config_key=key,
                config_group=field["group"],
                label=field["label"],
                is_secret=1 if field["secret"] else 0,
            )
            db.session.add(item)
        value = form.get(key, "")
        item.config_value = value if field["secret"] else value.strip()
        item.config_group = field["group"]
        item.label = field["label"]
        item.is_secret = 1 if field["secret"] else 0
    db.session.commit()
    apply_runtime_config(app)
