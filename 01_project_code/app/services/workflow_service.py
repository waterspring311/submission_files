from ..config import EMAIL_CONFIG
from ..extensions import db
from ..models import TalentPool
from .email_service import send_interview_invitation_email
from .orm_repository import create_interview_link_record, save_talent


INITIAL_SCREEN_PASS = "初筛通过"


def _candidate_name(resume):
    if resume.name:
        return resume.name
    if resume.email and "@" in resume.email:
        return resume.email.split("@")[0]
    return "未知候选人"


def _email_ready():
    return bool(EMAIL_CONFIG.get("sender") and EMAIL_CONFIG.get("password") and EMAIL_CONFIG.get("server"))


def _talent_payload_from_resume(resume, status):
    return {
        "name": resume.name,
        "gender": resume.gender,
        "age": resume.age,
        "education": resume.education,
        "major": resume.major,
        "city": resume.city,
        "email": resume.email or None,
        "skills": resume.skills,
        "resume_text": resume.resume_text,
        "tags": resume.job,
        "source": "管理员审核通过",
        "status": status,
    }


def _set_existing_talent_status(email, status):
    if not email:
        return None
    talent = TalentPool.query.filter_by(email=email).first()
    if not talent:
        return None
    talent.status = status
    return talent


def advance_resume_after_review(resume):
    result = {
        "link_created": False,
        "talent_synced": False,
        "mail_sent": False,
        "message": "审核状态已更新。",
    }
    if not resume:
        result["message"] = "简历不存在。"
        return result

    if resume.review_status == "rejected":
        resume.interview_status = "review_rejected"
        resume.mail_status = "审核未通过"
        _set_existing_talent_status(resume.email, "archived")
        db.session.commit()
        result["message"] = "简历已驳回，后续面试流程不会推进。"
        return result

    if resume.review_status != "approved":
        resume.interview_status = resume.interview_status or "pending_review"
        resume.mail_status = resume.mail_status or "待管理员审核"
        db.session.commit()
        return result

    talent_status = "ai_pending" if resume.result == INITIAL_SCREEN_PASS else "screen_failed"
    save_talent(_talent_payload_from_resume(resume, talent_status))
    result["talent_synced"] = True

    if resume.result != INITIAL_SCREEN_PASS:
        resume.interview_status = "no_ai_interview"
        resume.mail_status = "审核通过，初筛未通过"
        db.session.commit()
        result["message"] = "简历已审核通过并同步到人才库，但未达到AI面试触发分。"
        return result

    link = resume.interview_link
    if not link:
        link, _, _ = create_interview_link_record(
            {
                "resume_id": resume.id,
                "candidate_name": _candidate_name(resume),
                "email": resume.email,
                "resume_name": f"resume_{resume.id}",
                "job_name": resume.job,
            }
        )
        result["link_created"] = True

    resume.interview_status = "ai_pending"
    if resume.email and _email_ready():
        result["mail_sent"] = send_interview_invitation_email(resume.email, _candidate_name(resume), link)
        resume.mail_status = "面试邀请已发送" if result["mail_sent"] else "面试邀请发送失败"
    else:
        resume.mail_status = "面试邀请待人工发送"
    db.session.commit()
    result["message"] = "简历已审核通过，已同步人才库并生成AI面试链接。"
    return result
