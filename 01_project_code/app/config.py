import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BASE_DIR / "04_data" / ".env"
load_dotenv(ENV_PATH)

UPLOAD_FOLDER = str(BASE_DIR / "01_resume_inbox")
PROCESSED_FOLDER = str(BASE_DIR / "02_processed_resumes")
JD_FOLDER = str(BASE_DIR / "04_data" / "job_jd")
LOG_ROOT = str(BASE_DIR / "07_logs")
EXCEL_DATA_PATH = os.getenv(
    "EXCEL_DATA_PATH",
    str(BASE_DIR / "04_data" / "recruitment_data.xlsx"),
)

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "123456"),
    "database": os.getenv("MYSQL_DATABASE", "recruitment"),
    "charset": os.getenv("MYSQL_CHARSET", "utf8mb4"),
}

API_CONFIG = {
    "key": os.getenv("API_KEY"),
    "url": os.getenv("API_URL"),
    "model": os.getenv("API_MODEL", "qwen-turbo"),
    "format": os.getenv("API_FORMAT", "auto"),
}

EMAIL_CONFIG = {
    "sender": os.getenv("MAIL_SENDER"),
    "password": os.getenv("MAIL_PASSWORD"),
    "server": os.getenv("MAIL_SERVER", "smtp.qq.com"),
    "port": int(os.getenv("MAIL_PORT", "465")),
    "hr_email": os.getenv("HR_EMAIL"),
}

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8501")

INTERVIEW_CONFIG = {
    "token_expire_hours": 48,
    "module_names": ["基础知识", "项目经历", "实习经历", "技能实战", "技能进阶实战"],
    "module_weights": [0.1, 0.3, 0.3, 0.2, 0.1],
    "questions_per_module": [2, 3, 3, 2, 2],
}

TARGET_JOBS = [
    "AI大数据工程师",
    "AI算法工程师",
    "AI应用开发工程师",
    "大数据开发工程师",
    "大数据运维开发工程师",
    "数据分析师",
    "数据科学家",
    "推荐算法工程师",
]

for folder_path in (UPLOAD_FOLDER, PROCESSED_FOLDER, JD_FOLDER, LOG_ROOT):
    os.makedirs(folder_path, exist_ok=True)


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    MYSQL_HOST = MYSQL_CONFIG["host"]
    MYSQL_PORT = MYSQL_CONFIG["port"]
    MYSQL_USER = MYSQL_CONFIG["user"]
    MYSQL_PASSWORD = MYSQL_CONFIG["password"]
    MYSQL_DATABASE = MYSQL_CONFIG["database"]
    MYSQL_CHARSET = MYSQL_CONFIG["charset"]

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset={MYSQL_CHARSET}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }

    APP_BASE_URL = APP_BASE_URL


class TestingConfig(Config):
    TESTING = True
