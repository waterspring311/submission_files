import json
import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename

from ..config import BASE_DIR, UPLOAD_FOLDER
from ..services.ai_scorer import handle_score
from ..services.orm_repository import (
    get_public_job_by_name,
    list_jobs,
    save_resume,
)
from ..services.resume_parser import handle_upload_and_parse

candidate_bp = Blueprint("candidate", __name__)

SESSION_DIR = Path(BASE_DIR) / "04_data" / "candidate_sessions"
SESSION_DIR.mkdir(parents=True, exist_ok=True)


def _read_text(path):
    if not path:
        return ""
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def _write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path):
    if not path:
        return {}
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


@candidate_bp.get("")
def index():
    return render_template(
        "candidate.html",
        jobs=list_jobs(open_only=True),
        parsed=session.get("candidate_parsed"),
        selected_job=session.get("candidate_job"),
        result=_read_json(session.get("candidate_result_path")),
    )


@candidate_bp.post("/upload")
def upload_resume():
    uploaded_file = request.files.get("resume")
    if not uploaded_file or not uploaded_file.filename:
        flash("请先选择简历文件。", "warning")
        return redirect(url_for("candidate.index"))

    file_bytes = uploaded_file.read()
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    filename = secure_filename(uploaded_file.filename) or "resume.txt"
    stored_name = f"{timestamp}_{filename}"
    stored_path = Path(UPLOAD_FOLDER) / stored_name
    stored_path.write_bytes(file_bytes)

    parsed = handle_upload_and_parse(file_bytes, filename)
    text_path = SESSION_DIR / f"{timestamp}_resume.txt"
    text_path.write_text(parsed.get("text", ""), encoding="utf-8")

    session["candidate_parsed"] = {key: value for key, value in parsed.items() if key != "text"}
    session["candidate_text_path"] = str(text_path)
    session["candidate_resume_file_path"] = os.path.join("01_resume_inbox", stored_name)
    session.pop("candidate_result_path", None)
    flash("简历已上传并解析完成。", "success")
    return redirect(url_for("candidate.index"))


@candidate_bp.post("/select-job")
def select_job():
    job_name = request.form.get("job_name", "")
    if not job_name:
        flash("请选择岗位。", "warning")
    elif not get_public_job_by_name(job_name):
        flash("该岗位暂未开放或仍在审核中，请重新选择。", "warning")
    else:
        session["candidate_job"] = job_name
        session.pop("candidate_result_path", None)
        flash(f"已选择岗位：{job_name}", "success")
    return redirect(url_for("candidate.index"))


@candidate_bp.post("/score")
def score_resume():
    parsed = session.get("candidate_parsed") or {}
    job_name = request.form.get("job_name") or session.get("candidate_job")
    resume_text = _read_text(session.get("candidate_text_path"))
    if not parsed or not resume_text:
        flash("请先上传并解析简历。", "warning")
        return redirect(url_for("candidate.index"))
    if not job_name:
        flash("请先选择岗位。", "warning")
        return redirect(url_for("candidate.index"))
    job = get_public_job_by_name(job_name)
    if not job:
        flash("该岗位暂未开放或仍在审核中，请重新选择。", "warning")
        session.pop("candidate_job", None)
        return redirect(url_for("candidate.index"))

    session["candidate_job"] = job_name
    result = handle_score(job_name, resume_text, job.jd_content, job.scoring_criteria)
    result_path = SESSION_DIR / f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_score.json"
    _write_json(result_path, result)
    session["candidate_result_path"] = str(result_path)
    flash("AI匹配评分已完成。", "success")
    return redirect(url_for("candidate.index"))


@candidate_bp.post("/submit")
def submit_application():
    parsed = session.get("candidate_parsed") or {}
    result = _read_json(session.get("candidate_result_path"))
    resume_text = _read_text(session.get("candidate_text_path"))
    job_name = session.get("candidate_job")

    if not parsed or not result or not resume_text or not job_name:
        flash("请先完成简历上传、岗位选择和AI评分。", "warning")
        return redirect(url_for("candidate.index"))
    if not get_public_job_by_name(job_name):
        flash("该岗位暂未开放或仍在审核中，请重新选择后再投递。", "warning")
        session.pop("candidate_job", None)
        return redirect(url_for("candidate.index"))

    score = int(result.get("score") or 0)
    apply_result = "初筛通过" if score >= 70 else "初筛未通过"
    email = parsed.get("email", "")

    resume = save_resume(
        {
            **parsed,
            "job": job_name,
            "score": score,
            "result": apply_result,
            "mail_status": "待管理员审核",
            "resume_text": resume_text,
            "skills": parsed.get("skills", ""),
            "review_status": "pending",
            "interview_status": "pending_review",
        }
    )

    flash(f"投递记录已提交。AI初筛结果：{apply_result}，等待管理员审核后推进后续流程。", "success")
    return render_template(
        "candidate_result.html",
        resume=resume,
        result=result,
        apply_result=apply_result,
        mail_status=resume.mail_status,
        interview_link="",
    )
