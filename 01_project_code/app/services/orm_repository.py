import json
from datetime import datetime
from hashlib import sha256

from ..extensions import db
from ..models import (
    HrInterviewSchedule,
    HrUser,
    InterviewRecord,
    InterviewUrl,
    JobPosition,
    ResumeRecord,
    TalentPool,
)
from .common import first_present, parse_date, parse_datetime, parse_time
from .interview_engine import score_answers
from .interview_links import build_interview_link, create_interview_token, get_interview_expired_at


REVIEW_STATUS_LABELS = {
    "pending": "待审核",
    "approved": "已通过",
    "rejected": "已驳回",
}


def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _form_dict(data):
    return data.to_dict(flat=True) if hasattr(data, "to_dict") else dict(data or {})


def dashboard_stats():
    return {
        "jobs": JobPosition.query.count(),
        "open_jobs": JobPosition.query.filter_by(is_open=1, review_status="approved").count(),
        "resumes": ResumeRecord.query.count(),
        "talents": TalentPool.query.count(),
        "active_talents": TalentPool.query.filter_by(status="active").count(),
        "interviews": InterviewRecord.query.count(),
        "hr_interviews": HrInterviewSchedule.query.count(),
    }


def list_jobs(open_only=False, keyword=None):
    query = JobPosition.query
    if open_only:
        query = query.filter_by(is_open=1, review_status="approved")
    if keyword:
        query = query.filter(JobPosition.job_name.ilike(f"%{keyword}%"))
    return query.order_by(JobPosition.created_at.desc()).all()


def list_jobs_for_review(status=None, keyword=None):
    query = JobPosition.query
    if status:
        query = query.filter_by(review_status=status)
    if keyword:
        query = query.filter(JobPosition.job_name.ilike(f"%{keyword}%"))
    return query.order_by(JobPosition.updated_at.desc(), JobPosition.created_at.desc()).all()


def get_job(job_id):
    return db.session.get(JobPosition, job_id)


def get_job_by_name(job_name):
    if not job_name:
        return None
    return JobPosition.query.filter_by(job_name=job_name).first()


def get_public_job_by_name(job_name):
    if not job_name:
        return None
    return JobPosition.query.filter_by(job_name=job_name, is_open=1, review_status="approved").first()


def save_job(data, job=None):
    data = _form_dict(data)
    is_new = job is None or job.id is None
    job = job or JobPosition()
    was_approved = not is_new and job.review_status == "approved"
    original = {
        "job_name": job.job_name or "",
        "jd_content": job.jd_content or "",
        "scoring_criteria": job.scoring_criteria or "",
        "education": job.education or "",
        "city": job.city or "",
        "is_intern": job.is_intern or 0,
        "hiring_count": job.hiring_count or 1,
    }
    job.job_name = data.get("job_name", job.job_name or "")
    job.jd_content = data.get("jd_content", job.jd_content or "")
    job.scoring_criteria = data.get("scoring_criteria", job.scoring_criteria or "")
    job.education = data.get("education", job.education or "")
    job.city = data.get("city", job.city or "")
    job.is_intern = 1 if data.get("is_intern") in ("1", "true", "on", 1, True) else 0
    job.hiring_count = _to_int(data.get("hiring_count"), job.hiring_count or 1)
    job.is_open = 1 if data.get("is_open", job.is_open if job.id else 1) in ("1", "true", "on", 1, True) else 0
    if is_new and not job.review_status:
        job.review_status = data.get("review_status") or "pending"
    if was_approved:
        changed = (
            original["job_name"] != (job.job_name or "")
            or original["jd_content"] != (job.jd_content or "")
            or original["scoring_criteria"] != (job.scoring_criteria or "")
            or original["education"] != (job.education or "")
            or original["city"] != (job.city or "")
            or original["is_intern"] != (job.is_intern or 0)
            or original["hiring_count"] != (job.hiring_count or 1)
        )
        if changed:
            job.review_status = "pending"
            job.review_notes = "岗位核心信息已修改，需重新审核后再对求职者开放。"
            job.reviewed_at = None
    db.session.add(job)
    db.session.commit()
    return job


