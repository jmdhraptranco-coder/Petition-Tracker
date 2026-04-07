from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import json
import re
import time
import warnings

from flask import current_app, flash, g, redirect, render_template, request, session, url_for

try:
    import requests
    from requests.auth import HTTPBasicAuth
except Exception:  # pragma: no cover
    requests = None

    class HTTPBasicAuth:  # type: ignore[override]
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

try:
    from urllib3.exceptions import InsecureRequestWarning
except Exception:  # pragma: no cover
    InsecureRequestWarning = None


LOGIN_PENDING_KEY = "pending_login_auth"
RESET_PENDING_KEY = "pw_reset_state"
OTP_TTL_SECONDS = 300


def normalize_mobile_for_otp(raw_mobile: str | None) -> str | None:
    digits = re.sub(r"\D+", "", raw_mobile or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if re.fullmatch(r"[6-9]\d{9}", digits or ""):
        return digits
    return None


def mask_mobile(mobile: str | None) -> str:
    normalized = normalize_mobile_for_otp(mobile)
    if not normalized:
        return ""
    return f"******{normalized[-4:]}"


def _session_now() -> int:
    return int(time.time())


def _message_from_payload(payload: Any) -> str:
    if isinstance(payload, dict):
        for key in ("message", "msg", "statusMessage", "error", "reason", "remarks", "response"):
            value = payload.get(key)
            if value:
                return str(value).strip()
        return json.dumps(payload, ensure_ascii=True, default=str)
    if payload is None:
        return ""
    return str(payload).strip()


def _looks_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value == 1
    if isinstance(value, str):
        return value.strip().lower() in {"1", "ok", "success", "true", "valid", "verified", "y", "yes"}
    return False


@dataclass
class APIResult:
    ok: bool
    reason: str | None = None
    message: str = ""
    payload: Any = None


class InternalAPI:
    def __init__(
        self,
        *,
        base_url: str | None,
        basic_username: str | None = None,
        basic_password: str | None = None,
        verify_ssl: bool = True,
        timeout_seconds: int = 60,
        otp_user_id: str | None = None,
        otp_app_name: str = "ita",
        otp_message: str = "IT Assets",
        otp_type: str = "otp",
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.basic_username = basic_username
        self.basic_password = basic_password
        self.verify_ssl = bool(verify_ssl)
        self.timeout_seconds = int(timeout_seconds)
        self.otp_user_id = str(otp_user_id or "").strip()
        self.otp_app_name = (otp_app_name or "ita").strip() or "ita"
        self.otp_message = (otp_message or "IT Assets").strip() or "IT Assets"
        self.otp_type = (otp_type or "otp").strip() or "otp"

    @classmethod
    def from_config(cls, config: Any) -> "InternalAPI":
        return cls(
            base_url=getattr(config, "AUTH_API_BASE_URL", None),
            basic_username=getattr(config, "AUTH_API_BASIC_USERNAME", None),
            basic_password=getattr(config, "AUTH_API_BASIC_PASSWORD", None),
            verify_ssl=bool(getattr(config, "AUTH_API_VERIFY_TLS", True)),
            timeout_seconds=int(getattr(config, "AUTH_API_TIMEOUT_SECONDS", 60)),
            otp_user_id=getattr(config, "AUTH_API_OTP_USER_ID", None),
            otp_app_name=getattr(config, "AUTH_API_APP_NAME", "ita"),
            otp_message=getattr(config, "AUTH_API_OTP_MESSAGE", "IT Assets"),
            otp_type=getattr(config, "AUTH_API_OTP_TYPE", "otp"),
        )

    def is_configured(self) -> bool:
        return bool(self.base_url)

    def _auth(self) -> HTTPBasicAuth | None:
        if not (self.basic_username and self.basic_password):
            return None
        return HTTPBasicAuth(self.basic_username, self.basic_password)

    def _post(self, path: str, payload: dict[str, Any]) -> APIResult:
        if requests is None:
            return APIResult(False, reason="auth_api_dependency_missing", message="Authentication client dependency is unavailable.")
        if not self.is_configured():
            return APIResult(False, reason="auth_api_unconfigured", message="Authentication service is not configured.")
        url = f"{self.base_url}{path}"
        try:
            if self.verify_ssl or InsecureRequestWarning is None:
                response = requests.post(
                    url,
                    json=payload,
                    verify=self.verify_ssl,
                    timeout=self.timeout_seconds,
                    auth=self._auth(),
                )
            else:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", InsecureRequestWarning)
                    response = requests.post(
                        url,
                        json=payload,
                        verify=False,
                        timeout=self.timeout_seconds,
                        auth=self._auth(),
                    )
        except requests.Timeout:
            return APIResult(False, reason="server_busy", message="Authentication server timed out.")
        except requests.RequestException:
            return APIResult(False, reason="server_busy", message="Authentication server is unavailable.")

        try:
            body = response.json()
        except ValueError:
            body = response.text

        if response.status_code >= 500:
            return APIResult(False, reason="server_busy", message="Authentication server is busy.", payload=body)
        if response.status_code >= 400:
            return APIResult(False, reason="invalid_credentials", message=_message_from_payload(body) or "Authentication failed.", payload=body)
        return APIResult(True, message=_message_from_payload(body), payload=body)

    def check_credentials(self, username: str, password: str) -> APIResult:
        result = self._post("/checkCred", {"user_id": username, "passwd": password})
        if not result.ok:
            return result
        payload = result.payload
        if isinstance(payload, dict):
            for key in ("success", "status", "valid", "authenticated"):
                if key in payload and _looks_truthy(payload.get(key)):
                    return APIResult(True, message=result.message or "Credentials verified.", payload=payload)
        message = (result.message or "").lower()
        if any(token in message for token in ("expired", "inactive", "disabled")):
            return APIResult(False, reason="expired_credentials", message=result.message or "Credentials are expired.", payload=payload)
        if any(token in message for token in ("invalid", "failed", "wrong", "mismatch", "denied")):
            return APIResult(False, reason="invalid_credentials", message=result.message or "Invalid username or password.", payload=payload)
        return APIResult(True, message=result.message or "Credentials verified.", payload=payload)

    def send_otp(self, mobile: str) -> APIResult:
        payload = {
            "mobileno": mobile,
            "otpType": self.otp_type,
            "userId": self.otp_user_id,
            "appName": self.otp_app_name,
            "message": self.otp_message,
        }
        result = self._post("/sendOTP", payload)
        if not result.ok:
            return result
        message = (result.message or "").lower()
        if any(token in message for token in ("failed", "error", "unable")):
            return APIResult(False, reason="server_busy", message=result.message or "Unable to send OTP.", payload=result.payload)
        return APIResult(True, message=result.message or "OTP sent.", payload=result.payload)

    def verify_otp(self, mobile: str, otp_code: str) -> APIResult:
        payload = {
            "mobileno": mobile,
            "otpcode": otp_code,
            "userId": self.otp_user_id,
            "appName": self.otp_app_name,
        }
        result = self._post("/verifyOTP", payload)
        if not result.ok:
            return result
        payload_data = result.payload
        if isinstance(payload_data, dict):
            for key in ("success", "status", "verified", "valid"):
                if key in payload_data and _looks_truthy(payload_data.get(key)):
                    return APIResult(True, message=result.message or "OTP verified.", payload=payload_data)
        message = (result.message or "").lower()
        if any(token in message for token in ("expired", "timeout")):
            return APIResult(False, reason="invalid_otp", message=result.message or "OTP expired.", payload=payload_data)
        if any(token in message for token in ("invalid", "wrong", "mismatch", "failed")):
            return APIResult(False, reason="invalid_otp", message=result.message or "Invalid OTP.", payload=payload_data)
        return APIResult(True, message=result.message or "OTP verified.", payload=payload_data)


def clear_pending_login_state() -> None:
    session.pop(LOGIN_PENDING_KEY, None)


def clear_reset_password_state() -> None:
    session.pop(RESET_PENDING_KEY, None)


def get_pending_login_state() -> dict[str, Any] | None:
    state = session.get(LOGIN_PENDING_KEY)
    if not isinstance(state, dict):
        return None
    created_at = int(state.get("created_at") or 0)
    now_ts = _session_now()
    if created_at <= 0 or now_ts - created_at > OTP_TTL_SECONDS:
        clear_pending_login_state()
        return None
    return dict(state)


def get_reset_password_state() -> dict[str, Any] | None:
    state = session.get(RESET_PENDING_KEY)
    if not isinstance(state, dict):
        return None
    created_at = int(state.get("created_at") or 0)
    verified_at = int(state.get("verified_at") or 0)
    now_ts = _session_now()
    anchor = verified_at or created_at
    if anchor <= 0 or now_ts - anchor > OTP_TTL_SECONDS:
        clear_reset_password_state()
        return None
    return dict(state)


def begin_pending_login(user: dict[str, Any], mobile: str) -> dict[str, Any]:
    state = {
        "created_at": _session_now(),
        "user_id": int(user["id"]),
        "username": user.get("username") or "",
        "mobile": mobile,
        "masked_mobile": mask_mobile(mobile),
        "must_change_password": bool(user.get("must_change_password")),
    }
    session[LOGIN_PENDING_KEY] = state
    session.modified = True
    return state


def begin_reset_password(user: dict[str, Any], mobile: str) -> dict[str, Any]:
    state = {
        "created_at": _session_now(),
        "verified_at": None,
        "otp_verified": False,
        "user_id": int(user["id"]),
        "username": user.get("username") or "",
        "mobile": mobile,
        "masked_mobile": mask_mobile(mobile),
    }
    session[RESET_PENDING_KEY] = state
    session.modified = True
    return state


def mark_reset_password_verified() -> dict[str, Any] | None:
    state = get_reset_password_state()
    if not state:
        return None
    state["otp_verified"] = True
    state["verified_at"] = _session_now()
    session[RESET_PENDING_KEY] = state
    session.modified = True
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
    pending_login = get_pending_login_state()
    reset_state = get_reset_password_state()
    return render_login_page(
        active_tab=active_tab,
        pending_login_otp=bool(pending_login),
        pending_login_username=(pending_login or {}).get("username", ""),
        pending_login_masked_mobile=(pending_login or {}).get("masked_mobile", ""),
        pending_reset_otp=bool(reset_state and not reset_state.get("otp_verified")),
        reset_username=(reset_state or {}).get("username", ""),
        reset_masked_mobile=(reset_state or {}).get("masked_mobile", ""),
    )


def handle_login(context: dict[str, Any]):
    render_login_page = context["render_login_page"]
    check_credentials = context["check_internal_credentials"]
    send_login_otp = context["send_login_otp"]
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

            clear_pending_login_state()
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            credential_result = check_credentials(username, password)
            user = None
            if isinstance(credential_result.payload, dict):
                user = credential_result.payload.get("user")
            if not user:
                user = get_user_by_username(username)

            if not credential_result.ok:
                register_login_failure()
                _set_auth_invalid_reason(credential_result.reason or "invalid_credentials", username=username, user_id=user.get("id"), flow="login", detail=credential_result.message)
                flash(credential_result.message or "Invalid username or password.", "danger")
                reset_login_captcha()
                return _render_login_page_with_state(render_login_page, active_tab="secure")

            if not user or user.get("is_active") is False:
                register_login_failure()
                _set_auth_invalid_reason("expired_credentials", username=username, flow="login", detail="missing_or_inactive_local_user")
                flash("Invalid username or password.", "danger")
                reset_login_captcha()
                return _render_login_page_with_state(render_login_page, active_tab="secure")

            mobile = normalize_mobile_for_otp(user.get("phone"))
            if not mobile:
                clear_legacy_login_captcha_session()
                activate_login_session(user)
                clear_login_failures()
                g._log_security_event("auth.login_success", severity="info", auth_factor="password_only_no_registered_phone")
                flash(f"Welcome, {user['full_name']}!", "success")
                return redirect(url_for("dashboard"))

            otp_result = send_login_otp(mobile)
            if not otp_result.ok:
                _set_auth_invalid_reason(otp_result.reason or "server_busy", username=username, user_id=user.get("id"), flow="login", detail=otp_result.message)
                flash(otp_result.message or "Unable to send OTP. Please try again.", "danger")
                return _render_login_page_with_state(render_login_page, active_tab="secure")

            pending_state = begin_pending_login(user, mobile)
            g._log_security_event("auth.pending_otp_started", severity="info", flow="login", target_user_id=user.get("id"))
            flash(f"OTP sent to your registered mobile {pending_state['masked_mobile']}.", "info")
            return redirect(url_for("login_verify_otp"))

    return _render_login_page_with_state(render_login_page, active_tab="secure")


def handle_login_verify(context: dict[str, Any]):
    send_login_otp = context["send_login_otp"]
    verify_login_otp = context["verify_login_otp"]
    get_user_by_username = context["get_user_by_username"]
    clear_legacy_login_captcha_session = context["clear_legacy_login_captcha_session"]
    clear_login_failures = context["clear_login_failures"]
    activate_login_session = context["activate_login_session"]
    begin_forced_password_change = context["begin_forced_password_change"]

    pending_state = get_pending_login_state()
    if not pending_state:
        flash("Your verification session expired. Please login again.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST" and (request.form.get("login_action") or "").strip().lower() == "resend_otp":
        otp_result = send_login_otp(pending_state["mobile"])
        if not otp_result.ok:
            _set_auth_invalid_reason(otp_result.reason or "server_busy", username=pending_state.get("username"), user_id=pending_state.get("user_id"), flow="login_resend", detail=otp_result.message)
            flash(otp_result.message or "Unable to resend OTP.", "danger")
        else:
            pending_state["created_at"] = _session_now()
            session[LOGIN_PENDING_KEY] = pending_state
            session.modified = True
            flash(f"OTP resent to {pending_state['masked_mobile']}.", "info")
        return redirect(url_for("login_verify_otp"))

    if request.method == "POST":
        otp_code = (request.form.get("otp_code") or "").strip()
        if not re.fullmatch(r"\d{4,8}", otp_code):
            flash("Enter a valid OTP.", "warning")
            return render_template("login_otp_verify.html", username=pending_state.get("username", ""), masked_mobile=pending_state.get("masked_mobile", ""))

        verify_result = verify_login_otp(pending_state["mobile"], otp_code)
        if not verify_result.ok:
            _set_auth_invalid_reason(verify_result.reason or "invalid_otp", username=pending_state.get("username"), user_id=pending_state.get("user_id"), flow="login_verify", detail=verify_result.message)
            flash(verify_result.message or "Invalid OTP.", "danger")
            return render_template("login_otp_verify.html", username=pending_state.get("username", ""), masked_mobile=pending_state.get("masked_mobile", ""))

        user = get_user_by_username(pending_state["username"])
        clear_pending_login_state()
        clear_legacy_login_captcha_session()
        clear_login_failures()
        if not user or user.get("is_active") is False:
            _set_auth_invalid_reason("expired_credentials", username=pending_state.get("username"), user_id=pending_state.get("user_id"), flow="login_finalize", detail="local_user_missing_after_otp")
            flash("Your account is no longer active. Please contact administrator.", "danger")
            return redirect(url_for("login"))
        if user.get("must_change_password"):
            begin_forced_password_change(user)
            g._log_security_event("auth.first_login_change_required", severity="info", target_user_id=user["id"])
            return redirect(url_for("first_login_setup"))

        activate_login_session(user)
        g._log_security_event("auth.login_success", severity="info", auth_factor="password_plus_otp")
        flash(f"Welcome, {user['full_name']}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login_otp_verify.html", username=pending_state.get("username", ""), masked_mobile=pending_state.get("masked_mobile", ""))


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

        if not normalize_mobile_for_otp(phone):
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
    send_login_otp = context["send_login_otp"]

    clear_reset_password_state()
    username = (request.form.get("fp_username") or request.form.get("recovery_username") or "").strip()
    if not username:
        flash("Username is required for password reset.", "warning")
        return redirect(url_for("login", tab="recovery"))

    user = get_user_by_username(username)
    if not user or user.get("is_active") is False:
        _set_auth_invalid_reason("expired_credentials", username=username, flow="password_reset_request", detail="unknown_or_inactive_user")
        flash("Unable to start password reset for this account.", "warning")
        return redirect(url_for("login", tab="recovery"))

    mobile = normalize_mobile_for_otp(user.get("phone"))
    if not mobile:
        flash("No valid recovery mobile number is registered for this account.", "warning")
        return redirect(url_for("login", tab="recovery"))

    send_result = send_login_otp(mobile)
    if not send_result.ok:
        _set_auth_invalid_reason(send_result.reason or "server_busy", username=username, user_id=user.get("id"), flow="password_reset_request", detail=send_result.message)
        flash(send_result.message or "Unable to send OTP. Please try again.", "danger")
        return redirect(url_for("login", tab="recovery"))

    reset_state = begin_reset_password(user, mobile)
    g._log_security_event("auth.pending_otp_started", severity="info", flow="password_reset", target_user_id=user.get("id"))
    flash(f"OTP sent to {reset_state['masked_mobile']}.", "info")
    return redirect(url_for("forgot_password_verify"))


def handle_forgot_password_verify(context: dict[str, Any]):
    verify_login_otp = context["verify_login_otp"]

    state = get_reset_password_state()
    if not state or state.get("otp_verified"):
        flash("Your password reset session expired. Please start again.", "warning")
        return redirect(url_for("login", tab="recovery"))

    if request.method == "GET":
        return render_template("password_reset_verify.html", username=state.get("username", ""), masked_mobile=state.get("masked_mobile", ""))

    otp_code = (request.form.get("otp_code") or "").strip()
    if not re.fullmatch(r"\d{4,8}", otp_code):
        flash("Enter a valid OTP.", "warning")
        return render_template("password_reset_verify.html", username=state.get("username", ""), masked_mobile=state.get("masked_mobile", ""))

    verify_result = verify_login_otp(state["mobile"], otp_code)
    if not verify_result.ok:
        _set_auth_invalid_reason(verify_result.reason or "invalid_otp", username=state.get("username"), user_id=state.get("user_id"), flow="password_reset_verify", detail=verify_result.message)
        flash(verify_result.message or "Invalid OTP.", "danger")
        return render_template("password_reset_verify.html", username=state.get("username", ""), masked_mobile=state.get("masked_mobile", ""))

    mark_reset_password_verified()
    g._log_security_event("auth.otp_verified", severity="info", flow="password_reset", target_user_id=state.get("user_id"))
    flash("OTP verified. Set your new password now.", "success")
    return redirect(url_for("forgot_password_set"))


def handle_forgot_password_resend_otp(context: dict[str, Any]):
    send_login_otp = context["send_login_otp"]

    state = get_reset_password_state()
    if not state or state.get("otp_verified"):
        flash("Your password reset session expired. Please start again.", "warning")
        return redirect(url_for("login", tab="recovery"))

    send_result = send_login_otp(state["mobile"])
    if not send_result.ok:
        _set_auth_invalid_reason(send_result.reason or "server_busy", username=state.get("username"), user_id=state.get("user_id"), flow="password_reset_resend", detail=send_result.message)
        flash(send_result.message or "Unable to resend OTP.", "danger")
        return redirect(url_for("login", tab="recovery"))

    state["created_at"] = _session_now()
    session[RESET_PENDING_KEY] = state
    session.modified = True
    flash(f"OTP resent to {state['masked_mobile']}.", "info")
    return redirect(url_for("forgot_password_verify"))


def handle_forgot_password_set(context: dict[str, Any]):
    validate_password_strength = context["validate_password_strength"]
    flash_internal_error = context["flash_internal_error"]
    update_password_only = context["update_password_only"]

    state = get_reset_password_state()
    if not state or not state.get("otp_verified"):
        flash("Verify OTP before setting a new password.", "warning")
        return redirect(url_for("login", tab="recovery"))

    if request.method == "POST":
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if new_password == "Nigaa@123":
            flash("You cannot reuse the default password.", "danger")
            return render_template("password_reset_set.html", username=state.get("username", ""))

        ok, err = validate_password_strength(new_password, "New password")
        if not ok:
            flash(err, "danger")
            return render_template("password_reset_set.html", username=state.get("username", ""))

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("password_reset_set.html", username=state.get("username", ""))

        try:
            update_password_only(state["user_id"], new_password)
        except Exception:
            flash_internal_error("Unable to update password. Please try again.")
            return render_template("password_reset_set.html", username=state.get("username", ""))

        clear_reset_password_state()
        g._log_security_event("auth.password_reset_completed", severity="info", target_user_id=state.get("user_id"))
        flash("Password updated successfully. Please login with your new password.", "success")
        return redirect(url_for("login"))

    return render_template("password_reset_set.html", username=state.get("username", ""))
