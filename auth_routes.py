from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re
import time

from flask import current_app, flash, g, redirect, render_template, request, session, url_for


RESET_PENDING_KEY = "pw_reset_state"
RESET_TTL_SECONDS = 300


def normalize_mobile(raw_mobile: str | None) -> str | None:
    digits = re.sub(r"\D+", "", raw_mobile or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if re.fullmatch(r"[6-9]\d{9}", digits or ""):
        return digits
    return None


def _session_now() -> int:
    return int(time.time())


@dataclass
class APIResult:
    ok: bool
    reason: str | None = None
    message: str = ""
    payload: Any = None


def clear_reset_password_state() -> None:
    session.pop(RESET_PENDING_KEY, None)


def get_reset_password_state() -> dict[str, Any] | None:
    state = session.get(RESET_PENDING_KEY)
    if not isinstance(state, dict):
        return None
    created_at = int(state.get("created_at") or 0)
    now_ts = _session_now()
    if created_at <= 0 or now_ts - created_at > RESET_TTL_SECONDS:
        clear_reset_password_state()
        return None
    return dict(state)


def begin_reset_password(user: dict[str, Any]) -> dict[str, Any]:
    state = {
        "created_at": _session_now(),
        "user_id": int(user["id"]),
        "username": user.get("username") or "",
    }
    session[RESET_PENDING_KEY] = state
    return state


def _set_auth_invalid_reason(reason: str, *, username: str | None = None, user_id: Any = None, flow: str | None = None, detail: str | None = None) -> None:
    g.auth_invalid_reason = reason
    if hasattr(g, "_log_security_event"):
        g._log_security_event(
            "auth.invalid_attempt",
            severity="warning",
            auth_invalid_reason=reason,
            username=username,
            target_user_id=user_id,
            flow=flow,
            detail=detail,
        )


def _render_login_page_with_state(render_login_page, *, active_tab: str = "secure"):
    return render_login_page(
        active_tab=active_tab,
    )


def handle_login(context: dict[str, Any]):
    render_login_page = context["render_login_page"]
    check_credentials = context["check_internal_credentials"]
    get_user_by_username = context["get_user_by_username"]
    clear_legacy_login_captcha_session = context["clear_legacy_login_captcha_session"]
    clear_login_failures = context["clear_login_failures"]
    register_login_failure = context["register_login_failure"]
    is_login_blocked = context["is_login_blocked"]
    validate_login_captcha = context["validate_login_captcha"]
    reset_login_captcha = context["reset_login_captcha"]
    activate_login_session = context["activate_login_session"]
    begin_forced_password_change = context["begin_forced_password_change"]

    if request.method == "GET" and request.args.get("refresh_captcha") == "1":
        reset_login_captcha()

    # Show password-reset success message if flash was lost across session boundary.
    if request.method == "GET" and request.args.get("pw_reset") == "ok":
        flash("Password updated successfully. Please login with your new password.", "success")

    if request.method == "POST":
        login_action = (request.form.get("login_action") or "credentials").strip().lower()
        if login_action != "credentials":
            return _render_login_page_with_state(render_login_page, active_tab="secure")

        is_blocked, retry_after = is_login_blocked()
        if is_blocked and login_action == "credentials":
            g._log_security_event("auth.login_blocked", severity="warning", retry_after_seconds=retry_after)
            flash(f"Too many failed attempts. Try again after {retry_after} seconds.", "danger")
            return redirect(url_for("login"))

        if login_action == "credentials":
            if not validate_login_captcha(
                request.form.get("captcha_answer"),
                request.form.get("captcha_token"),
                request.form.get("captcha_proof"),
            ):
                register_login_failure()
                flash("Captcha answer is incorrect.", "warning")
                reset_login_captcha()
                return _render_login_page_with_state(render_login_page, active_tab="secure")

            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""

            user = get_user_by_username(username)

            if not user or user.get("is_active") is False:
                register_login_failure()
                _set_auth_invalid_reason("invalid_credentials", username=username, flow="login", detail="unknown_or_inactive_user")
                flash("Invalid username or password.", "danger")
                reset_login_captcha()
                return _render_login_page_with_state(render_login_page, active_tab="secure")

            credential_result = check_credentials(username, password)
            if not credential_result.ok:
                register_login_failure()
                _set_auth_invalid_reason(credential_result.reason or "invalid_credentials", username=username, user_id=user.get("id"), flow="login", detail=credential_result.message)
                flash(credential_result.message or "Invalid username or password.", "danger")
                reset_login_captcha()
                return _render_login_page_with_state(render_login_page, active_tab="secure")

            clear_legacy_login_captcha_session()
            clear_login_failures()

            if user.get("must_change_password"):
                begin_forced_password_change(user)
                g._log_security_event("auth.first_login_change_required", severity="info", target_user_id=user["id"])
                return redirect(url_for("first_login_setup"))

            activate_login_session(user)
            g._log_security_event("auth.login_success", severity="info", auth_factor="password")
            flash(f"Welcome, {user.get('full_name', 'User')}!", "success")
            return redirect(url_for("dashboard"))

    return _render_login_page_with_state(render_login_page, active_tab="secure")


def handle_first_login_setup(context: dict[str, Any]):
    validate_password_strength = context["validate_password_strength"]
    flash_internal_error = context["flash_internal_error"]
    update_password_and_phone = context["update_password_and_phone"]
    get_user_by_id = context["get_user_by_id"]
    activate_login_session = context["activate_login_session"]
    invalidate_current_session = context["invalidate_current_session"]

    user_id = session.get("force_change_user_id")
    if not user_id:
        return redirect(url_for("login"))

    is_super_admin = session.get("force_change_role") == "super_admin"

    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        phone = (request.form.get("phone") or "").strip()

        if new_password == "Nigaa@123":
            flash("You cannot keep the default password. Please choose a new one.", "danger")
            return redirect(url_for("first_login_setup"))

        ok, err = validate_password_strength(new_password, "New password")
        if not ok:
            flash(err, "danger")
            return redirect(url_for("first_login_setup"))

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("first_login_setup"))

        if not normalize_mobile(phone):
            flash("Please enter a valid 10-digit Indian mobile number (starts with 6-9).", "danger")
            return redirect(url_for("first_login_setup"))

        try:
            update_password_and_phone(user_id, new_password, phone)
        except Exception:
            flash_internal_error("Unable to update credentials. Please try again.")
            return redirect(url_for("first_login_setup"))

        g._log_security_event("auth.first_login_password_changed", severity="info", target_user_id=user_id)
        updated_user = get_user_by_id(user_id)
        if updated_user and updated_user.get("is_active") is not False:
            activate_login_session(updated_user)
            g._log_security_event("auth.login_success", severity="info", auth_factor="first_login_setup")
            flash(f"Password updated successfully. Welcome, {updated_user['full_name']}!", "success")
            return redirect(url_for("dashboard"))
        invalidate_current_session(revoke_store=True)
        flash("Password updated successfully. Please login with your new credentials.", "success")
        return redirect(url_for("login"))

    return render_template(
        "first_login_setup.html",
        username=session.get("force_change_username", ""),
        is_super_admin=is_super_admin,
    )