def update_job_review(job_id, status, notes=""):
    job = get_job(job_id)
    if not job:
        return None
    job.review_status = status if status in REVIEW_STATUS_LABELS else "pending"
    job.review_notes = notes or ""
    job.reviewed_at = datetime.utcnow()
    db.session.commit()
    return job


def toggle_job_status(job_id):
    job = get_job(job_id)
    if not job:
        return None
    job.is_open = 0 if job.is_open else 1
    db.session.commit()
    return job


def delete_job(job_id):
    job = get_job(job_id)
    if not job:
        return False
    db.session.delete(job)
    db.session.commit()
    return True


def get_jd_content(job_name):
    job = get_job_by_name(job_name)
    return job.jd_content if job else ""


def get_scoring_criteria(job_name):
    job = get_job_by_name(job_name)
    return job.scoring_criteria if job else ""


def list_resumes(limit=50, keyword=None, job=None):
    query = ResumeRecord.query
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((ResumeRecord.name.ilike(like)) | (ResumeRecord.email.ilike(like)))
    if job:
        query = query.filter_by(job=job)
    query = query.order_by(ResumeRecord.created_at.desc())
    return query.limit(limit).all() if limit else query.all()


def list_resumes_for_review(status=None, keyword=None, job=None, limit=100):
    query = ResumeRecord.query
    if status:
        query = query.filter_by(review_status=status)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter((ResumeRecord.name.ilike(like)) | (ResumeRecord.email.ilike(like)))
    if job:
        query = query.filter_by(job=job)
    return query.order_by(ResumeRecord.created_at.desc()).limit(limit).all()


def get_resume(resume_id):
    return db.session.get(ResumeRecord, resume_id)


def save_resume(data):
    data = _form_dict(data)
    resume = ResumeRecord(
        deliver_time=parse_datetime(first_present(data, "deliver_time", "投递时间")),
        name=first_present(data, "name", "姓名", default=""),
        gender=first_present(data, "gender", "性别", default=""),
        age=str(first_present(data, "age", "年龄", default="")),
        education=first_present(data, "education", "学历", default=""),
        major=first_present(data, "major", "专业", default=""),
        city=first_present(data, "city", "所在城市", default=""),
        target_city=first_present(data, "target_city", "意向地区", default=""),
        job=first_present(data, "job", "岗位", default=""),
        score=_to_int(first_present(data, "score", "得分", default=0)),
        email=first_present(data, "email", "邮箱", default=""),
        mail_status=first_present(data, "mail_status", "邮件状态", default="pending"),
        result=first_present(data, "result", "测评结果", default="pending"),
        interview_status=first_present(data, "interview_status", "面试状态", default="pending_review"),
        interview_token=first_present(data, "interview_token", "面试Token"),
        interview_link=first_present(data, "interview_link", "面试链接"),
        resume_text=first_present(data, "resume_text", "简历文本", default=""),
        skills=first_present(data, "skills", "技能", default=""),
        review_status=first_present(data, "review_status", "审核状态", default="pending"),
    )
    db.session.add(resume)
    db.session.commit()
    return resume


def update_resume_review(resume_id, status, notes=""):
    resume = get_resume(resume_id)
    if not resume:
        return None
    resume.review_status = status if status in REVIEW_STATUS_LABELS else "pending"
    resume.review_notes = notes or ""
    resume.reviewed_at = datetime.utcnow()
    db.session.commit()
    return resume


def list_talents(status=None, keyword=None, education=None, city=None, limit=100):
    query = TalentPool.query
    if status:
        query = query.filter_by(status=status)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (TalentPool.name.ilike(like))
            | (TalentPool.email.ilike(like))
            | (TalentPool.skills.ilike(like))
            | (TalentPool.tags.ilike(like))
        )
    if education:
        query = query.filter(TalentPool.education.ilike(f"%{education}%"))
    if city:
        query = query.filter(TalentPool.city.ilike(f"%{city}%"))
    return query.order_by(TalentPool.last_updated.desc()).limit(limit).all()


def get_talent(talent_id):
    return db.session.get(TalentPool, talent_id)


