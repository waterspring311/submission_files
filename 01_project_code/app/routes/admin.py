from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from ..models import JobPosition, ResumeRecord
from ..services.admin_service import grouped_config_items, save_system_config
from ..services.orm_repository import (
    REVIEW_STATUS_LABELS,
    dashboard_stats,
    list_jobs_for_review,
    list_resumes_for_review,
    update_job_review,
    update_resume_review,
)
from ..services.workflow_service import advance_resume_after_review

admin_bp = Blueprint("admin", __name__)


@admin_bp.get("")
def dashboard():
    return render_template(
        "admin_dashboard.html",
        stats=dashboard_stats(),
        pending_jobs=JobPosition.query.filter_by(review_status="pending").count(),
        pending_resumes=ResumeRecord.query.filter_by(review_status="pending").count(),
    )


@admin_bp.route("/config", methods=["GET", "POST"])
def config():
    if request.method == "POST":
        save_system_config(request.form, current_app)
        flash("系统配置已保存并加载到当前运行环境。", "success")
        return redirect(url_for("admin.config"))
    return render_template("admin_config.html", groups=grouped_config_items())


@admin_bp.get("/jobs")
def jobs():
    return render_template(
        "admin_jobs.html",
        jobs=list_jobs_for_review(
            status=request.args.get("status") or None,
            keyword=request.args.get("keyword") or None,
        ),
        status_labels=REVIEW_STATUS_LABELS,
        selected_status=request.args.get("status", ""),
        keyword=request.args.get("keyword", ""),
    )


@admin_bp.post("/jobs/<int:job_id>/review")
def review_job(job_id):
    job = update_job_review(job_id, request.form.get("review_status", "pending"), request.form.get("review_notes", ""))
    flash("招聘信息审核状态已更新。" if job else "招聘信息不存在。", "success" if job else "warning")
    return redirect(url_for("admin.jobs", status=request.args.get("status", ""), keyword=request.args.get("keyword", "")))


@admin_bp.get("/resumes")
def resumes():
    return render_template(
        "admin_resumes.html",
        resumes=list_resumes_for_review(
            status=request.args.get("status") or None,
            keyword=request.args.get("keyword") or None,
            job=request.args.get("job") or None,
            limit=200,
        ),
        status_labels=REVIEW_STATUS_LABELS,
        selected_status=request.args.get("status", ""),
        keyword=request.args.get("keyword", ""),
        selected_job=request.args.get("job", ""),
    )


@admin_bp.post("/resumes/<int:resume_id>/review")
def review_resume(resume_id):
    resume = update_resume_review(
        resume_id,
        request.form.get("review_status", "pending"),
        request.form.get("review_notes", ""),
    )
    workflow_result = advance_resume_after_review(resume) if resume else {"message": "简历不存在。"}
    flash(workflow_result["message"], "success" if resume else "warning")
    return redirect(url_for("admin.resumes", status=request.args.get("status", ""), keyword=request.args.get("keyword", "")))