def handle_forgot_password_request(context: dict[str, Any]):
    get_user_by_username = context["get_user_by_username"]
    check_credentials = context["check_credentials"]
    validate_password_strength = context["validate_password_strength"]
    update_password_only = context["update_password_only"]
    invalidate_user_sessions = context.get("invalidate_user_sessions")
    invalidate_current_session = context.get("invalidate_current_session")
    flash_internal_error = context["flash_internal_error"]

    username = (request.form.get("fp_username") or request.form.get("recovery_username") or "").strip()
    old_password = request.form.get("recovery_old_password") or ""
    new_password = request.form.get("recovery_new_password") or ""
    confirm_password = request.form.get("recovery_confirm_password") or ""

    if not username:
        flash("Username is required for password reset.", "warning")
        return redirect(url_for("login", tab="recovery"))

    if not old_password:
        flash("Current password is required for password reset.", "warning")
        return redirect(url_for("login", tab="recovery"))

    if not new_password:
        flash("New password is required.", "warning")
        return redirect(url_for("login", tab="recovery"))

    user = get_user_by_username(username)
    if not user or user.get("is_active") is False:
        _set_auth_invalid_reason("expired_credentials", username=username, flow="password_reset", detail="unknown_or_inactive_user")
        flash("Invalid username or current password.", "warning")
        return redirect(url_for("login", tab="recovery"))

    credential_result = check_credentials(username, old_password)
    if not credential_result.ok:
        _set_auth_invalid_reason(credential_result.reason or "invalid_credentials", username=username, user_id=user.get("id"), flow="password_reset", detail="wrong_old_password")
        flash("Invalid username or current password.", "warning")
        return redirect(url_for("login", tab="recovery"))

    if new_password == old_password:
        flash("New password must be different from the current password.", "danger")
        return redirect(url_for("login", tab="recovery"))

    if new_password == "Nigaa@123":
        flash("You cannot use the default password.", "danger")
        return redirect(url_for("login", tab="recovery"))

    ok, err = validate_password_strength(new_password, "New password")
    if not ok:
        flash(err, "danger")
        return redirect(url_for("login", tab="recovery"))

    if new_password != confirm_password:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("login", tab="recovery"))

    try:
        update_password_only(user["id"], new_password)
    except Exception:
        flash_internal_error("Unable to update password. Please try again.")
        return redirect(url_for("login", tab="recovery"))

    if invalidate_user_sessions:
        invalidate_user_sessions(user["id"])

    g._log_security_event("auth.password_reset_completed", severity="info", target_user_id=user.get("id"))

    if invalidate_current_session:
        invalidate_current_session(revoke_store=True)

    flash("Password updated successfully. Please login with your new password.", "success")
    return redirect(url_for("login", pw_reset="ok"), 303)


def handle_forgot_password_set(context: dict[str, Any]):
    """Legacy endpoint kept for bookmark/back-button safety — redirects to login."""
    flash("Please use the password recovery form to reset your password.", "info")
    return redirect(url_for("login", tab="recovery"))
