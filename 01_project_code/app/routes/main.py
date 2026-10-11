from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..extensions import db
from ..services.orm_repository import (
    dashboard_stats,
    delete_job,
    delete_talent,
    get_job,
    get_resume,
    list_jobs,
    list_resumes,
    list_talents,
    recommend_talents_for_job,
    save_job,
    save_resume,
    save_talent,
    toggle_job_status,
    update_talent_status,
)
from .responses import created, fail, ok

main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def index():
    return render_template(
        "dashboard.html",
        stats=dashboard_stats(),
        jobs=list_jobs(open_only=True)[:5],
        resumes=list_resumes(limit=5),
    )


@main_bp.get("/health")
def health():
    db.session.execute(db.text("SELECT 1"))
    return ok(database="ok")


@main_bp.get("/jobs")
def jobs():
    edit_job = get_job(request.args.get("edit")) if request.args.get("edit") else None
    return render_template(
        "jobs.html",
        jobs=list_jobs(open_only=False, keyword=request.args.get("keyword")),
        edit_job=edit_job,
        keyword=request.args.get("keyword", ""),
    )


@main_bp.post("/jobs")
def create_or_update_job():
    job_id = request.form.get("job_id")
    job = get_job(job_id) if job_id else None
    saved_job = save_job(request.form, job=job)
    if saved_job.review_status == "pending":
        flash("岗位已保存，并提交管理员审核。审核通过后会展示给求职者。", "success")
    else:
        flash("岗位已保存。", "success")
    return redirect(url_for("main.jobs"))


@main_bp.post("/jobs/<int:job_id>/status")
def change_job_status(job_id):
    job = toggle_job_status(job_id)
    flash("岗位状态已更新。" if job else "岗位不存在。", "success" if job else "warning")
    return redirect(url_for("main.jobs"))


@main_bp.post("/jobs/<int:job_id>/delete")
def remove_job(job_id):
    deleted = delete_job(job_id)
    flash("岗位已删除。" if deleted else "岗位不存在。", "success" if deleted else "warning")
    return redirect(url_for("main.jobs"))


@main_bp.get("/api/jobs")
def api_jobs():
    return ok(jobs=[job.to_dict() for job in list_jobs(open_only=True)])


@main_bp.get("/resumes")
def resumes():
    return render_template(
        "resumes.html",
        resumes=list_resumes(keyword=request.args.get("keyword"), job=request.args.get("job")),
        jobs=list_jobs(open_only=False),
        keyword=request.args.get("keyword", ""),
        selected_job=request.args.get("job", ""),
    )


@main_bp.post("/resumes")
def create_resume():
    resume = save_resume(request.get_json(silent=True) or request.form)
    return created(resume=resume.to_dict())


@main_bp.get("/resumes/<int:resume_id>")
def resume_detail(resume_id):
    resume = get_resume(resume_id)
    if not resume:
        return fail("resume not found", status=404)
    if request.args.get("format") == "json":
        return ok(resume=resume.to_dict())
    return render_template("resume_detail.html", resume=resume)


@main_bp.get("/talents")
def talents():
    recommend_job = request.args.get("recommend_job", "")
    if recommend_job:
        talent_list = recommend_talents_for_job(recommend_job, limit=20)
    else:
        talent_list = list_talents(
            status=request.args.get("status") or None,
            keyword=request.args.get("keyword") or None,
            education=request.args.get("education") or None,
            city=request.args.get("city") or None,
        )
    return render_template(
        "talents.html",
        talents=talent_list,
        jobs=list_jobs(open_only=True),
        filters=request.args,
        recommend_job=recommend_job,
    )


@main_bp.post("/talents")
def create_talent():
    data = request.get_json(silent=True)
    talent = save_talent(data or request.form)
    if data is not None:
        return created(talent=talent.to_dict())
    flash("人才信息已保存。", "success")
    return redirect(url_for("main.talents"))


@main_bp.post("/talents/<int:talent_id>/status")
def change_talent_status(talent_id):
    status = request.form.get("status", "active")
    talent = update_talent_status(talent_id, status)
    flash("人才状态已更新。" if talent else "人才不存在。", "success" if talent else "warning")
    return redirect(url_for("main.talents"))


@main_bp.post("/talents/<int:talent_id>/delete")
def remove_talent(talent_id):
    deleted = delete_talent(talent_id)
    flash("人才已删除。" if deleted else "人才不存在。", "success" if deleted else "warning")
    return redirect(url_for("main.talents"))


@main_bp.get("/api/talents")
def api_talents():
    return ok(talents=[talent.to_dict() for talent in list_talents(status=request.args.get("status"))])
