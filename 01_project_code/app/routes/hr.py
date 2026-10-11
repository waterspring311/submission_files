from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..services.email_service import send_hr_interview_invitation_email, send_offer_email
from ..services.orm_repository import (
    get_talent,
    list_hr_interviews,
    list_jobs,
    list_talents,
    schedule_hr_interview,
    update_hr_interview_result,
    update_hr_interview_status,
    update_talent_status,
)
from ..services.reporting import build_daily_report
from .responses import created

hr_bp = Blueprint("hr", __name__)


@hr_bp.route("/login", methods=["GET", "POST"])
def login():
    return redirect(url_for("auth.login"))


@hr_bp.route("/daily-report", methods=["GET", "POST"])
def daily_report():
    label = request.form.get("range") or request.args.get("range") or "今日"
    use_ai = request.method == "POST" and request.form.get("use_ai") == "1"
    report, ai_success = build_daily_report(label, use_ai=use_ai)
    if request.method == "POST":
        flash("日报已生成。" if ai_success or not use_ai else "AI不可用，已生成本地日报。", "success")
    return render_template("daily_report.html", report=report, selected_range=label, ai_success=ai_success)


@hr_bp.get("/interviews")
def hr_interviews():
    return render_template(
        "hr_interviews.html",
        interviews=list_hr_interviews(status=request.args.get("status") or None),
        talents=list_talents(limit=200),
        jobs=list_jobs(open_only=True),
        selected_status=request.args.get("status", ""),
    )


@hr_bp.post("/interviews")
def create_hr_interview():
    data = request.get_json(silent=True)
    interview = schedule_hr_interview(data or request.form)
    if request.form.get("send_mail") == "1":
        send_hr_interview_invitation_email(
            email=interview.email,
            candidate_name=interview.candidate_name,
            job_name=interview.job_name,
            interview_date=str(interview.interview_date),
            interview_time=str(interview.interview_time),
            interview_location=interview.interview_location or "",
            interviewer=interview.interviewer or "",
            interview_notes=interview.interview_notes or "",
        )
    if data is not None:
        return created(interview=interview.to_dict())
    flash("HR面试已安排。", "success")
    return redirect(url_for("hr.hr_interviews"))


@hr_bp.post("/interviews/<int:interview_id>/status")
def change_hr_interview_status(interview_id):
    interview = update_hr_interview_status(interview_id, request.form.get("status", "pending"))
    flash("面试状态已更新。" if interview else "面试不存在。", "success" if interview else "warning")
    return redirect(url_for("hr.hr_interviews"))


@hr_bp.post("/interviews/<int:interview_id>/result")
def save_hr_interview_result(interview_id):
    interview = update_hr_interview_result(
        interview_id,
        request.form.get("result", ""),
        request.form.get("result_notes", ""),
    )
    flash("面试结果已保存。" if interview else "面试不存在。", "success" if interview else "warning")
    return redirect(url_for("hr.hr_interviews"))


@hr_bp.route("/offers", methods=["GET", "POST"])
def offers():
    if request.method == "POST":
        talent_id = request.form.get("talent_id")
        talent = get_talent(talent_id) if talent_id else None
        success = send_offer_email(
            email=request.form.get("email") or (talent.email if talent else ""),
            candidate_name=request.form.get("candidate_name") or (talent.name if talent else ""),
            job_name=request.form.get("job_name") or (talent.tags if talent else ""),
            salary=request.form.get("salary") or "面议",
            start_date=request.form.get("start_date") or "待定",
            benefits=request.form.get("benefits") or "标准福利",
        )
        if success and talent_id:
            update_talent_status(talent_id, "hired")
        flash("录用通知已发送。" if success else "录用通知发送失败，请检查邮箱配置。", "success" if success else "warning")
        return redirect(url_for("hr.offers"))

    talents = list_talents(limit=200)
    offer_candidates = [talent for talent in talents if talent.status in ("offer_pending", "拟录取")]
    return render_template("offers.html", talents=offer_candidates, jobs=list_jobs(open_only=True))
