from datetime import datetime

from .extensions import db


class SerializerMixin:
    def to_dict(self):
        data = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if hasattr(value, "isoformat"):
                value = value.isoformat()
            data[column.name] = value
        return data


class JobPosition(db.Model, SerializerMixin):
    __tablename__ = "job_positions"

    id = db.Column(db.Integer, primary_key=True)
    job_name = db.Column(db.String(200), unique=True, nullable=False)
    jd_content = db.Column(db.Text)
    scoring_criteria = db.Column(db.Text)
    education = db.Column(db.String(100))
    city = db.Column(db.String(100))
    is_intern = db.Column(db.Integer, default=0)
    hiring_count = db.Column(db.Integer, default=1)
    is_open = db.Column(db.Integer, default=1)
    review_status = db.Column(db.String(50), default="pending")
    review_notes = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ResumeRecord(db.Model, SerializerMixin):
    __tablename__ = "resume_record"

    id = db.Column(db.Integer, primary_key=True)
    deliver_time = db.Column(db.DateTime)
    name = db.Column(db.String(100))
    gender = db.Column(db.String(20))
    age = db.Column(db.String(20))
    education = db.Column(db.String(100))
    major = db.Column(db.String(200))
    city = db.Column(db.String(100))
    target_city = db.Column(db.String(200))
    job = db.Column(db.String(200))
    score = db.Column(db.Integer)
    email = db.Column(db.String(200))
    mail_status = db.Column(db.String(50))
    result = db.Column(db.String(50))
    interview_token = db.Column(db.String(200))
    interview_link = db.Column(db.String(500))
    interview_status = db.Column(db.String(50), default="pending")
    resume_text = db.Column(db.Text)
    skills = db.Column(db.Text)
    review_status = db.Column(db.String(50), default="pending")
    review_notes = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TalentPool(db.Model, SerializerMixin):
    __tablename__ = "talent_pool"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    gender = db.Column(db.String(20))
    age = db.Column(db.String(20))
    education = db.Column(db.String(100))
    major = db.Column(db.String(200))
    city = db.Column(db.String(100))
    email = db.Column(db.String(200), unique=True)
    phone = db.Column(db.String(20))
    skills = db.Column(db.Text)
    experience = db.Column(db.Text)
    resume_text = db.Column(db.Text)
    resume_file_path = db.Column(db.String(500))
    tags = db.Column(db.Text)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(db.String(50), default="active")
    source = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InterviewRecord(db.Model, SerializerMixin):
    __tablename__ = "interview_record"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(200), unique=True, nullable=False)
    email = db.Column(db.String(200))
    candidate_name = db.Column(db.String(100))
    resume_name = db.Column(db.String(200))
    job_name = db.Column(db.String(200))
    resume_id = db.Column(db.Integer)
    status = db.Column(db.String(50), default="pending")
    questions_basic = db.Column(db.Text)
    questions_project = db.Column(db.Text)
    questions_intern = db.Column(db.Text)
    questions_practice = db.Column(db.Text)
    questions_advanced = db.Column(db.Text)
    answers = db.Column(db.Text)
    final_score = db.Column(db.Numeric(5, 2))
    scoring_details = db.Column(db.Text)
    result = db.Column(db.String(50))
    interview_duration = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expired_at = db.Column(db.DateTime)


class InterviewUrl(db.Model, SerializerMixin):
    __tablename__ = "interview_url"

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, nullable=False)
    url = db.Column(db.String(500), nullable=False)
    token = db.Column(db.String(200), nullable=False, index=True)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)
    used_at = db.Column(db.DateTime)
    destroyed_at = db.Column(db.DateTime)
    request_count = db.Column(db.Integer, default=0)
    interrupted = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HrUser(db.Model, SerializerMixin):
    __tablename__ = "hr_login"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    real_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200))
    role = db.Column(db.String(50), default="admin")
    status = db.Column(db.Integer, default=1)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HrInterviewSchedule(db.Model, SerializerMixin):
    __tablename__ = "hr_interview_schedule"

    id = db.Column(db.Integer, primary_key=True)
    talent_id = db.Column(db.Integer)
    candidate_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200))
    job_name = db.Column(db.String(200))
    interview_type = db.Column(db.String(50), default="HR面试")
    interview_date = db.Column(db.Date)
    interview_time = db.Column(db.Time)
    interview_duration = db.Column(db.Integer, default=30)
    interview_location = db.Column(db.String(500))
    interviewer = db.Column(db.String(100))
    contact_phone = db.Column(db.String(50))
    interview_notes = db.Column(db.Text)
    status = db.Column(db.String(50), default="pending")
    result = db.Column(db.String(50))
    result_notes = db.Column(db.Text)
    scheduled_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemConfig(db.Model, SerializerMixin):
    __tablename__ = "system_config"

    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False)
    config_value = db.Column(db.Text)
    config_group = db.Column(db.String(50), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    is_secret = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
