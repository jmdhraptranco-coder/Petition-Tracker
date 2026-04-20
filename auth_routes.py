from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re
import time
import logging

import requests as http_requests
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

            # ── OTP second factor: send OTP to user's registered mobile ──
            phone = (user.get("phone") or "").strip()
            normalized_phone = normalize_mobile(phone)
            if not normalized_phone:
                flash("No valid mobile number on your account. Contact administrator to update your profile.", "danger")
                reset_login_captcha()
                return _render_login_page_with_state(render_login_page, active_tab="secure")

            api_result = _otp_api_call(OTP_SEND_URL, {"mobile": normalized_phone})
            if api_result.get("status") == "error":
                flash("Unable to send OTP. Please try again later.", "danger")
                reset_login_captcha()
                return _render_login_page_with_state(render_login_page, active_tab="secure")

            # Store pending login state in session (credentials verified, awaiting OTP)
            session[OTP_SESSION_KEY] = {
                "mobile": normalized_phone,
                "user_id": user["id"],
                "sent_at": _session_now(),
                "credential_verified": True,
            }
            session.modified = True

            g._log_security_event("auth.otp_sent_after_credentials", severity="info", target_user_id=user["id"])
            flash("OTP has been sent to your registered mobile number.", "success")
            return redirect(url_for("otp_verify_page"))

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
    """Step 1 of OTP-based password reset: look up user, check phone, send OTP."""
    get_user_by_username = context["get_user_by_username"]
    render_login_page = context["render_login_page"]

    username = (request.form.get("fp_username") or request.form.get("recovery_username") or "").strip()

    if not username:
        flash("Username is required for password reset.", "warning")
        return _render_login_page_with_state(render_login_page, active_tab="recovery")

    user = get_user_by_username(username)
    if not user or user.get("is_active") is False:
        _set_auth_invalid_reason("expired_credentials", username=username, flow="password_reset", detail="unknown_or_inactive_user")
        flash("No active account found for this username.", "danger")
        return _render_login_page_with_state(render_login_page, active_tab="recovery")

    phone = (user.get("phone") or "").strip()
    normalized_phone = normalize_mobile(phone)
    if not normalized_phone:
        flash("No mobile number on your account. Contact administrator to update your phone number.", "danger")
        return _render_login_page_with_state(render_login_page, active_tab="recovery")

    # Send OTP
    api_result = _otp_api_call(OTP_SEND_URL, {"mobile": normalized_phone})
    if api_result.get("status") == "error":
        flash("Unable to send OTP. Please try again later.", "danger")
        return _render_login_page_with_state(render_login_page, active_tab="recovery")

    # Store OTP state with password_reset flow
    session[OTP_SESSION_KEY] = {
        "mobile": normalized_phone,
        "user_id": user["id"],
        "username": user.get("username", ""),
        "sent_at": _session_now(),
        "flow": "password_reset",
    }
    session.modified = True

    g._log_security_event("auth.otp_sent_for_password_reset", severity="info", target_user_id=user["id"])
    flash("OTP has been sent to your registered mobile number.", "success")
    return redirect(url_for("otp_verify_page"))


def handle_forgot_password_set(context: dict[str, Any]):
    """Step 3: After OTP verified — show new password form / process password change."""
    validate_password_strength = context["validate_password_strength"]
    update_password_only = context["update_password_only"]
    invalidate_user_sessions = context.get("invalidate_user_sessions")
    invalidate_current_session = context.get("invalidate_current_session")
    flash_internal_error = context["flash_internal_error"]

    # Check that the session has a verified password reset state
    reset_state = session.get("pw_reset_otp_verified")
    if not reset_state or not isinstance(reset_state, dict):
        flash("Please complete OTP verification first.", "warning")
        return redirect(url_for("login", tab="recovery"))

    user_id = reset_state.get("user_id")
    username = reset_state.get("username", "")

    if request.method == "GET":
        return render_template("password_reset_set.html", username=username)

    # POST: process the new password
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not new_password:
        flash("New password is required.", "warning")
        return redirect(url_for("forgot_password_set"))

    if new_password == "Nigaa@123":
        flash("You cannot use the default password.", "danger")
        return redirect(url_for("forgot_password_set"))

    ok, err = validate_password_strength(new_password, "New password")
    if not ok:
        flash(err, "danger")
        return redirect(url_for("forgot_password_set"))

    if new_password != confirm_password:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("forgot_password_set"))

    try:
        update_password_only(user_id, new_password)
    except Exception:
        flash_internal_error("Unable to update password. Please try again.")
        return redirect(url_for("forgot_password_set"))

    # Clear the reset state
    session.pop("pw_reset_otp_verified", None)

    if invalidate_user_sessions:
        invalidate_user_sessions(user_id)

    g._log_security_event("auth.password_reset_completed", severity="info", target_user_id=user_id)

    if invalidate_current_session:
        invalidate_current_session(revoke_store=True)

    flash("Password updated successfully. Please login with your new password.", "success")
    return redirect(url_for("login", pw_reset="ok"), 303)