def save_talent(data):
    data = _form_dict(data)
    email = first_present(data, "email", "邮箱")
    talent = TalentPool.query.filter_by(email=email).first() if email else None
    if talent is None:
        talent = TalentPool()
        db.session.add(talent)

    field_map = {
        "name": ("name", "姓名"),
        "gender": ("gender", "性别"),
        "age": ("age", "年龄"),
        "education": ("education", "学历"),
        "major": ("major", "专业"),
        "city": ("city", "所在城市"),
        "email": ("email", "邮箱"),
        "phone": ("phone", "电话"),
        "skills": ("skills", "技能"),
        "experience": ("experience", "经验"),
        "resume_text": ("resume_text", "简历文本"),
        "resume_file_path": ("resume_file_path", "简历路径"),
        "tags": ("tags", "岗位"),
        "status": ("status", "状态"),
        "source": ("source", "来源"),
    }
    for field, keys in field_map.items():
        value = first_present(data, *keys)
        if value is not None:
            setattr(talent, field, value)

    talent.status = talent.status or "active"
    talent.source = talent.source or "简历投递"
    db.session.commit()
    return talent


def update_talent_status(talent_id, status):
    talent = get_talent(talent_id)
    if not talent:
        return None
    talent.status = status
    talent.last_updated = datetime.utcnow()
    db.session.commit()
    return talent


def delete_talent(talent_id):
    talent = get_talent(talent_id)
    if not talent:
        return False
    db.session.delete(talent)
    db.session.commit()
    return True


def recommend_talents_for_job(job_name, limit=5):
    talents = list_talents(status="active", limit=200)
    scored = []
    for talent in talents:
        text = " ".join(
            str(value or "")
            for value in (talent.tags, talent.skills, talent.major, talent.experience, talent.resume_text)
        )
        score = 0
        for term in job_name.replace("（", " ").replace("）", " ").replace("/", " ").split():
            if term and term in text:
                score += 2
        if job_name and job_name in text:
            score += 5
        scored.append((score, talent))
    scored.sort(key=lambda item: (item[0], item[1].last_updated or item[1].created_at), reverse=True)
    return [talent for _, talent in scored[:limit]]


def verify_hr_login(username, password):
    password_hash = sha256(password.encode("utf-8")).hexdigest()
    user = HrUser.query.filter_by(username=username, password=password_hash, status=1).first()
    if user:
        user.last_login = datetime.utcnow()
        db.session.commit()
    return user


def list_hr_interviews(status=None, limit=100):
    query = HrInterviewSchedule.query
    if status:
        query = query.filter_by(status=status)
    return query.order_by(HrInterviewSchedule.created_at.desc()).limit(limit).all()


def get_hr_interview(interview_id):
    return db.session.get(HrInterviewSchedule, interview_id)


def schedule_hr_interview(data):
    data = _form_dict(data)
    interview = HrInterviewSchedule(
        talent_id=data.get("talent_id") or None,
        candidate_name=data.get("candidate_name", ""),
        email=data.get("email"),
        job_name=data.get("job_name"),
        interview_type=data.get("interview_type", "HR面试"),
        interview_date=parse_date(data.get("interview_date")),
        interview_time=parse_time(data.get("interview_time")),
        interview_duration=_to_int(data.get("interview_duration"), 30),
        interview_location=data.get("interview_location"),
        interviewer=data.get("interviewer"),
        contact_phone=data.get("contact_phone"),
        interview_notes=data.get("interview_notes"),
        status=data.get("status", "pending"),
        scheduled_by=data.get("scheduled_by"),
    )
    db.session.add(interview)
    if interview.talent_id:
        talent = db.session.get(TalentPool, interview.talent_id)
        if talent:
            talent.status = "hr_scheduled"
            talent.last_updated = datetime.utcnow()
    db.session.commit()
    return interview


def update_hr_interview_status(interview_id, status):
    interview = get_hr_interview(interview_id)
    if not interview:
        return None
    interview.status = status
    db.session.commit()
    return interview


def update_hr_interview_result(interview_id, result, result_notes=""):
    interview = get_hr_interview(interview_id)
    if not interview:
        return None
    interview.result = result
    interview.result_notes = result_notes
    interview.status = "completed"
    if interview.talent_id:
        talent = db.session.get(TalentPool, interview.talent_id)
        if talent:
            result_text = (result or "").lower()
            if any(term in result_text for term in ("通过", "录用", "offer", "拟录取", "pass", "passed")):
                talent.status = "offer_pending"
            elif any(term in result_text for term in ("不通过", "淘汰", "拒绝")):
                talent.status = "archived"
            elif "暂缓" in result_text:
                talent.status = "hr_hold"
            else:
                talent.status = "hr_completed"
            talent.last_updated = datetime.utcnow()
    db.session.commit()
    return interview


