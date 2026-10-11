import json
from pathlib import Path

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..config import BASE_DIR
from ..services.interview_engine import MODULE_NAMES, generate_questions_for_module
from ..services.orm_repository import (
    complete_interview,
    create_interview_link_record,
    get_interview_record,
    get_interview_url,
    get_jd_content,
    get_resume,
    list_interview_records,
    save_module_questions,
    touch_interview_url,
    update_interview_status,
    verify_interview_access,
)
from .responses import created, fail, ok

interview_bp = Blueprint("interviews", __name__)
INTERVIEW_SESSION_DIR = Path(BASE_DIR) / "04_data" / "interview_sessions"
INTERVIEW_SESSION_DIR.mkdir(parents=True, exist_ok=True)


@interview_bp.get("")
def records():
    return render_template(
        "interviews.html",
        interviews=list_interview_records(status=request.args.get("status") or None),
        selected_status=request.args.get("status", ""),
    )


@interview_bp.post("/links")
def create_link():
    data = request.get_json(silent=True) or request.form
    resume_id = data.get("resume_id") if data else None
    resume = get_resume(resume_id) if resume_id else None
    if not resume or resume.review_status != "approved" or resume.result != "初筛通过":
        message = "AI面试链接只能从审核通过且初筛通过的简历生成。"
        if request.form:
            flash(message, "warning")
            return redirect(url_for("interviews.records"))
        return fail(message, status=400)
    link, record, url_record = create_interview_link_record(data)
    if request.form:
        flash("AI面试链接已生成。", "success")
        return redirect(url_for("interviews.records"))
    return created(
        interview_id=record.id,
        token=record.token,
        url_id=url_record.id if url_record else None,
        link=link,
    )


@interview_bp.get("/links/<token>")
def get_link(token):
    record = get_interview_url(token)
    if not record:
        return fail("interview url not found", status=404)
    return ok(url=record.to_dict())


def _state_key(token):
    return INTERVIEW_SESSION_DIR / f"{token}.json"


def _visit_key(token):
    return f"interview_seen_{token}"


def _get_state(token):
    path = _state_key(token)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "started": False,
        "module_index": 0,
        "current_questions": [],
        "module_answers": [],
        "answers": [],
    }


def _save_state(token, state):
    _state_key(token).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _clear_state(token):
    try:
        _state_key(token).unlink()
    except OSError:
        pass


@interview_bp.route("/take/<token>", methods=["GET", "POST"])
def take_interview(token):
    if not session.get(_visit_key(token)):
        interrupted, request_count = touch_interview_url(token)
        session[_visit_key(token)] = True
        session.modified = True
    else:
        url_record = get_interview_url(token)
        interrupted = bool(url_record and url_record.destroyed_at)
        request_count = url_record.request_count if url_record else 0

    is_valid, record, message = verify_interview_access(token)
    if interrupted:
        is_valid = False
        message = "面试链接访问次数超过限制，已失效"

    if not is_valid:
        return render_template("interview_take.html", record=record, error=message, request_count=request_count)

    state = _get_state(token)
    action = request.form.get("action")

    if request.method == "POST" and action == "start":
        state = {"started": True, "module_index": 0, "current_questions": [], "module_answers": [], "answers": []}
        update_interview_status(token, "进行中")
        _save_state(token, state)
        return redirect(url_for("interviews.take_interview", token=token))

    current_module = None
    current_question = None
    completed = state.get("module_index", 0) >= len(MODULE_NAMES)

    if state.get("started") and not completed:
        current_module = MODULE_NAMES[state["module_index"]]
        if not state.get("current_questions"):
            resume = get_resume(record.resume_id) if record.resume_id else None
            questions = generate_questions_for_module(
                current_module,
                resume.resume_text if resume else "",
                get_jd_content(record.job_name),
            )
            state["current_questions"] = questions
            state["module_answers"] = []
            save_module_questions(token, current_module, questions)

        answer_index = len(state.get("module_answers", []))
        questions = state.get("current_questions", [])
        current_question = questions[answer_index] if answer_index < len(questions) else None

        if request.method == "POST" and action == "answer":
            answer_text = request.form.get("answer", "").strip()
            if not answer_text:
                flash("请填写回答后再提交。", "warning")
            elif current_question:
                state["module_answers"].append(
                    {
                        "module": current_module,
                        "question": current_question.get("question"),
                        "reference_answer": current_question.get("reference_answer", ""),
                        "scoring_points": current_question.get("scoring_points", []),
                        "answer": answer_text,
                    }
                )
                if len(state["module_answers"]) >= len(questions):
                    state["answers"].extend(state["module_answers"])
                    state["module_index"] += 1
                    state["current_questions"] = []
                    state["module_answers"] = []
                _save_state(token, state)
                return redirect(url_for("interviews.take_interview", token=token))

    completed = state.get("module_index", 0) >= len(MODULE_NAMES)
    if request.method == "POST" and action == "submit" and completed:
        record = complete_interview(token, state.get("answers", []))
        _clear_state(token)
        flash("面试答案已提交。", "success")
        return render_template("interview_take.html", record=record, submitted=True, request_count=request_count)

    _save_state(token, state)
    return render_template(
        "interview_take.html",
        record=record,
        state=state,
        modules=MODULE_NAMES,
        current_module=current_module,
        current_question=current_question,
        completed=completed,
        request_count=request_count,
    )