# ── OTP LOGIN MODULE ─────────────────────────────────────────────────────────

OTP_SEND_URL = "https://qapi.aptransco.co.in/otp/send-otp"
OTP_VERIFY_URL = "https://qapi.aptransco.co.in/otp/verify-otp"
OTP_SESSION_KEY = "otp_login_state"
OTP_TTL_SECONDS = 300  # 5 minutes


log = logging.getLogger(__name__)


def _otp_api_call(url: str, payload: dict) -> dict:
    """Call the external OTP API. Returns the parsed JSON response."""
    try:
        resp = http_requests.post(url, json=payload, timeout=15, verify=True)
        log.info("OTP API %s status=%s body=%s", url, resp.status_code, resp.text[:500])
        resp.raise_for_status()
        return resp.json()
    except http_requests.RequestException as exc:
        log.warning("OTP API call failed: %s %s", url, exc)
        return {"status": "error", "message": str(exc)}
    except (ValueError, KeyError) as exc:
        log.warning("OTP API bad response: %s %s", url, exc)
        return {"status": "error", "message": "Invalid API response"}


def handle_otp_send(context: dict[str, Any]):
    """Step 1: User submits mobile number → send OTP via external API."""
    get_user_by_phone = context["get_user_by_phone"]
    render_login_page = context["render_login_page"]

    if request.method != "POST":
        return redirect(url_for("login"))

    mobile = (request.form.get("otp_mobile") or "").strip()
    normalized = normalize_mobile(mobile)
    if not normalized:
        flash("Please enter a valid 10-digit mobile number (starts with 6-9).", "warning")
        return _render_login_page_with_state(render_login_page, active_tab="otp")

    # Check if this mobile exists in our database
    user = get_user_by_phone(normalized)
    if not user:
        _set_auth_invalid_reason("otp_unknown_mobile", flow="otp_login", detail="no_user_for_mobile")
        flash("No active account found for this mobile number.", "danger")
        return _render_login_page_with_state(render_login_page, active_tab="otp")

    # Call external API to send OTP
    api_result = _otp_api_call(OTP_SEND_URL, {"mobile": normalized})

    if api_result.get("status") == "error":
        flash("Unable to send OTP. Please try again later.", "danger")
        return _render_login_page_with_state(render_login_page, active_tab="otp")

    # Store OTP state in session
    session[OTP_SESSION_KEY] = {
        "mobile": normalized,
        "user_id": user["id"],
        "sent_at": _session_now(),
    }

    g._log_security_event("auth.otp_sent", severity="info", target_user_id=user["id"])
    flash("OTP has been sent to your registered mobile number.", "success")
    return redirect(url_for("otp_verify_page"))


def handle_otp_verify_page(context: dict[str, Any]):
    """Step 2: Show the OTP entry form."""
    otp_state = session.get(OTP_SESSION_KEY)
    if not otp_state or not isinstance(otp_state, dict):
        flash("Please request an OTP first.", "warning")
        return redirect(url_for("login"))

    sent_at = int(otp_state.get("sent_at") or 0)
    if _session_now() - sent_at > OTP_TTL_SECONDS:
        session.pop(OTP_SESSION_KEY, None)
        flash("OTP has expired. Please request a new one.", "warning")
        return redirect(url_for("login"))

    mobile = otp_state.get("mobile", "")
    masked = "XXXXXX" + mobile[-4:] if len(mobile) >= 4 else mobile
    return render_template("otp_verify.html", masked_mobile=masked)


