from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from ..services.auth_service import authenticate_user, home_endpoint_for_role

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or request.form.get("next") or ""
    if request.method == "GET":
        if session.get("user"):
            return redirect(url_for(home_endpoint_for_role(session["user"]["role"])))
        return render_template("login.html", next_url=next_url)

    result = authenticate_user(
        request.form.get("username"),
        request.form.get("password"),
        request.form.get("role"),
    )
    if not result.ok:
        return render_template("login.html", error=result.error, next_url=next_url), 401

    session.clear()
    session["user"] = result.user
    flash(f"欢迎，{result.user['display_name']}。", "success")
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect(url_for(home_endpoint_for_role(result.user["role"])))


@auth_bp.get("/logout")
def logout():
    session.clear()
    flash("已退出登录。", "success")
    return redirect(url_for("auth.login"))