def list_interview_records(status=None, limit=100):
    query = InterviewRecord.query
    if status:
        query = query.filter_by(status=status)
    return query.order_by(InterviewRecord.created_at.desc()).limit(limit).all()


def create_interview_link_record(data):
    data = _form_dict(data)
    token = create_interview_token(
        data.get("email"),
        data.get("resume_name", ""),
        data.get("job_name", ""),
    )
    record = InterviewRecord(
        token=token,
        email=data.get("email"),
        candidate_name=data.get("candidate_name", ""),
        resume_name=data.get("resume_name", ""),
        job_name=data.get("job_name", ""),
        resume_id=data.get("resume_id") or None,
        status="pending",
        expired_at=get_interview_expired_at(),
    )
    db.session.add(record)
    db.session.flush()

    link = build_interview_link(token)
    url_record = None
    if data.get("resume_id"):
        resume = db.session.get(ResumeRecord, data.get("resume_id"))
        if resume:
            resume.interview_token = token
            resume.interview_link = link
            resume.interview_status = "ai_pending"
        url_record = InterviewUrl(resume_id=data.get("resume_id"), url=link, token=token)
        db.session.add(url_record)

    db.session.commit()
    return link, record, url_record


def get_interview_url(token):
    return InterviewUrl.query.filter_by(token=token).first()


def get_interview_record(token):
    return InterviewRecord.query.filter_by(token=token).first()


def touch_interview_url(token):
    url_record = get_interview_url(token)
    if not url_record:
        return False, 0
    if url_record.destroyed_at:
        return True, url_record.request_count or 0
    url_record.request_count = (url_record.request_count or 0) + 1
    if url_record.used_at is None:
        url_record.used_at = datetime.utcnow()
    interrupted = url_record.request_count > 3
    if interrupted:
        url_record.interrupted = 1
        url_record.destroyed_at = datetime.utcnow()
    db.session.commit()
    return interrupted, url_record.request_count


def verify_interview_access(token):
    record = get_interview_record(token)
    if not record:
        return False, None, "面试记录不存在"
    url_record = get_interview_url(token)
    if url_record and url_record.destroyed_at:
        return False, record, "面试链接已失效"
    if record.expired_at and record.expired_at < datetime.utcnow():
        record.status = "expired"
        db.session.commit()
        return False, record, "面试链接已过期"
    if record.status == "completed":
        return False, record, "面试已完成"
    return True, record, "ok"


def update_interview_status(token, status):
    record = get_interview_record(token)
    if not record:
        return None
    record.status = status
    record.updated_at = datetime.utcnow()
    db.session.commit()
    return record


def save_module_questions(token, module_name, questions):
    record = get_interview_record(token)
    if not record:
        return None
    field_map = {
        "基础知识": "questions_basic",
        "项目经历": "questions_project",
        "实习经历": "questions_intern",
        "技能实战": "questions_practice",
        "技能进阶实战": "questions_advanced",
    }
    field_name = field_map.get(module_name)
    if field_name:
        setattr(record, field_name, json.dumps(questions, ensure_ascii=False))
        db.session.commit()
    return record


def complete_interview(token, answers):
    record = get_interview_record(token)
    if not record:
        return None
    scores, total, result = score_answers(answers)
    record.answers = json.dumps(answers, ensure_ascii=False)
    record.final_score = total
    record.scoring_details = json.dumps(scores, ensure_ascii=False)
    record.result = result
    record.status = "completed"
    record.updated_at = datetime.utcnow()
    if record.resume_id:
        resume = db.session.get(ResumeRecord, record.resume_id)
        if resume:
            resume.interview_status = "ai_completed"
    if record.email:
        talent = TalentPool.query.filter_by(email=record.email).first()
        if talent:
            talent.status = "hr_pending" if result == "建议进入复试" else "ai_hold"
            talent.last_updated = datetime.utcnow()
    db.session.commit()
    return record