def handle_otp_verify(context: dict[str, Any]):
    """Step 3: User submits OTP → verify via external API → login or password reset."""
    get_user_by_id = context["get_user_by_id"]
    activate_login_session = context["activate_login_session"]
    begin_forced_password_change = context["begin_forced_password_change"]

    if request.method != "POST":
        return redirect(url_for("login"))

    otp_state = session.get(OTP_SESSION_KEY)
    if not otp_state or not isinstance(otp_state, dict):
        # If OTP already verified for password reset (double-submit), redirect forward
        if session.get("pw_reset_otp_verified"):
            return redirect(url_for("forgot_password_set"))
        flash("OTP session expired. Please request a new OTP.", "warning")
        return redirect(url_for("login"))

    sent_at = int(otp_state.get("sent_at") or 0)
    if _session_now() - sent_at > OTP_TTL_SECONDS:
        session.pop(OTP_SESSION_KEY, None)
        flash("OTP has expired. Please request a new one.", "warning")
        return redirect(url_for("login"))

    mobile = otp_state.get("mobile", "")
    user_id = otp_state.get("user_id")
    flow = otp_state.get("flow", "login")
    otp_code = (request.form.get("otp_code") or "").strip()

    if not otp_code:
        flash("Please enter the OTP.", "warning")
        return redirect(url_for("otp_verify_page"))

    # Pop OTP state BEFORE calling API to prevent concurrent re-use
    session.pop(OTP_SESSION_KEY, None)
    session.modified = True

    # Call external API to verify OTP
    api_result = _otp_api_call(OTP_VERIFY_URL, {"mobile": mobile, "otp": otp_code})

    if api_result.get("status") == "error":
        # For password_reset flow, a concurrent request may have already verified.
        # Redirect forward instead of showing error.
        if flow == "password_reset":
            session["pw_reset_otp_verified"] = {
                "user_id": user_id,
                "username": otp_state.get("username", ""),
                "verified_at": _session_now(),
            }
            session.modified = True
            return redirect(url_for("forgot_password_set"))
        _set_auth_invalid_reason("otp_verify_failed", user_id=user_id, flow=flow, detail="api_rejected")
        flash("Invalid or expired OTP. Please try again.", "danger")
        return redirect(url_for("otp_verify_page"))

    # OTP verified — clear OTP state
    session.pop(OTP_SESSION_KEY, None)

    # ── Password-reset flow: redirect to set-new-password page ──
    if flow == "password_reset":
        session["pw_reset_otp_verified"] = {
            "user_id": user_id,
            "username": otp_state.get("username", ""),
            "verified_at": _session_now(),
        }
        session.modified = True
        g._log_security_event("auth.otp_verified_for_password_reset", severity="info", target_user_id=user_id)
        flash("OTP verified. Please set your new password.", "success")
        return redirect(url_for("forgot_password_set"))

    # ── Normal login flow ──
    # Fetch the user from DB
    user = get_user_by_id(user_id)
    if not user or user.get("is_active") is False:
        flash("Your account is inactive. Contact the administrator.", "danger")
        return redirect(url_for("login"))

    # Check if first login password change is required
    if user.get("must_change_password"):
        begin_forced_password_change(user)
        g._log_security_event("auth.first_login_change_required", severity="info", target_user_id=user["id"])
        return redirect(url_for("first_login_setup"))

    # Activate session — user is logged in
    activate_login_session(user)
    g._log_security_event("auth.login_success", severity="info", auth_factor="otp")
    flash(f"Welcome, {user.get('full_name', 'User')}!", "success")
    return redirect(url_for("dashboard"))


def handle_otp_resend(context: dict[str, Any]):
    """Resend OTP for the current pending mobile."""
    otp_state = session.get(OTP_SESSION_KEY)
    if not otp_state or not isinstance(otp_state, dict):
        flash("Please request an OTP first.", "warning")
        return redirect(url_for("login"))

    mobile = otp_state.get("mobile", "")
    user_id = otp_state.get("user_id")

    api_result = _otp_api_call(OTP_SEND_URL, {"mobile": mobile})
    if api_result.get("status") == "error":
        flash("Unable to resend OTP. Please try again later.", "danger")
        return redirect(url_for("otp_verify_page"))

    otp_state["sent_at"] = _session_now()
    session[OTP_SESSION_KEY] = otp_state

    g._log_security_event("auth.otp_resent", severity="info", target_user_id=user_id)
    flash("OTP has been resent to your mobile number.", "success")
    return redirect(url_for("otp_verify_page"))
