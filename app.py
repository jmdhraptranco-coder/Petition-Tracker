from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory, g, has_request_context
from functools import wraps
from config import Config
import models
from datetime import datetime, date
from collections import Counter
import os
import io
import csv
import re
import copy
import random
from uuid import uuid4
from werkzeug.utils import secure_filename
try:
    from openpyxl import load_workbook
except Exception:
    load_workbook = None

config = Config()
app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = config.SESSION_COOKIE_SECURE

if os.getenv('SKIP_SCHEMA_UPDATES') != '1':
    models.ensure_schema_updates()

BASE_UPLOAD_DIR = config.UPLOAD_BASE_DIR
ERECEIPT_UPLOAD_DIR = os.path.join(BASE_UPLOAD_DIR, 'e_receipts')
ENQUIRY_UPLOAD_DIR = os.path.join(BASE_UPLOAD_DIR, 'enquiry_reports')
PROFILE_UPLOAD_DIR = os.path.join(BASE_UPLOAD_DIR, 'profile_photos')
MAX_UPLOAD_SIZE_BYTES = config.MAX_UPLOAD_SIZE_MB * 1024 * 1024
PROFILE_PHOTO_MAX_BYTES = 2 * 1024 * 1024
PROFILE_PHOTO_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
VALID_RECEIVED_AT = {'jmd_office', 'cvo_apspdcl_tirupathi', 'cvo_apepdcl_vizag', 'cvo_apcpdcl_vijayawada'}
VALID_TARGET_CVO = {'apspdcl', 'apepdcl', 'apcpdcl', 'headquarters'}
VALID_ENQUIRY_TYPES = {'detailed', 'preliminary'}
VALID_SOURCE_OF_PETITION = {'media', 'public_individual', 'govt', 'sumoto', 'cmd_office'}
VALID_GOVT_INSTITUTIONS = {
    'aprc',
    'governor',
    'cs_energy_department',
    'cmd_aptransco',
    'cmo',
    'energy_department',
}
VALID_PETITION_TYPES = {
    'bribe',
    'corruption',
    'harassment',
    'misconduct',
    'works_related',
    'irregularities_in_tenders',
    'illegal_assets',
    'fake_certificates',
    'theft_misappropriation_materials',
    'other',
}
PETITION_TYPE_LABELS = {
    # Current workflow values
    'bribe': 'Bribe',
    'corruption': 'Corruption',
    'harassment': 'Harassment',
    'misconduct': 'Misconduct',
    'works_related': 'Works Related',
    'irregularities_in_tenders': 'Irregularities in Tenders',
    'illegal_assets': 'Illegal Assets',
    'fake_certificates': 'Fake Certificates',
    'theft_misappropriation_materials': 'Theft/Misappropriation of Materials',
    'other': 'Other',
    # Legacy DB values kept for display/filter compatibility
    'theft_of_materials': 'Theft of Materials',
    'adverse_news': 'Adverse News',
    'procedural_lapses': 'Procedural Lapses',
}
VALID_PERMISSION_REQUEST_TYPES = {'direct_enquiry', 'permission_required'}
DIRECT_ENQUIRY_EFILE_EDITABLE_STATUSES = {'received', 'forwarded_to_cvo', 'assigned_to_inspector', 'enquiry_in_progress'}
VALID_USER_ROLES = {
    'super_admin', 'data_entry', 'po',
    'cmd_apspdcl', 'cmd_apepdcl', 'cmd_apcpdcl',
    'cgm_hr_transco',
    'dsp', 'cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'inspector'
}
VALID_PUBLIC_SIGNUP_ROLES = {
    'data_entry', 'po',
    'cmd_apspdcl', 'cmd_apepdcl', 'cmd_apcpdcl',
    'cgm_hr_transco',
    'dsp', 'cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'inspector'
}
VALID_CVO_OFFICES = {'apspdcl', 'apepdcl', 'apcpdcl', 'headquarters'}
DEO_OFFICE_FLOW = {
    'headquarters': {
        'received_at': 'jmd_office',
        'received_at_label': 'JMD Office',
        'target_cvo': 'headquarters',
        'target_cvo_label': 'Headquarters (DSP)',
        'force_permission_required': True,
    },
    'apspdcl': {
        'received_at': 'cvo_apspdcl_tirupathi',
        'received_at_label': 'CVO/DSP (APSPDCL) - Tirupathi',
        'target_cvo': 'apspdcl',
        'target_cvo_label': 'APSPDCL (Tirupathi)',
        'force_permission_required': False,
    },
    'apepdcl': {
        'received_at': 'cvo_apepdcl_vizag',
        'received_at_label': 'CVO/DSP (APEPDCL) - Vizag',
        'target_cvo': 'apepdcl',
        'target_cvo_label': 'APEPDCL (Vizag)',
        'force_permission_required': False,
    },
    'apcpdcl': {
        'received_at': 'cvo_apcpdcl_vijayawada',
        'received_at_label': 'CVO/DSP (APCPDCL) - Vijayawada',
        'target_cvo': 'apcpdcl',
        'target_cvo_label': 'APCPDCL (Vijayawada)',
        'force_permission_required': False,
    },
}
DEO_COMBINED_TARGET_FLOW = {
    # APSPDCL DEO handles both APSPDCL and APCPDCL entries.
    'apspdcl': [
        {
            'received_at': 'cvo_apspdcl_tirupathi',
            'received_at_label': 'CVO/DSP (APSPDCL) - Tirupathi',
            'target_cvo': 'apspdcl',
            'target_cvo_label': 'APSPDCL (Tirupathi)',
            'force_permission_required': False,
        },
        {
            'received_at': 'cvo_apcpdcl_vijayawada',
            'received_at_label': 'CVO/DSP (APCPDCL) - Vijayawada',
            'target_cvo': 'apcpdcl',
            'target_cvo_label': 'APCPDCL (Vijayawada)',
            'force_permission_required': False,
        },
    ],
}
PHONE_RE = re.compile(r'^[0-9+\-\s()]{7,20}$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
VALID_DYNAMIC_FIELD_TYPES = {'text', 'textarea', 'select', 'date', 'tel', 'email', 'file'}

DEFAULT_FORM_FIELD_CONFIGS = {
    'deo_petition.received_date': {'label': 'Received Date', 'type': 'date', 'required': True, 'options': []},
    'deo_petition.received_at': {
        'label': 'Received At',
        'type': 'select',
        'required': True,
        'options': [
            {'value': 'jmd_office', 'label': 'JMD Office'},
            {'value': 'cvo_apspdcl_tirupathi', 'label': 'CVO/DSP (APSPDCL) - Tirupathi'},
            {'value': 'cvo_apepdcl_vizag', 'label': 'CVO/DSP (APEPDCL) - Vizag'},
            {'value': 'cvo_apcpdcl_vijayawada', 'label': 'CVO/DSP (APCPDCL) - Vijayawada'},
        ]
    },
    'deo_petition.ereceipt_no': {'label': 'E-Receipt No', 'type': 'text', 'required': False, 'options': []},
    'deo_petition.ereceipt_file': {'label': 'Upload E-Receipt (PDF, max 10MB)', 'type': 'file', 'required': False, 'options': []},
    'deo_petition.target_cvo': {
        'label': 'Target CVO/DSP Jurisdiction',
        'type': 'select',
        'required': False,
        'options': [
            {'value': 'apspdcl', 'label': 'APSPDCL (Tirupathi)'},
            {'value': 'apepdcl', 'label': 'APEPDCL (Vizag)'},
            {'value': 'apcpdcl', 'label': 'APCPDCL (Vijayawada)'},
            {'value': 'headquarters', 'label': 'Headquarters (DSP)'},
        ]
    },
    'deo_petition.permission_request_type': {
        'label': 'Permission Request',
        'type': 'select',
        'required': True,
        'options': [
            {'value': 'direct_enquiry', 'label': 'Direct Enquiry (CVO/DSP sends copy and starts enquiry)'},
            {'value': 'permission_required', 'label': 'Permission Required (CVO/DSP sends to PO for approval)'},
        ]
    },
    'deo_petition.petitioner_name': {'label': 'Petitioner Name', 'type': 'text', 'required': False, 'options': []},
    'deo_petition.contact': {'label': 'Contact Number', 'type': 'tel', 'required': False, 'options': []},
    'deo_petition.place': {'label': 'Place', 'type': 'text', 'required': False, 'options': []},
    'deo_petition.subject': {'label': 'Subject', 'type': 'textarea', 'required': True, 'options': []},
    'deo_petition.petition_type': {
        'label': 'Type of Petition',
        'type': 'select',
        'required': True,
        'options': [
            {'value': 'bribe', 'label': 'Bribe'},
            {'value': 'corruption', 'label': 'Corruption'},
            {'value': 'harassment', 'label': 'Harassment'},
            {'value': 'misconduct', 'label': 'Misconduct'},
            {'value': 'works_related', 'label': 'Works Related'},
            {'value': 'irregularities_in_tenders', 'label': 'Irregularities in Tenders'},
            {'value': 'illegal_assets', 'label': 'Illegal Assets'},
            {'value': 'fake_certificates', 'label': 'Fake Certificates'},
            {'value': 'theft_misappropriation_materials', 'label': 'Theft/Misappropriation of Materials'},
            {'value': 'other', 'label': 'Other'},
        ]
    },
    'deo_petition.source_of_petition': {
        'label': 'Source of Petition',
        'type': 'select',
        'required': True,
        'options': [
            {'value': 'media', 'label': 'Media'},
            {'value': 'public_individual', 'label': 'Public (Individual)'},
            {'value': 'govt', 'label': 'Govt'},
            {'value': 'sumoto', 'label': 'Sumoto'},
            {'value': 'cmd_office', 'label': 'O/o CMD'},
        ]
    },
    'deo_petition.remarks': {'label': 'Remarks', 'type': 'textarea', 'required': False, 'options': []},
    'deo_petition.govt_institution_type': {
        'label': 'Type of Institution',
        'type': 'select',
        'required': True,
        'options': [
            {'value': 'aprc', 'label': '1. APRC'},
            {'value': 'governor', 'label': '2. Governor'},
            {'value': 'cs_energy_department', 'label': '3. CS (Energy Department)'},
            {'value': 'cmd_aptransco', 'label': '4. CMD APTRANSCO'},
            {'value': 'cmo', 'label': '5. CMO'},
            {'value': 'energy_department', 'label': '6. Energy Minister'},
        ]
    },
    'inspector_report.report_text': {'label': 'Conclusion of Enquiry Report', 'type': 'textarea', 'required': True, 'options': []},
    'inspector_report.recommendation': {'label': 'Recommendations / Suggestions', 'type': 'textarea', 'required': True, 'options': []},
    'inspector_report.report_file': {'label': 'Enquiry File (PDF, max 10MB)', 'type': 'file', 'required': True, 'options': []},
    'inspector_report.request_detailed_permission': {
        'label': 'Ask permission to convert this preliminary enquiry into detailed enquiry',
        'type': 'text',
        'required': False,
        'options': []
    },
    'inspector_report.detailed_request_reason': {
        'label': 'Reason for Detailed Enquiry Request',
        'type': 'textarea',
        'required': True,
        'options': []
    },
    'cvo_review.cvo_comments': {'label': 'CVO/DSP Comments on Enquiry Report', 'type': 'textarea', 'required': True, 'options': []},
    'cvo_review.consolidated_report_file': {'label': 'Consolidated Report File (PDF, Optional, max 10MB)', 'type': 'file', 'required': False, 'options': []},
    'cmd_action.action_taken': {'label': 'Action Taken Details', 'type': 'textarea', 'required': True, 'options': []},
    'cmd_action.action_report_file': {'label': 'Upload Action Report Copy (PDF, Optional, max 10MB)', 'type': 'file', 'required': False, 'options': []},
    'po_decision.approve_permission_efile_no': {'label': 'E-Office File No', 'type': 'text', 'required': True, 'options': []},
    'po_decision.reject_permission_reason': {'label': 'Reason for Rejection', 'type': 'textarea', 'required': True, 'options': []},
    'po_decision.send_cmd_instructions': {'label': 'CMD/CGM-HR Instructions', 'type': 'textarea', 'required': False, 'options': []},
    'po_decision.send_cmd_efile_no': {'label': 'E-Office File No', 'type': 'text', 'required': True, 'options': []},
    'po_decision.po_lodge_efile_no': {'label': 'E-Office File No', 'type': 'text', 'required': False, 'options': []},
    'po_decision.po_lodge_remarks': {'label': 'PO Lodge Remarks', 'type': 'textarea', 'required': False, 'options': []},
    'po_decision.po_direct_lodge_efile_no': {'label': 'E-Office File No', 'type': 'text', 'required': False, 'options': []},
    'po_decision.po_direct_lodge_remarks': {'label': 'PO Lodge Remarks', 'type': 'textarea', 'required': False, 'options': []},
    'po_decision.close_comments': {'label': 'Closing Remarks', 'type': 'textarea', 'required': False, 'options': []},
}

FORM_MANAGEMENT_GROUPS = {
    'deo_petition': 'DEO Petition Form',
    'inspector_report': 'Inspector Enquiry Form',
    'cvo_review': 'CVO/DSP Review Form',
    'cmd_action': 'CMD/CGM-HR Action Form',
    'po_decision': 'PO Decision Form',
}


def parse_optional_int(raw_value):
    value = (raw_value or '').strip()
    if not value:
        return None
    try:
        parsed = int(value)
        return parsed if parsed > 0 else None
    except (TypeError, ValueError):
        return None


def parse_date_input(value):
    text = (value or '').strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, '%Y-%m-%d').date()
    except ValueError:
        return None


def reset_login_captcha():
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    session['login_captcha_a'] = a
    session['login_captcha_b'] = b
    session['login_captcha_answer'] = a + b
    return a, b


def get_login_captcha():
    a = session.get('login_captcha_a')
    b = session.get('login_captcha_b')
    ans = session.get('login_captcha_answer')
    if a is None or b is None or ans is None:
        return reset_login_captcha()
    return a, b


def validate_login_captcha(raw_answer):
    try:
        provided = int((raw_answer or '').strip())
    except (TypeError, ValueError):
        return False
    expected = session.get('login_captcha_answer')
    return expected is not None and provided == expected


def get_deo_office_flow(user_role, cvo_office):
    if user_role != 'data_entry':
        return None
    office = (cvo_office or '').strip().lower()
    return DEO_OFFICE_FLOW.get(office)


def get_deo_target_options(user_role, cvo_office):
    if user_role != 'data_entry':
        return []
    office = (cvo_office or '').strip().lower()
    merged = DEO_COMBINED_TARGET_FLOW.get(office)
    if merged:
        return merged
    flow = DEO_OFFICE_FLOW.get(office)
    return [flow] if flow else []


def validate_pdf_upload(file_obj, label):
    if not file_obj or not file_obj.filename:
        return True, None

    original_name = secure_filename(file_obj.filename or '')
    if not original_name:
        return False, f'{label} filename is invalid.'

    ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else ''
    if ext != 'pdf':
        return False, f'{label} must be PDF format.'

    file_obj.seek(0, os.SEEK_END)
    file_size = file_obj.tell()
    file_obj.seek(0)
    if file_size <= 0:
        return False, f'{label} is empty.'
    if file_size > MAX_UPLOAD_SIZE_BYTES:
        return False, f'{label} must be below {config.MAX_UPLOAD_SIZE_MB} MB.'

    header = file_obj.read(5)
    file_obj.seek(0)
    if header != b'%PDF-':
        return False, f'{label} is not a valid PDF file.'

    return True, original_name


def validate_contact(contact):
    if not contact:
        return True
    return bool(PHONE_RE.match(contact))


def validate_email(email):
    if not email:
        return True
    return bool(EMAIL_RE.match(email))


def ensure_upload_dirs():
    os.makedirs(ERECEIPT_UPLOAD_DIR, exist_ok=True)
    os.makedirs(ENQUIRY_UPLOAD_DIR, exist_ok=True)
    os.makedirs(PROFILE_UPLOAD_DIR, exist_ok=True)


def validate_profile_photo_upload(file_obj, user_id=None):
    if not file_obj or not file_obj.filename:
        return True, None, None

    safe_name = secure_filename(file_obj.filename)
    if not safe_name:
        return False, None, 'Profile photo filename is invalid.'

    ext = safe_name.rsplit('.', 1)[-1].lower() if '.' in safe_name else ''
    if ext not in PROFILE_PHOTO_EXTENSIONS:
        return False, None, 'Profile photo must be jpg, jpeg, png, or webp.'

    file_obj.seek(0, os.SEEK_END)
    size = file_obj.tell()
    file_obj.seek(0)
    if size <= 0:
        return False, None, 'Profile photo file is empty.'
    if size > PROFILE_PHOTO_MAX_BYTES:
        return False, None, 'Profile photo must be below 2 MB.'

    photo_user_id = user_id if user_id is not None else session.get('user_id', 'x')
    stored_name = f"user_{photo_user_id}_{uuid4().hex}.{ext}"
    return True, stored_name, None


def delete_profile_photo_file(filename):
    if not filename:
        return
    path = os.path.join(PROFILE_UPLOAD_DIR, filename)
    try:
        if os.path.isfile(path):
            os.remove(path)
    except Exception:
        pass


def refresh_session_user():
    user_id = session.get('user_id')
    if not user_id:
        return
    user = models.get_user_by_id(user_id)
    if not user:
        return
    session['username'] = user.get('username')
    session['full_name'] = user.get('full_name')
    session['user_role'] = user.get('role')
    session['cvo_office'] = user.get('cvo_office')
    session['phone'] = user.get('phone')
    session['email'] = user.get('email')
    session['profile_photo'] = user.get('profile_photo')


ensure_upload_dirs()


def get_effective_form_field_configs():
    if has_request_context():
        cached_cfg = getattr(g, '_effective_form_field_configs', None)
        if isinstance(cached_cfg, dict):
            return cached_cfg

    merged = copy.deepcopy(DEFAULT_FORM_FIELD_CONFIGS)
    try:
        overrides = models.get_form_field_configs()
    except Exception:
        overrides = {}

    for key, override in overrides.items():
        if key not in merged:
            continue
        if isinstance(override, dict):
            if override.get('label'):
                merged[key]['label'] = str(override.get('label')).strip() or merged[key]['label']
            field_type = (override.get('type') or '').strip()
            if field_type in VALID_DYNAMIC_FIELD_TYPES:
                merged[key]['type'] = field_type
            merged[key]['required'] = bool(override.get('required'))
            if merged[key]['type'] == 'select':
                options = override.get('options')
                if isinstance(options, list) and options:
                    valid_options = []
                    for opt in options:
                        if not isinstance(opt, dict):
                            continue
                        value = str(opt.get('value', '')).strip()
                        label = str(opt.get('label', '')).strip()
                        if value and label:
                            valid_options.append({'value': value, 'label': label})
                    if valid_options:
                        merged[key]['options'] = valid_options
    if has_request_context():
        g._effective_form_field_configs = merged
    return merged


def get_petitions_for_user_cached(user_id, user_role, cvo_office=None, status_filter=None, enquiry_mode='all'):
    if not has_request_context():
        return models.get_petitions_for_user(user_id, user_role, cvo_office, status_filter, enquiry_mode)

    cache = getattr(g, '_petitions_for_user_cache', None)
    if not isinstance(cache, dict):
        cache = {}
        g._petitions_for_user_cache = cache

    cache_key = (user_id, user_role, cvo_office, status_filter, enquiry_mode)
    if cache_key not in cache:
        cache[cache_key] = models.get_petitions_for_user(
            user_id, user_role, cvo_office, status_filter, enquiry_mode
        )
    return cache[cache_key]


def get_form_field_config(form_key, field_key):
    key = f'{form_key}.{field_key}'
    return get_effective_form_field_configs().get(key, {'label': field_key, 'type': 'text', 'required': False, 'options': []})


def resolve_efile_no_for_action(petition, incoming_efile_no, required_message=None):
    existing_efile = (petition.get('efile_no') or '').strip() if petition else ''
    incoming = (incoming_efile_no or '').strip()

    if existing_efile:
        if incoming and incoming != existing_efile:
            return None, 'E-Office File No is already set. Editing is not allowed.'
        return existing_efile, None

    if not incoming:
        if required_message:
            return None, required_message
        return None, None

    if len(incoming) > 100:
        return None, 'E-Office File No is too long.'

    return incoming, None


# ========================================
# AUTH DECORATORS
# ========================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_role' not in session or session['user_role'] not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ========================================
# CONTEXT PROCESSOR
# ========================================

@app.context_processor
def inject_globals():
    role_labels = {
        'super_admin': 'Super Admin',
        'data_entry': 'Data Entry Operator',
        'po': 'Personal Officer (Vigilance)',
        'cmd_apspdcl': 'CMD - APSPDCL',
        'cmd_apepdcl': 'CMD - APEPDCL',
        'cmd_apcpdcl': 'CMD - APCPDCL',
        'cgm_hr_transco': 'CGM/HR TRANSCO (Headquarters)',
        'dsp': 'DSP (Deputy Superintendent of Police) - Headquarters',
        'cvo_apspdcl': 'CVO/DSP - APSPDCL (Tirupathi)',
        'cvo_apepdcl': 'CVO/DSP - APEPDCL (Vizag)',
        'cvo_apcpdcl': 'CVO/DSP - APCPDCL (Vijayawada)',
        'inspector': 'Field Inspector (CI/SI)'
    }
    status_labels = {
        'received': 'Received',
        'forwarded_to_cvo': 'Forwarded to CVO/DSP',
        'sent_for_permission': 'Sent for Permission',
        'permission_approved': 'Permission Approved',
        'permission_rejected': 'Permission Rejected',
        'assigned_to_inspector': 'Assigned to Inspector',
        'sent_back_for_reenquiry': 'Sent Back for Re-enquiry',
        'enquiry_in_progress': 'Enquiry In Progress',
        'enquiry_report_submitted': 'Enquiry Report Submitted',
        'cvo_comments_added': 'CVO/DSP Comments Added',
        'forwarded_to_jmd': 'Forwarded to PO (Legacy)',
        'forwarded_to_po': 'Forwarded to PO',
        'conclusion_given': 'Conclusion Given',
        'action_instructed': 'Sent to CMD for Action',
        'action_taken': 'CMD Action Report Submitted',
        'lodged': 'Lodged',
        'closed': 'Closed'
    }
    status_colors = {
        'received': '#3b82f6',
        'forwarded_to_cvo': '#8b5cf6',
        'sent_for_permission': '#f59e0b',
        'permission_approved': '#10b981',
        'permission_rejected': '#ef4444',
        'assigned_to_inspector': '#6366f1',
        'sent_back_for_reenquiry': '#f97316',
        'enquiry_in_progress': '#0ea5e9',
        'enquiry_report_submitted': '#14b8a6',
        'cvo_comments_added': '#8b5cf6',
        'forwarded_to_jmd': '#f97316',
        'forwarded_to_po': '#ec4899',
        'conclusion_given': '#84cc16',
        'action_instructed': '#06b6d4',
        'action_taken': '#22c55e',
        'lodged': '#0ea5e9',
        'closed': '#6b7280'
    }
    workflow_stage_labels = {
        1: 'Petition Initiated',
        2: 'Enquiry in Progress',
        3: 'Report Finalized & Submitted',
        4: 'Action Pending',
        5: 'Petition Lodged',
        6: 'Petition Closed'
    }
    status_to_stage = {
        'received': 1,
        'forwarded_to_cvo': 1,
        'sent_for_permission': 1,
        'permission_approved': 1,
        'permission_rejected': 1,
        'assigned_to_inspector': 2,
        'sent_back_for_reenquiry': 2,
        'enquiry_in_progress': 2,
        'enquiry_report_submitted': 3,
        'cvo_comments_added': 3,
        'forwarded_to_po': 3,
        'forwarded_to_jmd': 3,
        'action_instructed': 4,
        'action_taken': 4,
        'lodged': 5,
        'closed': 6
    }
    petition_types = PETITION_TYPE_LABELS
    petition_sources = {
        'media': 'Media',
        'public_individual': 'Public (Individual)',
        'govt': 'Govt',
        'sumoto': 'Sumoto',
        'cmd_office': 'O/o CMD',
    }
    cfg = get_effective_form_field_configs()
    govt_options = cfg.get('deo_petition.govt_institution_type', {}).get('options', [])
    govt_labels = {o.get('value'): o.get('label') for o in govt_options if isinstance(o, dict)}
    profile_photo = session.get('profile_photo')
    notification = {
        'received_count': 0,
        'pending_count': 0,
        'badge_count': 0,
        'badge_text': '0',
        'items': [],
    }
    user_id = session.get('user_id')
    user_role = session.get('user_role')
    if user_id and user_role:
        try:
            visible_petitions = get_petitions_for_user_cached(
                user_id, user_role, session.get('cvo_office'), status_filter=None
            )
            # Show notifications only for items that are currently in this login's queue.
            pending_in_login = [
                p for p in visible_petitions
                if p.get('status') != 'closed' and p.get('current_handler_id') == user_id
            ]
            received_petitions = [p for p in pending_in_login if p.get('status') == 'received']
            notification['received_count'] = len(received_petitions)
            notification['pending_count'] = len(pending_in_login)
            notification['badge_count'] = notification['pending_count']
            notification['badge_text'] = '9+' if notification['badge_count'] > 9 else str(notification['badge_count'])
            notification['items'] = [
                {
                    'id': p.get('id'),
                    'sno': p.get('sno') or f"#{p.get('id')}",
                    'status_label': status_labels.get(p.get('status'), str(p.get('status') or '-').replace('_', ' ').title()),
                    'subject': p.get('subject') or 'No subject',
                    'received_date': p.get('received_date').strftime('%d/%m/%Y') if p.get('received_date') else '-',
                }
                for p in pending_in_login[:6]
                if p.get('id')
            ]
        except Exception:
            pass
    return dict(
        brand_name=config.BRAND_NAME,
        brand_subtitle=config.BRAND_SUBTITLE,
        brand_logo_file=config.BRAND_LOGO_FILE,
        brand_logo_fallback=config.BRAND_LOGO_FALLBACK,
        role_labels=role_labels,
        status_labels=status_labels,
        status_colors=status_colors,
        petition_types=petition_types,
        petition_sources=petition_sources,
        govt_institution_labels=govt_labels,
        get_field_cfg=lambda form_key, field_key: cfg.get(
            f'{form_key}.{field_key}',
            {'label': field_key, 'type': 'text', 'required': False, 'options': []}
        ),
        workflow_stage_labels=workflow_stage_labels,
        status_to_stage=status_to_stage,
        current_user_role=session.get('user_role'),
        current_user_username=session.get('username'),
        current_user_name=session.get('full_name'),
        current_user_id=session.get('user_id'),
        current_user_phone=session.get('phone'),
        current_user_email=session.get('email'),
        current_user_profile_photo=session.get('profile_photo'),
        current_user_profile_photo_url=(
            url_for('profile_photo_file', filename=profile_photo) if profile_photo else None
        ),
        notification=notification,
        now=datetime.now()
    )

# ========================================
# AUTH ROUTES
# ========================================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    landing_stats = {
        'petitions_tracked': 0,
        'offices_covered': 0,
        'resolution_rate': 0,
        'active_monitoring': 0,
    }
    live_status = {
        'resolved_today': 0,
        'under_review': 0,
        'urgent_pending': 0,
    }
    try:
        petitions = models.get_all_petitions()
        today = date.today()
        total_petitions = len(petitions)
        closed_petitions = sum(1 for p in petitions if p.get('status') == 'closed')
        office_keys = set()
        review_statuses = {
            'forwarded_to_cvo',
            'sent_for_permission',
            'permission_approved',
            'assigned_to_inspector',
            'sent_back_for_reenquiry',
            'enquiry_in_progress',
            'enquiry_report_submitted',
            'cvo_comments_added',
            'forwarded_to_po',
            'forwarded_to_jmd',
            'action_instructed',
        }
        urgent_age_days = 30
        resolved_today = 0
        under_review = 0
        urgent_pending = 0

        for petition in petitions:
            for key in ('target_cvo', 'received_at'):
                raw_value = petition.get(key)
                value = str(raw_value).strip() if raw_value is not None else ''
                if value:
                    office_keys.add(value)
            status = petition.get('status')
            if status in review_statuses:
                under_review += 1
            updated_at = petition.get('updated_at')
            if status == 'closed' and updated_at and getattr(updated_at, 'date', None):
                if updated_at.date() == today:
                    resolved_today += 1
            if status != 'closed':
                received_date = petition.get('received_date')
                if received_date and ((today - received_date).days >= urgent_age_days):
                    urgent_pending += 1

        landing_stats = {
            'petitions_tracked': total_petitions,
            'offices_covered': len(office_keys),
            'resolution_rate': int(round((closed_petitions / total_petitions) * 100)) if total_petitions else 0,
            'active_monitoring': max(0, total_petitions - closed_petitions),
        }
        live_status = {
            'resolved_today': resolved_today,
            'under_review': under_review,
            'urgent_pending': urgent_pending,
        }
    except Exception:
        # Keep landing page accessible even if database is not reachable.
        pass

    return render_template('landing.html', landing_stats=landing_stats, live_status=live_status)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET' and request.args.get('refresh_captcha') == '1':
        reset_login_captcha()

    if request.method == 'POST':
        if not validate_login_captcha(request.form.get('captcha_answer')):
            flash('Captcha answer is incorrect.', 'warning')
            reset_login_captcha()
            a, b = get_login_captcha()
            return render_template('login.html', captcha_a=a, captcha_b=b)

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = models.authenticate_user(username, password)
        if user:
            if user['role'] == 'jmd':
                flash('JMD login is disabled. Please login using PO credentials.', 'warning')
                reset_login_captcha()
                return redirect(url_for('login'))
            session.pop('login_captcha_a', None)
            session.pop('login_captcha_b', None)
            session.pop('login_captcha_answer', None)
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['user_role'] = user['role']
            session['cvo_office'] = user.get('cvo_office')
            session['phone'] = user.get('phone')
            session['email'] = user.get('email')
            session['profile_photo'] = user.get('profile_photo')
            flash(f'Welcome, {user["full_name"]}!', 'success')
            return redirect(url_for('dashboard'))

        flash('Invalid username or password.', 'danger')
        reset_login_captcha()

    a, b = get_login_captcha()
    return render_template('login.html', captcha_a=a, captcha_b=b)


@app.route('/auth/request-signup', methods=['POST'])
def request_signup():
    flash('Self signup is disabled. Contact Super Admin to create your account.', 'warning')
    return redirect(url_for('login'))


@app.route('/auth/request-recovery', methods=['POST'])
def request_recovery():
    username = (request.form.get('recovery_username') or '').strip()
    new_password = request.form.get('recovery_password', '').strip()
    confirm_password = request.form.get('recovery_confirm_password', '').strip()

    if not username:
        flash('Username is required for password recovery.', 'warning')
        return redirect(url_for('login'))
    if len(new_password) < 6:
        flash('New password must be at least 6 characters.', 'warning')
        return redirect(url_for('login'))
    if new_password != confirm_password:
        flash('Password and confirm password do not match.', 'warning')
        return redirect(url_for('login'))

    try:
        models.create_password_reset_request(username, new_password)
        flash('Password recovery request submitted. Wait for Super Admin approval.', 'success')
    except Exception as e:
        error_text = str(e).lower()
        if 'not found' in error_text:
            flash('Username not found.', 'warning')
        else:
            flash(f'Unable to submit recovery request: {str(e)}', 'danger')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ========================================
# DASHBOARD
# ========================================

@app.route('/dashboard')
@login_required
def dashboard():
    user_role = session['user_role']
    user_id = session['user_id']
    cvo_office = session.get('cvo_office')

    petitions = get_petitions_for_user_cached(user_id, user_role, cvo_office)
    officer_lookup = {}
    for p in petitions:
        officer_id = p.get('assigned_inspector_id')
        officer_name = (p.get('inspector_name') or '').strip()
        if officer_id and officer_name:
            officer_lookup[int(officer_id)] = officer_name
    officer_options = [
        {'id': oid, 'name': name}
        for oid, name in sorted(officer_lookup.items(), key=lambda x: x[1].lower())
    ]
    dashboard_filter = _extract_dashboard_filters(request.args, officer_lookup)
    filtered_petitions = _apply_dashboard_filters(petitions, dashboard_filter)

    petition_type_labels = PETITION_TYPE_LABELS
    source_labels = {
        'media': 'Media',
        'public_individual': 'Public (Individual)',
        'govt': 'Govt',
        'sumoto': 'Sumoto',
        'cmd_office': 'O/o CMD',
    }
    office_labels = {
        'jmd_office': 'PO Office',
        'cvo_apspdcl_tirupathi': 'CVO/DSP APSPDCL',
        'cvo_apepdcl_vizag': 'CVO/DSP APEPDCL',
        'cvo_apcpdcl_vijayawada': 'CVO/DSP APCPDCL',
    }
    cvo_labels = {
        'apspdcl': 'APSPDCL',
        'apepdcl': 'APEPDCL',
        'apcpdcl': 'APCPDCL',
        'headquarters': 'Headquarters',
    }
    active_filter_labels = []
    if dashboard_filter['from_date']:
        active_filter_labels.append(f"From: {dashboard_filter['from_date'].strftime('%d %b %Y')}")
    if dashboard_filter['to_date']:
        active_filter_labels.append(f"To: {dashboard_filter['to_date'].strftime('%d %b %Y')}")
    if dashboard_filter['petition_type'] != 'all':
        active_filter_labels.append(f"Type: {petition_type_labels.get(dashboard_filter['petition_type'], dashboard_filter['petition_type'])}")
    if dashboard_filter['source_of_petition'] != 'all':
        active_filter_labels.append(f"Source: {source_labels.get(dashboard_filter['source_of_petition'], dashboard_filter['source_of_petition'])}")
    if dashboard_filter['received_at'] != 'all':
        active_filter_labels.append(f"Received: {office_labels.get(dashboard_filter['received_at'], dashboard_filter['received_at'])}")
    if dashboard_filter['target_cvo'] != 'all':
        active_filter_labels.append(f"Office: {cvo_labels.get(dashboard_filter['target_cvo'], dashboard_filter['target_cvo'])}")
    if dashboard_filter['officer_id']:
        active_filter_labels.append(f"Officer: {officer_lookup.get(dashboard_filter['officer_id'], str(dashboard_filter['officer_id']))}")

    stats = _build_filtered_dashboard_stats(user_role, user_id, petitions, filtered_petitions)
    analytics = _build_dashboard_analytics([], {'sla_within': 0, 'sla_breached': 0})

    total_items = len(filtered_petitions)
    page_size = min(100, max(10, parse_optional_int(request.args.get('page_size')) or 20))
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    page = min(total_pages, max(1, parse_optional_int(request.args.get('page')) or 1))
    start = (page - 1) * page_size
    end = start + page_size
    paged_petitions = filtered_petitions[start:end]

    return render_template(
        'dashboard.html',
        stats=stats,
        petitions=paged_petitions,
        analytics=analytics,
        officer_options=officer_options,
        dashboard_filter={
            'from_date': dashboard_filter['from_date'].strftime('%Y-%m-%d') if dashboard_filter['from_date'] else '',
            'to_date': dashboard_filter['to_date'].strftime('%Y-%m-%d') if dashboard_filter['to_date'] else '',
            'petition_type': dashboard_filter['petition_type'],
            'source_of_petition': dashboard_filter['source_of_petition'],
            'received_at': dashboard_filter['received_at'],
            'target_cvo': dashboard_filter['target_cvo'],
            'officer_id': str(dashboard_filter['officer_id']) if dashboard_filter['officer_id'] else 'all',
            'page': page,
            'page_size': page_size,
        },
        dashboard_active_filter_count=len(active_filter_labels),
        dashboard_active_filter_labels=active_filter_labels,
        dashboard_pagination={
            'page': page,
            'page_size': page_size,
            'total_items': total_items,
            'total_pages': total_pages,
            'start_item': (start + 1) if total_items else 0,
            'end_item': min(end, total_items),
        }
    )


def _extract_dashboard_filters(args, officer_lookup):
    from_date = parse_date_input(args.get('from_date'))
    to_date = parse_date_input(args.get('to_date'))
    if from_date and to_date and from_date > to_date:
        from_date, to_date = to_date, from_date

    petition_type_filter = (args.get('petition_type') or 'all').strip()
    if petition_type_filter not in PETITION_TYPE_LABELS and petition_type_filter != 'all':
        petition_type_filter = 'all'
    source_filter = (args.get('source_of_petition') or 'all').strip()
    if source_filter not in VALID_SOURCE_OF_PETITION and source_filter != 'all':
        source_filter = 'all'
    received_at_filter = (args.get('received_at') or 'all').strip()
    if received_at_filter not in VALID_RECEIVED_AT and received_at_filter != 'all':
        received_at_filter = 'all'
    target_cvo_filter = (args.get('target_cvo') or 'all').strip()
    if target_cvo_filter not in VALID_TARGET_CVO and target_cvo_filter != 'all':
        target_cvo_filter = 'all'

    officer_filter = None
    officer_filter_raw = (args.get('officer_id') or 'all').strip()
    if officer_filter_raw != 'all':
        parsed_officer = parse_optional_int(officer_filter_raw)
        if parsed_officer in officer_lookup:
            officer_filter = parsed_officer

    return {
        'from_date': from_date,
        'to_date': to_date,
        'petition_type': petition_type_filter,
        'source_of_petition': source_filter,
        'received_at': received_at_filter,
        'target_cvo': target_cvo_filter,
        'officer_id': officer_filter,
    }


def _apply_dashboard_filters(petitions, filters):
    filtered = []
    for p in petitions:
        received_date = p.get('received_date')
        if filters['from_date'] and (not received_date or received_date < filters['from_date']):
            continue
        if filters['to_date'] and (not received_date or received_date > filters['to_date']):
            continue
        if filters['petition_type'] != 'all' and p.get('petition_type') != filters['petition_type']:
            continue
        if filters['source_of_petition'] != 'all' and p.get('source_of_petition') != filters['source_of_petition']:
            continue
        if filters['received_at'] != 'all' and p.get('received_at') != filters['received_at']:
            continue
        if filters['target_cvo'] != 'all' and p.get('target_cvo') != filters['target_cvo']:
            continue
        if filters['officer_id'] and int(p.get('assigned_inspector_id') or 0) != filters['officer_id']:
            continue
        filtered.append(p)
    return filtered


def _build_filtered_dashboard_stats(user_role, user_id, all_petitions, filtered_petitions):
    base_stats = {
        'total_visible': len(all_petitions),
    }
    base_stats.update(models._get_workflow_stage_stats(all_petitions))  # type: ignore[attr-defined]
    base_stats.update(models._get_sla_stats_for_petitions(all_petitions))  # type: ignore[attr-defined]
    base_stats['kpi_cards'] = models._build_role_kpi_cards(user_role, all_petitions, user_id)  # type: ignore[attr-defined]
    filtered_stats = dict(base_stats)
    filtered_stats['total_visible'] = len(filtered_petitions)
    filtered_stats['kpi_cards'] = models._build_role_kpi_cards(user_role, filtered_petitions, user_id)  # type: ignore[attr-defined]
    filtered_stats.update(models._get_workflow_stage_stats(filtered_petitions))  # type: ignore[attr-defined]

    # Keep original SLA stats when no filters are applied; otherwise recompute on filtered set.
    if len(filtered_petitions) != len(all_petitions):
        filtered_stats.update(models._get_sla_stats_for_petitions(filtered_petitions))  # type: ignore[attr-defined]
    return filtered_stats


def _build_dashboard_analytics(petitions, stats):
    status_labels = {
        'received': 'Received',
        'forwarded_to_cvo': 'Forwarded to CVO/DSP',
        'sent_for_permission': 'Sent for Permission',
        'permission_approved': 'Permission Approved',
        'permission_rejected': 'Permission Rejected',
        'assigned_to_inspector': 'Assigned to Field Officer',
        'sent_back_for_reenquiry': 'Sent Back for Re-enquiry',
        'enquiry_in_progress': 'Enquiry In Progress',
        'enquiry_report_submitted': 'Report Submitted',
        'cvo_comments_added': 'CVO/DSP Comments Added',
        'forwarded_to_po': 'Forwarded to PO',
        'action_instructed': 'Action Pending at CMD',
        'action_taken': 'Action Taken by CMD',
        'lodged': 'Lodged',
        'closed': 'Closed'
    }
    petition_type_labels = PETITION_TYPE_LABELS
    source_labels = {
        'media': 'Media',
        'public_individual': 'Public',
        'govt': 'Govt',
        'sumoto': 'Sumoto',
        'cmd_office': 'O/o CMD',
    }

    now = datetime.now()
    months = []
    for i in range(5, -1, -1):
        m = now.month - i
        y = now.year
        while m <= 0:
            m += 12
            y -= 1
        key = f"{y:04d}-{m:02d}"
        months.append({
            'key': key,
            'label': datetime(y, m, 1).strftime('%b %Y'),
            'value': 0
        })
    month_index = {m['key']: m for m in months}

    status_counts = Counter()
    type_counts = Counter()
    source_counts = Counter()
    permission_mode_counts = Counter({'Direct': 0, 'Permission': 0})
    office_counts = Counter()
    officer_counts = Counter()
    officer_label_by_id = {}

    for p in petitions:
        status = p.get('status')
        if status:
            status_counts[status_labels.get(status, status.replace('_', ' ').title())] += 1

        ptype = p.get('petition_type')
        if ptype:
            type_counts[petition_type_labels.get(ptype, ptype.replace('_', ' ').title())] += 1

        source = p.get('source_of_petition')
        if source:
            source_counts[source_labels.get(source, source.replace('_', ' ').title())] += 1

        permission_mode_counts['Permission' if p.get('requires_permission') else 'Direct'] += 1

        received_at = p.get('received_at') or 'unknown'
        office_counts[str(received_at)] += 1
        officer_id = p.get('assigned_inspector_id')
        officer_name = (p.get('inspector_name') or '').strip()
        if officer_id and officer_name:
            oid = str(officer_id)
            officer_label_by_id[oid] = officer_name
            officer_counts[oid] += 1

        rd = p.get('received_date')
        if rd:
            month_key = rd.strftime('%Y-%m')
            if month_key in month_index:
                month_index[month_key]['value'] += 1

    def _counter_to_series(counter_obj, limit=8):
        series = sorted(counter_obj.items(), key=lambda x: x[1], reverse=True)
        if limit:
            series = series[:limit]
        return {
            'labels': [x[0] for x in series],
            'values': [x[1] for x in series]
        }

    officer_series = sorted(officer_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    return {
        'monthly_trend': {
            'keys': [m['key'] for m in months],
            'labels': [m['label'] for m in months],
            'values': [m['value'] for m in months]
        },
        'status_split': _counter_to_series(status_counts, limit=10),
        'type_split': _counter_to_series(type_counts, limit=8),
        'source_split': _counter_to_series(source_counts, limit=8),
        'enquiry_mode_split': _counter_to_series(permission_mode_counts, limit=0),
        'office_split': _counter_to_series(office_counts, limit=6),
        'officer_split': {
            'keys': [k for k, _ in officer_series],
            'labels': [officer_label_by_id.get(k, f'Officer {k}') for k, _ in officer_series],
            'values': [v for _, v in officer_series],
        },
        'summary': {
            'total_visible': len(petitions),
            'closed': status_counts.get('Closed', 0),
            'lodged': status_counts.get('Lodged', 0),
            'active': max(0, len(petitions) - status_counts.get('Closed', 0)),
            'sla_within': stats.get('sla_within', 0),
            'sla_breached': stats.get('sla_breached', 0),
        }
    }

# ========================================
# PETITION ROUTES
# ========================================

@app.route('/petitions')
@login_required
def petitions_list():
    status_filter = request.args.get('status', 'all')
    enquiry_mode = request.args.get('mode', 'all')
    user_role = session['user_role']
    user_id = session['user_id']
    
    if user_role == 'super_admin':
        petitions = models.get_all_petitions(status_filter, enquiry_mode)
    else:
        petitions = models.get_petitions_for_user(user_id, user_role, session.get('cvo_office'), status_filter, enquiry_mode)
    
    return render_template('petitions_list.html', petitions=petitions, status_filter=status_filter, enquiry_mode=enquiry_mode)

@app.route('/petitions/new', methods=['GET', 'POST'])
@login_required
@role_required('super_admin', 'data_entry')
def petition_new():
    deo_flow = get_deo_office_flow(session.get('user_role'), session.get('cvo_office'))
    deo_target_options = get_deo_target_options(session.get('user_role'), session.get('cvo_office'))
    deo_target_map = {opt.get('target_cvo'): opt for opt in deo_target_options if isinstance(opt, dict)}
    show_cmd_source_option = (
        session.get('user_role') == 'data_entry' and
        (session.get('cvo_office') or '').strip().lower() in ('apepdcl', 'apspdcl')
    )

    def render_petition_form():
        return render_template(
            'petition_form.html',
            deo_flow=deo_flow,
            deo_target_options=deo_target_options,
            show_cmd_source_option=show_cmd_source_option,
        )

    if request.method == 'POST':
        ereceipt_no = request.form.get('ereceipt_no', '').strip() or None
        ereceipt_file = request.files.get('ereceipt_file')
        ereceipt_filename = None

        petitioner_name = request.form.get('petitioner_name', '').strip()
        contact = request.form.get('contact', '').strip()
        place = request.form.get('place', '').strip()
        subject = request.form.get('subject', '').strip()
        petition_type = (request.form.get('petition_type') or '').strip()
        source_of_petition = (request.form.get('source_of_petition') or '').strip()
        govt_institution_type = (request.form.get('govt_institution_type') or '').strip()
        received_at = (request.form.get('received_at') or '').strip()
        target_cvo = (request.form.get('target_cvo') or '').strip()
        permission_request_type = (request.form.get('permission_request_type') or '').strip()

        if session.get('user_role') == 'data_entry':
            if not deo_target_options:
                flash('DEO office mapping is missing. Please contact admin.', 'danger')
                return render_petition_form()
            selected_target = (target_cvo or '').strip()
            if len(deo_target_options) == 1 and not selected_target:
                selected_target = deo_target_options[0].get('target_cvo')
            selected_flow = deo_target_map.get(selected_target)
            if not selected_flow:
                flash('Please select a valid target CVO/DSP office.', 'warning')
                return render_petition_form()
            received_at = selected_flow['received_at']
            target_cvo = selected_flow['target_cvo']
            permission_request_type = 'permission_required' if selected_flow.get('force_permission_required') else 'direct_enquiry'

        is_jmd_received = (received_at == 'jmd_office')
        received_date_raw = request.form.get('received_date')
        received_date = parse_date_input(received_date_raw)
        remarks = request.form.get('remarks', '').strip()
        petition_cfg = get_effective_form_field_configs()
        cfg_received_date = petition_cfg.get('deo_petition.received_date', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.received_date'])
        cfg_received_at = petition_cfg.get('deo_petition.received_at', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.received_at'])
        cfg_ereceipt_no = petition_cfg.get('deo_petition.ereceipt_no', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.ereceipt_no'])
        cfg_ereceipt_file = petition_cfg.get('deo_petition.ereceipt_file', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.ereceipt_file'])
        cfg_target_cvo = petition_cfg.get('deo_petition.target_cvo', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.target_cvo'])
        cfg_permission_request = petition_cfg.get('deo_petition.permission_request_type', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.permission_request_type'])
        cfg_petitioner = petition_cfg.get('deo_petition.petitioner_name', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.petitioner_name'])
        cfg_contact = petition_cfg.get('deo_petition.contact', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.contact'])
        cfg_place = petition_cfg.get('deo_petition.place', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.place'])
        cfg_subject = petition_cfg.get('deo_petition.subject', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.subject'])
        cfg_petition_type = petition_cfg.get('deo_petition.petition_type', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.petition_type'])
        cfg_source = petition_cfg.get('deo_petition.source_of_petition', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.source_of_petition'])
        cfg_remarks = petition_cfg.get('deo_petition.remarks', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.remarks'])
        cfg_govt_institution = petition_cfg.get('deo_petition.govt_institution_type', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.govt_institution_type'])

        if cfg_received_date.get('required') and not received_date:
            flash(f"{cfg_received_date.get('label', 'Received Date')} is required.", 'warning')
            return render_petition_form()
        if received_date_raw and not received_date:
            flash(f"Please provide a valid {cfg_received_date.get('label', 'Received Date').lower()}.", 'warning')
            return render_petition_form()
        if cfg_received_at.get('required') and not received_at:
            flash(f"{cfg_received_at.get('label', 'Received At')} is required.", 'warning')
            return render_petition_form()
        if received_at not in VALID_RECEIVED_AT:
            flash(f"Please select a valid {cfg_received_at.get('label', 'Received At')}.", 'warning')
            return render_petition_form()
        if not subject:
            flash(f"{cfg_subject.get('label', 'Subject')} is required.", 'warning')
            return render_petition_form()
        if cfg_petition_type.get('required') and not petition_type:
            flash(f"{cfg_petition_type.get('label', 'Type of Petition')} is required.", 'warning')
            return render_petition_form()
        if petition_type not in VALID_PETITION_TYPES:
            flash(f"Please select a valid {cfg_petition_type.get('label', 'Type of Petition')}.", 'warning')
            return render_petition_form()
        if cfg_source.get('required') and not source_of_petition:
            flash(f"{cfg_source.get('label', 'Source of Petition')} is required.", 'warning')
            return render_petition_form()
        if source_of_petition not in VALID_SOURCE_OF_PETITION:
            flash(f"Please select a valid {cfg_source.get('label', 'Source of Petition')}.", 'warning')
            return render_petition_form()
        if source_of_petition == 'cmd_office' and not show_cmd_source_option:
            flash('O/o CMD source is allowed only for APSPDCL/APEPDCL DEO login.', 'warning')
            return render_petition_form()
        govt_option_values = {o.get('value') for o in cfg_govt_institution.get('options', []) if isinstance(o, dict)}
        if source_of_petition == 'govt' and cfg_govt_institution.get('required') and not govt_institution_type:
            flash(f"Please select {cfg_govt_institution.get('label', 'Type of Institution')}.", 'warning')
            return render_petition_form()
        if source_of_petition == 'govt' and govt_institution_type and govt_institution_type not in govt_option_values:
            flash('Please select a valid Govt institution type.', 'warning')
            return render_petition_form()
        if cfg_petitioner.get('required') and not petitioner_name:
            flash(f"{cfg_petitioner.get('label', 'Petitioner Name')} is required.", 'warning')
            return render_petition_form()
        if cfg_contact.get('required') and not contact:
            flash(f"{cfg_contact.get('label', 'Contact Number')} is required.", 'warning')
            return render_petition_form()
        if cfg_place.get('required') and not place:
            flash(f"{cfg_place.get('label', 'Place')} is required.", 'warning')
            return render_petition_form()
        if cfg_remarks.get('required') and not remarks:
            flash(f"{cfg_remarks.get('label', 'Remarks')} is required.", 'warning')
            return render_petition_form()
        if not is_jmd_received:
            if cfg_permission_request.get('required') and not permission_request_type:
                flash(f"{cfg_permission_request.get('label', 'Permission Request')} is required.", 'warning')
                return render_petition_form()
            if permission_request_type not in VALID_PERMISSION_REQUEST_TYPES:
                flash(f"Please select a valid {cfg_permission_request.get('label', 'Permission Request')}.", 'warning')
                return render_petition_form()
            if cfg_target_cvo.get('required') and not target_cvo:
                flash(f"{cfg_target_cvo.get('label', 'Target CVO/DSP Jurisdiction')} is required.", 'warning')
                return render_petition_form()
            if target_cvo not in VALID_TARGET_CVO:
                flash(f"Please select a valid {cfg_target_cvo.get('label', 'Target CVO/DSP Jurisdiction')}.", 'warning')
                return render_petition_form()
        if petitioner_name and len(petitioner_name) > 255:
            flash('Petitioner name is too long.', 'warning')
            return render_petition_form()
        if len(subject) > 5000:
            flash('Subject is too long.', 'warning')
            return render_petition_form()
        if len(place) > 255:
            flash('Place is too long.', 'warning')
            return render_petition_form()
        if not validate_contact(contact):
            flash('Please provide a valid contact number.', 'warning')
            return render_petition_form()
        if cfg_ereceipt_file.get('required') and (not ereceipt_file or not ereceipt_file.filename):
            flash(f"{cfg_ereceipt_file.get('label', 'E-Receipt File')} is required.", 'warning')
            return render_petition_form()
        if ereceipt_no and len(ereceipt_no) > 100:
            flash(f"{cfg_ereceipt_no.get('label', 'E-Receipt No')} is too long.", 'warning')
            return render_petition_form()
        if len(remarks) > 5000:
            flash('Remarks are too long.', 'warning')
            return render_petition_form()

        if ereceipt_file and ereceipt_file.filename:
            ok, upload_result = validate_pdf_upload(ereceipt_file, 'DEO e-receipt file')
            if not ok:
                flash(upload_result, 'danger')
                return render_petition_form()
            original_name = upload_result

            os.makedirs(ERECEIPT_UPLOAD_DIR, exist_ok=True)
            ereceipt_filename = f"deo_ereceipt_{datetime.now().strftime('%Y%m%d%H%M%S')}_{original_name}"
            ereceipt_file.save(os.path.join(ERECEIPT_UPLOAD_DIR, ereceipt_filename))

        data = {
            'efile_no': None,
            'petitioner_name': petitioner_name or 'Anonymous',
            'contact': contact,
            'place': place,
            'subject': subject,
            'petition_type': petition_type,
            'source_of_petition': source_of_petition,
            'govt_institution_type': govt_institution_type if source_of_petition == 'govt' else None,
            'received_at': received_at,
            'target_cvo': None if is_jmd_received else target_cvo,
            'permission_request_type': 'permission_required' if is_jmd_received else permission_request_type,
            'received_date': received_date or date.today(),
            'remarks': remarks,
            'ereceipt_no': ereceipt_no,
            'ereceipt_file': ereceipt_filename
        }
        
        try:
            if session.get('user_role') == 'data_entry' and not is_jmd_received:
                # DEO no longer decides enquiry mode; CVO decides at forwarded_to_cvo stage.
                data['requires_permission'] = True
                data['permission_status'] = 'pending'
            elif data['permission_request_type'] == 'direct_enquiry':
                data['requires_permission'] = False
                data['permission_status'] = 'not_required'
            else:
                data['requires_permission'] = True
                data['permission_status'] = 'pending'

            result = models.create_petition(data, session['user_id'])
            if is_jmd_received:
                models.send_for_permission(
                    result['id'],
                    session['user_id'],
                    comments='Auto-routed to PO from JMD Office receipt'
                )
                flash(f'Petition {result["sno"]} created and routed to PO successfully!', 'success')
            else:
                models.forward_petition_to_cvo(
                    result['id'],
                    session['user_id'],
                    data['target_cvo'],
                    comments='Auto-forwarded to concerned CVO/DSP from Data Entry'
                )
                flash(f'Petition {result["sno"]} created and auto-forwarded to CVO/DSP successfully!', 'success')
            return redirect(url_for('petition_view', petition_id=result['id']))
        except Exception as e:
            flash(f'Error creating petition: {str(e)}', 'danger')

    return render_petition_form()

@app.route('/petitions/<int:petition_id>')
@login_required
def petition_view(petition_id):
    petition = models.get_petition_by_id(petition_id)
    if not petition:
        flash('Petition not found.', 'danger')
        return redirect(url_for('petitions_list'))
    
    tracking = models.get_petition_tracking(petition_id)
    report = models.get_enquiry_report(petition_id)
    
    # Get inspectors mapped to the relevant CVO/DSP officer
    inspectors = []
    cvo_users = []
    cvo_like_roles = ('cvo_apspdcl', 'cvo_apepdcl', 'dsp')
    if session['user_role'] in cvo_like_roles:
        inspectors = models.get_inspectors_by_cvo(session['user_id'])
    elif session['user_role'] == 'super_admin':
        handler_id = petition.get('current_handler_id')
        if handler_id:
            handler_user = models.get_user_by_id(handler_id)
            if handler_user and handler_user.get('role') in cvo_like_roles:
                inspectors = models.get_inspectors_by_cvo(handler_id)
    if session['user_role'] in ('po', 'super_admin'):
        cvo_users = models.get_cvo_users()
    
    return render_template('petition_view.html', 
                         petition=petition, tracking=tracking, report=report,
                         inspectors=inspectors, cvo_users=cvo_users)

# ========================================
# WORKFLOW ACTION ROUTES
# ========================================

@app.route('/petitions/<int:petition_id>/action', methods=['POST'])
@login_required
def petition_action(petition_id):
    action = (request.form.get('action') or '').strip()
    comments = request.form.get('comments', '').strip()
    user_id = session['user_id']
    user_role = session['user_role']
    
    try:
        form_cfg = get_effective_form_field_configs()
        cfg_po_approve_efile = form_cfg.get('po_decision.approve_permission_efile_no', DEFAULT_FORM_FIELD_CONFIGS['po_decision.approve_permission_efile_no'])
        cfg_po_reject_reason = form_cfg.get('po_decision.reject_permission_reason', DEFAULT_FORM_FIELD_CONFIGS['po_decision.reject_permission_reason'])
        cfg_po_send_cmd_instructions = form_cfg.get('po_decision.send_cmd_instructions', DEFAULT_FORM_FIELD_CONFIGS['po_decision.send_cmd_instructions'])
        cfg_po_send_cmd_efile = form_cfg.get('po_decision.send_cmd_efile_no', DEFAULT_FORM_FIELD_CONFIGS['po_decision.send_cmd_efile_no'])
        cfg_po_lodge_efile = form_cfg.get('po_decision.po_lodge_efile_no', DEFAULT_FORM_FIELD_CONFIGS['po_decision.po_lodge_efile_no'])
        cfg_po_lodge_remarks = form_cfg.get('po_decision.po_lodge_remarks', DEFAULT_FORM_FIELD_CONFIGS['po_decision.po_lodge_remarks'])
        cfg_po_direct_lodge_efile = form_cfg.get('po_decision.po_direct_lodge_efile_no', DEFAULT_FORM_FIELD_CONFIGS['po_decision.po_direct_lodge_efile_no'])
        cfg_po_direct_lodge_remarks = form_cfg.get('po_decision.po_direct_lodge_remarks', DEFAULT_FORM_FIELD_CONFIGS['po_decision.po_direct_lodge_remarks'])
        cfg_po_close_comments = form_cfg.get('po_decision.close_comments', DEFAULT_FORM_FIELD_CONFIGS['po_decision.close_comments'])

        if not action:
            flash('Invalid action request.', 'warning')
            return redirect(url_for('petition_view', petition_id=petition_id))

        if action == 'forward_to_cvo':
            if user_role not in ('super_admin', 'data_entry'):
                flash('You are not allowed to forward petitions to CVO/DSP.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            target_cvo = (request.form.get('target_cvo') or '').strip()
            if target_cvo not in VALID_TARGET_CVO:
                flash('Please select a valid target CVO/DSP.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            models.forward_petition_to_cvo(petition_id, user_id, target_cvo, comments)
            flash('Petition forwarded to CVO/DSP successfully.', 'success')
            
        elif action == 'send_for_permission':
            if user_role not in ('super_admin', 'po'):
                flash('Only PO can send petitions for permission routing.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            models.send_for_permission(petition_id, user_id, comments)
            flash('Petition sent to PO for permission.', 'success')

        elif action in ('cvo_set_enquiry_mode', 'send_receipt_to_po'):
            if user_role not in ('super_admin', 'cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp'):
                flash('Only CVO/DSP can decide enquiry mode.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            petition = models.get_petition_by_id(petition_id)
            if not petition:
                flash('Petition not found.', 'danger')
                return redirect(url_for('petitions_list'))
            if petition.get('status') != 'forwarded_to_cvo':
                flash('Enquiry mode can be decided only when petition is with CVO/DSP.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))

            permission_request_type = (request.form.get('permission_request_type') or '').strip()
            if action == 'send_receipt_to_po':
                # Backward-compatible path for older form payload.
                permission_request_type = 'permission_required'
            if permission_request_type not in VALID_PERMISSION_REQUEST_TYPES:
                flash('Please select enquiry mode (Direct/Permission Required).', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))

            if permission_request_type == 'permission_required':
                permission_file = request.files.get('permission_file')
                permission_filename = None
                if permission_file and permission_file.filename:
                    ok, upload_result = validate_pdf_upload(permission_file, 'Permission document')
                    if not ok:
                        flash(upload_result, 'danger')
                        return redirect(url_for('petition_view', petition_id=petition_id))
                    original_name = upload_result
                    os.makedirs(ENQUIRY_UPLOAD_DIR, exist_ok=True)
                    permission_filename = f"cvo_permission_{petition_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{original_name}"
                    permission_file.save(os.path.join(ENQUIRY_UPLOAD_DIR, permission_filename))
                try:
                    models.cvo_send_receipt_to_po(petition_id, user_id, comments, permission_filename)
                except Exception:
                    if permission_filename:
                        try:
                            os.remove(os.path.join(ENQUIRY_UPLOAD_DIR, permission_filename))
                        except Exception:
                            pass
                    raise
                flash('Permission route selected and receipt sent to PO.', 'success')
            else:
                enquiry_type_decision = (request.form.get('enquiry_type_decision') or '').strip() or 'detailed'
                if enquiry_type_decision not in VALID_ENQUIRY_TYPES:
                    enquiry_type_decision = 'detailed'
                models.cvo_mark_direct_enquiry(petition_id, user_id, comments, enquiry_type_decision)
                flash('Direct enquiry mode selected. You can now assign inspector.', 'success')
            
        elif action == 'approve_permission':
            if user_role not in ('super_admin', 'po'):
                flash('Only PO can approve permission.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            petition = models.get_petition_by_id(petition_id)
            if not petition:
                flash('Petition not found.', 'danger')
                return redirect(url_for('petitions_list'))
            target_cvo = (request.form.get('target_cvo') or '').strip()
            enquiry_type_decision = (request.form.get('enquiry_type_decision') or '').strip()
            efile_no_input = request.form.get('efile_no', '').strip()
            if target_cvo not in VALID_TARGET_CVO:
                flash('Please select a valid target CVO/DSP.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if enquiry_type_decision not in VALID_ENQUIRY_TYPES:
                flash('Please select enquiry type decision (Detailed/Preliminary).', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            efile_no, efile_error = resolve_efile_no_for_action(
                petition,
                efile_no_input,
                required_message=f"{cfg_po_approve_efile.get('label', 'E-Office File No')} is required to approve permission." if cfg_po_approve_efile.get('required') else None
            )
            if efile_error:
                flash(efile_error, 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            models.approve_permission(petition_id, user_id, target_cvo, efile_no, comments, enquiry_type_decision)
            flash('Permission granted and pushed to respective CVO/DSP.', 'success')

        elif action == 'reject_permission':
            if user_role not in ('super_admin', 'po'):
                flash('Only PO can reject permission.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if cfg_po_reject_reason.get('required') and not comments:
                flash(f"{cfg_po_reject_reason.get('label', 'Reason for rejection')} is required.", 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            models.reject_permission(petition_id, user_id, comments)
            flash('Permission rejected.', 'warning')
            
        elif action == 'assign_inspector':
            if user_role not in ('super_admin', 'cvo_apspdcl', 'cvo_apepdcl', 'dsp'):
                flash('Only CVO/DSP can assign inspectors.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            petition = models.get_petition_by_id(petition_id)
            if petition and petition.get('requires_permission') and petition.get('status') != 'permission_approved':
                flash('Permission is compulsory. PO approval required before assigning inspector.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if petition and not petition.get('requires_permission') and petition.get('status') != 'forwarded_to_cvo':
                flash('For Direct Enquiry, inspector can be assigned only when petition is at CVO/DSP.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            inspector_id = parse_optional_int(request.form.get('inspector_id'))
            if not inspector_id:
                flash('Please select a valid field inspector.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            enquiry_type_decision = None
            memo_file = request.files.get('assignment_memo_file')
            memo_filename = None
            if memo_file and memo_file.filename:
                ok, upload_result = validate_pdf_upload(memo_file, 'Upload memo/instructions')
                if not ok:
                    flash(upload_result, 'danger')
                    return redirect(url_for('petition_view', petition_id=petition_id))
                original_name = upload_result
                os.makedirs(ENQUIRY_UPLOAD_DIR, exist_ok=True)
                memo_filename = f"assign_memo_{petition_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{original_name}"
                memo_file.save(os.path.join(ENQUIRY_UPLOAD_DIR, memo_filename))
            try:
                models.assign_to_inspector(
                    petition_id, user_id, inspector_id, comments, enquiry_type_decision, memo_filename
                )
            except Exception:
                if memo_filename:
                    try:
                        os.remove(os.path.join(ENQUIRY_UPLOAD_DIR, memo_filename))
                    except Exception:
                        pass
                raise
            flash('Petition assigned to inspector.', 'success')

        elif action == 'submit_report':
            if user_role not in ('super_admin', 'inspector'):
                flash('Only inspectors can upload enquiry report.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            petition = models.get_petition_by_id(petition_id)
            if not petition:
                flash('Petition not found.', 'danger')
                return redirect(url_for('petitions_list'))
            form_cfg = get_effective_form_field_configs()
            cfg_report_text = form_cfg.get('inspector_report.report_text', DEFAULT_FORM_FIELD_CONFIGS['inspector_report.report_text'])
            cfg_recommendation = form_cfg.get('inspector_report.recommendation', DEFAULT_FORM_FIELD_CONFIGS['inspector_report.recommendation'])
            cfg_report_file = form_cfg.get('inspector_report.report_file', DEFAULT_FORM_FIELD_CONFIGS['inspector_report.report_file'])
            cfg_request_detailed = form_cfg.get(
                'inspector_report.request_detailed_permission',
                DEFAULT_FORM_FIELD_CONFIGS['inspector_report.request_detailed_permission']
            )
            cfg_detailed_reason = form_cfg.get(
                'inspector_report.detailed_request_reason',
                DEFAULT_FORM_FIELD_CONFIGS['inspector_report.detailed_request_reason']
            )
            report_text = request.form.get('report_text', '').strip()
            recommendation = request.form.get('recommendation', '').strip()
            request_detailed_permission = (request.form.get('request_detailed_permission') or '').strip() == '1'
            detailed_request_reason = (request.form.get('detailed_request_reason') or '').strip()
            if cfg_report_text.get('required') and not report_text:
                flash(f"{cfg_report_text.get('label', 'Conclusion of enquiry report')} is required.", 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if len(report_text) > 20000:
                flash('Conclusion of enquiry report is too long.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if cfg_recommendation.get('required') and not recommendation:
                flash(f"{cfg_recommendation.get('label', 'Recommendations/Suggestions')} are required.", 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if len(recommendation) > 5000:
                flash('Recommendations/Suggestions text is too long.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if request_detailed_permission:
                if (petition.get('enquiry_type') or '').strip().lower() != 'preliminary':
                    flash('Detailed enquiry conversion request is allowed only for preliminary enquiry petitions.', 'warning')
                    return redirect(url_for('petition_view', petition_id=petition_id))
                if cfg_detailed_reason.get('required') and not detailed_request_reason:
                    flash(f"{cfg_detailed_reason.get('label', 'Reason for Detailed Enquiry Request')} is required.", 'warning')
                    return redirect(url_for('petition_view', petition_id=petition_id))
                if len(detailed_request_reason) > 2000:
                    flash(f"{cfg_detailed_reason.get('label', 'Reason for Detailed Enquiry Request')} is too long.", 'warning')
                    return redirect(url_for('petition_view', petition_id=petition_id))
            report_file = request.files.get('report_file')
            if cfg_report_file.get('required') and (not report_file or not report_file.filename):
                flash('Enquiry report file (PDF) is compulsory.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if not report_file or not report_file.filename:
                report_filename = None
                models.submit_enquiry_report(
                    petition_id, user_id, report_text, '', recommendation, report_filename,
                    request_detailed_permission=request_detailed_permission,
                    detailed_request_reason=detailed_request_reason
                )
                if request_detailed_permission:
                    flash(
                        f'Enquiry report uploaded and "{cfg_request_detailed.get("label", "Detailed enquiry conversion request")}" sent to CVO/DSP.',
                        'success'
                    )
                else:
                    flash('Enquiry report uploaded successfully.', 'success')
                return redirect(url_for('petition_view', petition_id=petition_id))
            ok, upload_result = validate_pdf_upload(report_file, 'Enquiry report attachment')
            if not ok:
                flash(upload_result, 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            original_name = upload_result
            os.makedirs(ENQUIRY_UPLOAD_DIR, exist_ok=True)
            report_filename = f"enquiry_{petition_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{original_name}"
            report_file.save(os.path.join(ENQUIRY_UPLOAD_DIR, report_filename))
            models.submit_enquiry_report(
                petition_id, user_id, report_text, '', recommendation, report_filename,
                request_detailed_permission=request_detailed_permission,
                detailed_request_reason=detailed_request_reason
            )
            if request_detailed_permission:
                flash(
                    f'Enquiry report uploaded and "{cfg_request_detailed.get("label", "Detailed enquiry conversion request")}" sent to CVO/DSP.',
                    'success'
                )
            else:
                flash('Enquiry report uploaded successfully.', 'success')
            
        elif action == 'cvo_comments':
            if user_role not in ('super_admin', 'cvo_apspdcl', 'cvo_apepdcl', 'dsp'):
                flash('Only CVO/DSP can enter remarks.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            form_cfg = get_effective_form_field_configs()
            cfg_cvo_comments = form_cfg.get('cvo_review.cvo_comments', DEFAULT_FORM_FIELD_CONFIGS['cvo_review.cvo_comments'])
            cfg_cvo_file = form_cfg.get('cvo_review.consolidated_report_file', DEFAULT_FORM_FIELD_CONFIGS['cvo_review.consolidated_report_file'])
            cvo_comments = request.form.get('cvo_comments', '').strip()
            if cfg_cvo_comments.get('required') and not cvo_comments:
                flash(f"{cfg_cvo_comments.get('label', 'CVO/DSP comments')} are required.", 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            consolidated_file = request.files.get('consolidated_report_file')
            if cfg_cvo_file.get('required') and (not consolidated_file or not consolidated_file.filename):
                flash(f"{cfg_cvo_file.get('label', 'Consolidated report file')} is required.", 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if consolidated_file and consolidated_file.filename:
                ok, upload_result = validate_pdf_upload(consolidated_file, 'Consolidated report upload')
                if not ok:
                    flash(upload_result, 'danger')
                    return redirect(url_for('petition_view', petition_id=petition_id))
                original_name = upload_result

                os.makedirs(ENQUIRY_UPLOAD_DIR, exist_ok=True)
                consolidated_filename = f"cvo_consolidated_{petition_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{original_name}"
                consolidated_file.save(os.path.join(ENQUIRY_UPLOAD_DIR, consolidated_filename))
                models.cvo_upload_consolidated_report(petition_id, user_id, consolidated_filename)
            models.cvo_add_comments(petition_id, user_id, cvo_comments)
            flash('Forwarded to PO for conclusion.', 'success')

        elif action == 'cvo_send_back_reenquiry':
            if user_role not in ('super_admin', 'cvo_apspdcl', 'cvo_apepdcl', 'dsp'):
                flash('Only CVO/DSP can send back for re-enquiry.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            petition = models.get_petition_by_id(petition_id)
            if not petition:
                flash('Petition not found.', 'danger')
                return redirect(url_for('petitions_list'))
            if petition.get('status') != 'enquiry_report_submitted':
                flash('Re-enquiry send back is allowed only after inspector report submission.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            inspector_id = parse_optional_int(request.form.get('inspector_id'))
            if not inspector_id:
                flash('Please select a valid field inspector.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            reenquiry_reason = request.form.get('comments', '').strip()
            if not reenquiry_reason:
                flash('Reason is required to send back for re-enquiry.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if len(reenquiry_reason) > 5000:
                flash('Reason is too long.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            models.cvo_send_back_to_inspector_for_reenquiry(
                petition_id, user_id, inspector_id, reenquiry_reason
            )
            flash('Sent back to field level for re-enquiry.', 'success')

        elif action == 'upload_consolidated_report':
            if user_role not in ('super_admin', 'cvo_apspdcl', 'cvo_apepdcl', 'dsp'):
                flash('Only CVO/DSP can upload consolidated report.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            petition = models.get_petition_by_id(petition_id)
            if petition and petition.get('status') != 'enquiry_report_submitted':
                flash('Consolidated report can be uploaded only after inspector report submission.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))

            consolidated_file = request.files.get('consolidated_report_file')
            if not consolidated_file or not consolidated_file.filename:
                flash('Please choose consolidated report PDF to upload.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))

            ok, upload_result = validate_pdf_upload(consolidated_file, 'Consolidated report upload')
            if not ok:
                flash(upload_result, 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            original_name = upload_result

            os.makedirs(ENQUIRY_UPLOAD_DIR, exist_ok=True)
            consolidated_filename = f"cvo_consolidated_{petition_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{original_name}"
            consolidated_file.save(os.path.join(ENQUIRY_UPLOAD_DIR, consolidated_filename))
            models.cvo_upload_consolidated_report(petition_id, user_id, consolidated_filename)
            flash('Consolidated report uploaded successfully.', 'success')

        elif action == 'request_detailed_enquiry':
            if user_role not in ('super_admin', 'cvo_apspdcl', 'cvo_apepdcl', 'dsp'):
                flash('Only CVO/DSP can request detailed enquiry.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            petition = models.get_petition_by_id(petition_id)
            if petition and petition.get('enquiry_type') != 'preliminary':
                flash('Detailed enquiry request is allowed only for preliminary petitions.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            cvo_comments = request.form.get('cvo_comments', '').strip()
            if not cvo_comments:
                flash('Remarks are required to request detailed enquiry.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            models.cvo_request_detailed_enquiry(petition_id, user_id, cvo_comments)
            flash('Detailed enquiry requested. Workflow restarted at PO permission stage.', 'success')
            
        elif action == 'give_conclusion':
            if user_role not in ('super_admin', 'po'):
                flash('Only PO can give conclusion.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            petition = models.get_petition_by_id(petition_id)
            if not petition:
                flash('Petition not found.', 'danger')
                return redirect(url_for('petitions_list'))
            efile_no_input = request.form.get('efile_no', '').strip()
            final_conclusion = request.form.get('final_conclusion', '').strip()
            instructions = request.form.get('instructions', '').strip()
            conclusion_file = request.files.get('conclusion_file')
            conclusion_filename = None
            efile_no, efile_error = resolve_efile_no_for_action(
                petition,
                efile_no_input,
                required_message='E-Office File No is required for final conclusion.'
            )
            if efile_error:
                flash(efile_error, 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if not final_conclusion:
                flash('Final conclusion is required.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if len(final_conclusion) > 10000:
                flash('Final conclusion is too long.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if len(instructions) > 5000:
                flash('Instructions are too long.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))

            if conclusion_file and conclusion_file.filename:
                ok, upload_result = validate_pdf_upload(conclusion_file, 'Conclusion upload')
                if not ok:
                    flash(upload_result, 'danger')
                    return redirect(url_for('petition_view', petition_id=petition_id))
                original_name = upload_result
                os.makedirs(ENQUIRY_UPLOAD_DIR, exist_ok=True)
                conclusion_filename = f"po_conclusion_{petition_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{original_name}"
                conclusion_file.save(os.path.join(ENQUIRY_UPLOAD_DIR, conclusion_filename))

            models.po_give_conclusion(petition_id, user_id, efile_no, final_conclusion, instructions, conclusion_filename)
            flash('Final conclusion submitted and petition closed.', 'success')

        elif action == 'send_to_cmd':
            if user_role not in ('super_admin', 'po'):
                flash('Only PO can forward petition to CMD/CGM-HR.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            petition = models.get_petition_by_id(petition_id)
            if not petition:
                flash('Petition not found.', 'danger')
                return redirect(url_for('petitions_list'))
            efile_no_input = request.form.get('efile_no', '').strip()
            efile_no, efile_error = resolve_efile_no_for_action(
                petition,
                efile_no_input,
                required_message=f"{cfg_po_send_cmd_efile.get('label', 'E-Office File No')} is compulsory before sending to CMD/CGM-HR." if cfg_po_send_cmd_efile.get('required') else None
            )
            if efile_error:
                flash(efile_error, 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            cmd_instructions = request.form.get('cmd_instructions', '').strip()
            if cfg_po_send_cmd_instructions.get('required') and not cmd_instructions:
                flash(f"{cfg_po_send_cmd_instructions.get('label', 'CMD/CGM-HR Instructions')} is required.", 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if len(cmd_instructions) > 5000:
                flash('CMD/CGM-HR instructions are too long.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            models.po_send_to_cmd(petition_id, user_id, cmd_instructions, efile_no)
            flash('Petition forwarded to concerned CMD/CGM-HR for action.', 'success')

        elif action == 'po_send_back_reenquiry':
            if user_role not in ('super_admin', 'po'):
                flash('Only PO can send back for re-enquiry.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            petition = models.get_petition_by_id(petition_id)
            if not petition:
                flash('Petition not found.', 'danger')
                return redirect(url_for('petitions_list'))
            if petition.get('status') != 'forwarded_to_po':
                flash('Re-enquiry send back is allowed only when report is pending with PO.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            reenquiry_reason = request.form.get('comments', '').strip()
            if not reenquiry_reason:
                flash('Reason is required to send back for re-enquiry.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if len(reenquiry_reason) > 5000:
                flash('Reason is too long.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            models.po_send_back_to_cvo_for_reenquiry(petition_id, user_id, reenquiry_reason)
            flash('Sent back to CVO/DSP for re-enquiry routing.', 'success')

        elif action == 'update_efile_no':
            if user_role not in ('super_admin', 'po'):
                flash('Only PO can update E-Office File No.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            efile_no = request.form.get('efile_no', '').strip()
            if not efile_no:
                flash('E-Office File No is required.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if len(efile_no) > 100:
                flash('E-Office File No is too long.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))

            petition = models.get_petition_by_id(petition_id)
            if not petition:
                flash('Petition not found.', 'danger')
                return redirect(url_for('petitions_list'))
            if petition.get('requires_permission'):
                flash('This action is allowed only for direct enquiry petitions.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if petition.get('status') not in DIRECT_ENQUIRY_EFILE_EDITABLE_STATUSES:
                flash('E-Office File No can be updated only before enquiry report completion.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if (petition.get('efile_no') or '').strip():
                flash('E-Office File No is already set. Editing is not allowed.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))

            updated = models.po_update_efile_no(petition_id, user_id, efile_no)
            if not updated:
                flash('E-Office File No is already set. Editing is not allowed.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            flash('E-Office File No updated successfully.', 'success')

        elif action == 'cmd_submit_action_report':
            if user_role not in ('super_admin', 'cmd_apspdcl', 'cmd_apepdcl', 'cmd_apcpdcl', 'cgm_hr_transco'):
                flash('Only CMD can upload action taken report.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            form_cfg = get_effective_form_field_configs()
            cfg_action_taken = form_cfg.get('cmd_action.action_taken', DEFAULT_FORM_FIELD_CONFIGS['cmd_action.action_taken'])
            cfg_action_file = form_cfg.get('cmd_action.action_report_file', DEFAULT_FORM_FIELD_CONFIGS['cmd_action.action_report_file'])
            action_taken = request.form.get('action_taken', '').strip()
            if cfg_action_taken.get('required') and not action_taken:
                flash(f"{cfg_action_taken.get('label', 'Action taken details')} are required.", 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if len(action_taken) > 10000:
                flash('Action taken details are too long.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))

            action_report_file = request.files.get('action_report_file')
            action_report_filename = None
            if cfg_action_file.get('required') and (not action_report_file or not action_report_file.filename):
                flash(f"{cfg_action_file.get('label', 'Action report copy')} is required.", 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if action_report_file and action_report_file.filename:
                ok, upload_result = validate_pdf_upload(action_report_file, 'Action report upload')
                if not ok:
                    flash(upload_result, 'danger')
                    return redirect(url_for('petition_view', petition_id=petition_id))
                original_name = upload_result
                os.makedirs(ENQUIRY_UPLOAD_DIR, exist_ok=True)
                action_report_filename = f"cmd_action_{petition_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{original_name}"
                action_report_file.save(os.path.join(ENQUIRY_UPLOAD_DIR, action_report_filename))

            models.cmd_submit_action_report(petition_id, user_id, action_taken, action_report_filename)
            flash('Action taken recorded and copy sent to PO for closure.', 'success')

        elif action == 'po_lodge':
            if user_role not in ('super_admin', 'po'):
                flash('Only PO can lodge petition.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            petition = models.get_petition_by_id(petition_id)
            if not petition:
                flash('Petition not found.', 'danger')
                return redirect(url_for('petitions_list'))
            lodge_remarks = request.form.get('lodge_remarks', '').strip()
            if cfg_po_lodge_remarks.get('required') and not lodge_remarks:
                flash(f"{cfg_po_lodge_remarks.get('label', 'PO Lodge Remarks')} is required.", 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if len(lodge_remarks) > 5000:
                flash('Lodge remarks are too long.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            efile_no_input = request.form.get('efile_no', '').strip()
            efile_no, efile_error = resolve_efile_no_for_action(
                petition,
                efile_no_input,
                required_message=f"{cfg_po_lodge_efile.get('label', 'E-Office File No')} is required." if cfg_po_lodge_efile.get('required') else None
            )
            if efile_error:
                flash(efile_error, 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            models.po_lodge_petition(petition_id, user_id, lodge_remarks, efile_no)
            flash('Petition lodged in PO login.', 'success')

        elif action == 'po_direct_lodge':
            if user_role not in ('super_admin', 'po'):
                flash('Only PO can directly lodge petition.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            petition = models.get_petition_by_id(petition_id)
            if petition and petition.get('status') not in ('sent_for_permission',):
                flash('Direct lodge without enquiry is allowed only at permission stage.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            lodge_remarks = request.form.get('lodge_remarks', '').strip()
            if cfg_po_direct_lodge_remarks.get('required') and not lodge_remarks:
                flash(f"{cfg_po_direct_lodge_remarks.get('label', 'PO Lodge Remarks')} is required.", 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if len(lodge_remarks) > 5000:
                flash('Lodge remarks are too long.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            efile_no_input = request.form.get('efile_no', '').strip()
            efile_no, efile_error = resolve_efile_no_for_action(
                petition,
                efile_no_input,
                required_message=f"{cfg_po_direct_lodge_efile.get('label', 'E-Office File No')} is required." if cfg_po_direct_lodge_efile.get('required') else None
            )
            if efile_error:
                flash(efile_error, 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            models.po_direct_lodge_no_enquiry(petition_id, user_id, lodge_remarks, efile_no)
            flash('Petition directly lodged by PO (no enquiry/action required).', 'success')
            
        elif action == 'close':
            if user_role not in ('super_admin', 'po'):
                flash('Only PO can close petition.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            petition = models.get_petition_by_id(petition_id)
            if petition and petition.get('status') != 'lodged':
                flash('Petition can be closed only after Lodged stage.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if cfg_po_close_comments.get('required') and not comments:
                flash(f"{cfg_po_close_comments.get('label', 'Closing Remarks')} is required.", 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if len(comments) > 5000:
                flash('Closing remarks are too long.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            models.close_petition(petition_id, user_id, comments)
            flash('Petition closed.', 'success')
        else:
            flash('Unsupported action.', 'warning')
            
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('petition_view', petition_id=petition_id))

@app.route('/e-receipts/<path:filename>')
@login_required
def ereceipt_file(filename):
    return send_from_directory(ERECEIPT_UPLOAD_DIR, filename, as_attachment=False)

@app.route('/enquiry-files/<path:filename>')
@login_required
def enquiry_file(filename):
    return send_from_directory(ENQUIRY_UPLOAD_DIR, filename, as_attachment=False)


@app.route('/profile-photos/<path:filename>')
@login_required
def profile_photo_file(filename):
    return send_from_directory(PROFILE_UPLOAD_DIR, filename, as_attachment=False)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = models.get_user_by_id(session['user_id'])
    if not user:
        flash('User profile not found.', 'danger')
        return redirect(url_for('logout'))

    if request.method == 'POST':
        full_name = (request.form.get('full_name') or '').strip()
        username = (request.form.get('username') or '').strip()
        phone = (request.form.get('phone') or '').strip() or None
        email = (request.form.get('email') or '').strip() or None
        new_password = (request.form.get('new_password') or '').strip()
        confirm_password = (request.form.get('confirm_password') or '').strip()
        remove_photo = request.form.get('remove_photo') == 'on'
        photo_upload = request.files.get('profile_photo')

        if not full_name or len(full_name) < 3:
            flash('Name must be at least 3 characters.', 'warning')
            return redirect(url_for('profile'))
        if not username or len(username) < 3:
            flash('Username must be at least 3 characters.', 'warning')
            return redirect(url_for('profile'))
        if not re.match(r'^[A-Za-z0-9_.-]+$', username):
            flash('Username can only contain letters, numbers, dot, underscore, and hyphen.', 'warning')
            return redirect(url_for('profile'))
        if not validate_contact(phone):
            flash('Please provide a valid phone number.', 'warning')
            return redirect(url_for('profile'))
        if not validate_email(email):
            flash('Please provide a valid email address.', 'warning')
            return redirect(url_for('profile'))

        if new_password:
            if len(new_password) < 6:
                flash('New password must be at least 6 characters.', 'warning')
                return redirect(url_for('profile'))
            if new_password != confirm_password:
                flash('Password confirmation does not match.', 'warning')
                return redirect(url_for('profile'))

        ok_photo, stored_photo_name, photo_error = validate_profile_photo_upload(photo_upload, session['user_id'])
        if not ok_photo:
            flash(photo_error, 'warning')
            return redirect(url_for('profile'))

        old_photo = user.get('profile_photo')
        photo_changed = False
        try:
            if username != user.get('username'):
                models.set_username(session['user_id'], username)

            models.update_user_profile_info(session['user_id'], full_name, phone, email)

            if new_password:
                models.set_user_password(session['user_id'], new_password)

            if stored_photo_name and photo_upload:
                ensure_upload_dirs()
                photo_upload.save(os.path.join(PROFILE_UPLOAD_DIR, stored_photo_name))
                models.set_user_profile_photo(session['user_id'], stored_photo_name)
                photo_changed = True
            elif remove_photo and old_photo:
                models.set_user_profile_photo(session['user_id'], None)
                photo_changed = True

            if photo_changed and old_photo and old_photo != stored_photo_name:
                delete_profile_photo_file(old_photo)

            refresh_session_user()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('profile'))
        except Exception as e:
            if stored_photo_name:
                delete_profile_photo_file(stored_photo_name)
            error_text = str(e).lower()
            if 'unique' in error_text or 'duplicate key' in error_text:
                flash('Username already exists. Choose a different username.', 'danger')
            else:
                flash(f'Unable to update profile: {str(e)}', 'danger')
            return redirect(url_for('profile'))

    return render_template('profile.html', user=user)

# ========================================
# USER MANAGEMENT (SUPER ADMIN)
# ========================================

@app.route('/users')
@login_required
@role_required('super_admin')
def users_list():
    users = models.get_all_users()
    cvo_users = models.get_cvo_users()
    role_login_users = models.get_role_login_users()
    inspector_mappings = models.get_inspector_mappings()
    try:
        signup_requests = models.get_pending_signup_requests()
    except Exception:
        signup_requests = []
    try:
        reset_requests = models.get_pending_password_reset_requests()
    except Exception:
        reset_requests = []
    return render_template(
        'users.html',
        users=users,
        cvo_users=cvo_users,
        role_login_users=role_login_users,
        inspector_mappings=inspector_mappings,
        signup_requests=signup_requests,
        reset_requests=reset_requests,
    )


@app.route('/users/signup-requests/<int:request_id>/approve', methods=['POST'])
@login_required
@role_required('super_admin')
def approve_signup_request(request_id):
    try:
        models.approve_signup_request(request_id, session['user_id'])
        flash('Signup request approved and user created.', 'success')
    except Exception as e:
        flash(f'Unable to approve signup request: {str(e)}', 'danger')
    return redirect(url_for('users_list'))


@app.route('/users/signup-requests/<int:request_id>/reject', methods=['POST'])
@login_required
@role_required('super_admin')
def reject_signup_request(request_id):
    note = (request.form.get('decision_notes') or '').strip()
    try:
        models.reject_signup_request(request_id, session['user_id'], note)
        flash('Signup request rejected.', 'success')
    except Exception as e:
        flash(f'Unable to reject signup request: {str(e)}', 'danger')
    return redirect(url_for('users_list'))


@app.route('/users/password-reset-requests/<int:request_id>/approve', methods=['POST'])
@login_required
@role_required('super_admin')
def approve_password_reset_request(request_id):
    try:
        models.approve_password_reset_request(request_id, session['user_id'])
        flash('Password reset request approved.', 'success')
    except Exception as e:
        flash(f'Unable to approve password reset request: {str(e)}', 'danger')
    return redirect(url_for('users_list'))


@app.route('/users/password-reset-requests/<int:request_id>/reject', methods=['POST'])
@login_required
@role_required('super_admin')
def reject_password_reset_request(request_id):
    note = (request.form.get('decision_notes') or '').strip()
    try:
        models.reject_password_reset_request(request_id, session['user_id'], note)
        flash('Password reset request rejected.', 'success')
    except Exception as e:
        flash(f'Unable to reject password reset request: {str(e)}', 'danger')
    return redirect(url_for('users_list'))


@app.route('/form-management', methods=['GET', 'POST'])
@login_required
@role_required('super_admin')
def form_management():
    if request.method == 'POST':
        action = (request.form.get('action') or 'update_field').strip()
        if action == 'add_field':
            form_key = (request.form.get('new_form_key') or '').strip()
            field_key = (request.form.get('new_field_key') or '').strip().lower()
            label = (request.form.get('new_label') or '').strip()
            field_type = (request.form.get('new_field_type') or 'text').strip()
            is_required = request.form.get('new_is_required') == 'on'
            if form_key not in FORM_MANAGEMENT_GROUPS:
                flash('Please select a valid form group.', 'danger')
                return redirect(url_for('form_management'))
            if not re.fullmatch(r'[a-z][a-z0-9_]{1,80}', field_key):
                flash('Field key must use lowercase letters, numbers, underscore (2-81 chars).', 'warning')
                return redirect(url_for('form_management'))
            if not label:
                flash('Field label is required.', 'warning')
                return redirect(url_for('form_management'))
            if field_type not in VALID_DYNAMIC_FIELD_TYPES:
                flash('Invalid field type.', 'danger')
                return redirect(url_for('form_management'))
            config_key = f'{form_key}.{field_key}'
            if config_key in get_effective_form_field_configs():
                flash('Field key already exists for this form group.', 'warning')
                return redirect(url_for('form_management'))
            try:
                models.upsert_form_field_config(
                    form_key=form_key,
                    field_key=field_key,
                    label=label,
                    field_type=field_type,
                    is_required=is_required,
                    options=[],
                    updated_by=session['user_id']
                )
                flash('New form field added successfully.', 'success')
            except Exception as e:
                flash(f'Unable to add form field: {str(e)}', 'danger')
            return redirect(url_for('form_management'))

        form_key = (request.form.get('form_key') or '').strip()
        field_key = (request.form.get('field_key') or '').strip()
        config_key = f'{form_key}.{field_key}'
        effective_cfg = get_effective_form_field_configs()
        if config_key not in effective_cfg:
            flash('Invalid form field selection.', 'danger')
            return redirect(url_for('form_management'))

        label = (request.form.get('label') or '').strip() or effective_cfg[config_key]['label']
        field_type = (request.form.get('field_type') or '').strip()
        if field_type not in VALID_DYNAMIC_FIELD_TYPES:
            flash('Invalid field type.', 'danger')
            return redirect(url_for('form_management'))

        is_required = request.form.get('is_required') == 'on'
        options = []
        if effective_cfg[config_key]['type'] == 'select' or field_type == 'select':
            raw_options = request.form.get('options_text', '')
            for line in raw_options.splitlines():
                item = line.strip()
                if not item:
                    continue
                if '|' in item:
                    value, label_text = item.split('|', 1)
                    value = value.strip()
                    label_text = label_text.strip()
                else:
                    value = item.strip()
                    label_text = item.strip()
                if value and label_text:
                    options.append({'value': value, 'label': label_text})

            if not options:
                options = effective_cfg[config_key].get('options', [])

        try:
            models.upsert_form_field_config(
                form_key, field_key, label, field_type, is_required, options, session['user_id']
            )
            flash('Form field updated successfully.', 'success')
        except Exception as e:
            flash(f'Unable to update form field: {str(e)}', 'danger')
        return redirect(url_for('form_management'))

    effective = get_effective_form_field_configs()
    grouped = {}
    for key, cfg in effective.items():
        fk, field = key.split('.', 1)
        grouped.setdefault(fk, []).append({'form_key': fk, 'field_key': field, **cfg, 'config_key': key})
    for fk in grouped:
        grouped[fk] = sorted(grouped[fk], key=lambda x: x['field_key'])

    return render_template(
        'form_management.html',
        grouped_fields=grouped,
        form_groups=FORM_MANAGEMENT_GROUPS,
        field_types=sorted(VALID_DYNAMIC_FIELD_TYPES),
    )

@app.route('/users/new', methods=['POST'])
@login_required
@role_required('super_admin')
def user_create():
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        full_name = request.form.get('full_name', '').strip()
        role = (request.form.get('role') or '').strip()
        cvo_office = (request.form.get('cvo_office') or '').strip() or None
        assigned_cvo_id = parse_optional_int(request.form.get('assigned_cvo_id'))
        phone = request.form.get('phone', '').strip() or None
        email = request.form.get('email', '').strip() or None

        if not username or len(username) < 3:
            flash('Username must be at least 3 characters.', 'warning')
            return redirect(url_for('users_list'))
        if not password or len(password) < 6:
            flash('Password must be at least 6 characters.', 'warning')
            return redirect(url_for('users_list'))
        if not full_name or len(full_name) < 3:
            flash('Officer name must be at least 3 characters.', 'warning')
            return redirect(url_for('users_list'))
        if role not in VALID_USER_ROLES:
            flash('Please select a valid role.', 'warning')
            return redirect(url_for('users_list'))
        if cvo_office and cvo_office not in VALID_CVO_OFFICES:
            flash('Please select a valid office.', 'warning')
            return redirect(url_for('users_list'))
        if not validate_contact(phone):
            flash('Please provide a valid phone number.', 'warning')
            return redirect(url_for('users_list'))
        if not validate_email(email):
            flash('Please provide a valid email address.', 'warning')
            return redirect(url_for('users_list'))

        if role == 'inspector':
            if not cvo_office:
                flash('Office is required for inspector role.', 'warning')
                return redirect(url_for('users_list'))
            if not assigned_cvo_id:
                flash('Please assign inspector to a CVO/DSP.', 'warning')
                return redirect(url_for('users_list'))
        elif role == 'data_entry':
            if not cvo_office:
                flash('Office is required for Data Entry role.', 'warning')
                return redirect(url_for('users_list'))
            assigned_cvo_id = None
        elif role.startswith('cvo_') or role == 'dsp':
            if not cvo_office:
                flash('Office is required for CVO/DSP role.', 'warning')
                return redirect(url_for('users_list'))
            assigned_cvo_id = None
        else:
            assigned_cvo_id = None
            cvo_office = None

        if assigned_cvo_id:
            cvo_user = models.get_user_by_id(assigned_cvo_id)
            if not cvo_user or cvo_user.get('role') not in ('cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp'):
                flash('Assigned CVO/DSP is invalid.', 'warning')
                return redirect(url_for('users_list'))
        
        models.create_user(username, password, full_name, role, cvo_office, assigned_cvo_id, phone, email)
        flash(f'User {username} created successfully!', 'success')
    except Exception as e:
        flash(f'Error creating user: {str(e)}', 'danger')
    
    return redirect(url_for('users_list'))


@app.route('/users/upload', methods=['POST'])
@login_required
@role_required('super_admin')
def users_upload():
    upload = request.files.get('users_file')
    if not upload or not upload.filename:
        flash('Please choose an Excel/CSV file to upload.', 'warning')
        return redirect(url_for('users_list'))

    filename = secure_filename(upload.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ('xlsx', 'csv'):
        flash('Only .xlsx or .csv files are allowed for bulk user creation.', 'danger')
        return redirect(url_for('users_list'))

    required_headers = {'username', 'password', 'full_name', 'role'}
    rows = []
    try:
        if ext == 'csv':
            content = upload.stream.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(content))
            headers = {h.strip().lower() for h in (reader.fieldnames or [])}
            if not required_headers.issubset(headers):
                flash('Missing required columns. Required: username,password,full_name,role', 'danger')
                return redirect(url_for('users_list'))
            for row in reader:
                rows.append({(k or '').strip().lower(): (v or '').strip() for k, v in row.items()})
        else:
            if load_workbook is None:
                flash('Excel support requires openpyxl dependency. Install and retry.', 'danger')
                return redirect(url_for('users_list'))
            wb = load_workbook(upload, read_only=True, data_only=True)
            ws = wb.active
            all_rows = list(ws.iter_rows(values_only=True))
            if not all_rows:
                flash('Uploaded file is empty.', 'warning')
                return redirect(url_for('users_list'))
            headers = [str(h).strip().lower() if h is not None else '' for h in all_rows[0]]
            if not required_headers.issubset(set(headers)):
                flash('Missing required columns. Required: username,password,full_name,role', 'danger')
                return redirect(url_for('users_list'))
            for r in all_rows[1:]:
                data = {}
                for idx, col in enumerate(headers):
                    if not col:
                        continue
                    value = r[idx] if idx < len(r) else ''
                    data[col] = str(value).strip() if value is not None else ''
                if any(v for v in data.values()):
                    rows.append(data)
    except Exception as e:
        flash(f'Unable to parse upload file: {str(e)}', 'danger')
        return redirect(url_for('users_list'))

    created = 0
    failed = 0
    errors = []
    for i, row in enumerate(rows, start=2):
        username = row.get('username', '').strip()
        password = row.get('password', '').strip()
        full_name = row.get('full_name', '').strip()
        role = row.get('role', '').strip().lower()
        cvo_office = row.get('cvo_office', '').strip().lower() or None
        assigned_cvo_username = row.get('assigned_cvo_username', '').strip() or None
        phone = row.get('phone', '').strip() or None
        email = row.get('email', '').strip() or None

        if not username or not password or not full_name or not role:
            failed += 1
            errors.append(f'Row {i}: required values missing.')
            continue
        if role not in VALID_USER_ROLES:
            failed += 1
            errors.append(f'Row {i}: invalid role "{role}".')
            continue
        if cvo_office and cvo_office not in VALID_CVO_OFFICES:
            failed += 1
            errors.append(f'Row {i}: invalid cvo_office "{cvo_office}".')
            continue
        if len(username) < 3:
            failed += 1
            errors.append(f'Row {i}: username must be at least 3 characters.')
            continue
        if len(password) < 6:
            failed += 1
            errors.append(f'Row {i}: password must be at least 6 characters.')
            continue
        if len(full_name) < 3:
            failed += 1
            errors.append(f'Row {i}: full_name must be at least 3 characters.')
            continue
        if not validate_contact(phone):
            failed += 1
            errors.append(f'Row {i}: invalid phone.')
            continue
        if not validate_email(email):
            failed += 1
            errors.append(f'Row {i}: invalid email.')
            continue
        if role == 'inspector' and (not cvo_office or not assigned_cvo_username):
            failed += 1
            errors.append(f'Row {i}: inspector requires cvo_office and assigned_cvo_username.')
            continue
        if role == 'data_entry' and not cvo_office:
            failed += 1
            errors.append(f'Row {i}: data_entry requires cvo_office.')
            continue
        if (role.startswith('cvo_') or role == 'dsp') and not cvo_office:
            failed += 1
            errors.append(f'Row {i}: cvo_office is required for {role}.')
            continue
        if role != 'inspector' and assigned_cvo_username:
            failed += 1
            errors.append(f'Row {i}: assigned_cvo_username is allowed only for inspector role.')
            continue

        assigned_cvo_id = None
        if assigned_cvo_username:
            cvo_user = models.get_user_by_username(assigned_cvo_username)
            if not cvo_user or cvo_user.get('role') not in ('cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp'):
                failed += 1
                errors.append(f'Row {i}: assigned_cvo_username "{assigned_cvo_username}" is invalid.')
                continue
            assigned_cvo_id = cvo_user['id']

        try:
            models.create_user(username, password, full_name, role, cvo_office, assigned_cvo_id, phone, email)
            created += 1
        except Exception as e:
            failed += 1
            errors.append(f'Row {i}: {str(e)}')

    if created:
        flash(f'Bulk user upload complete. Created: {created}, Failed: {failed}.', 'success')
    if failed:
        preview = '; '.join(errors[:5])
        if len(errors) > 5:
            preview += '; ...'
        flash(f'Upload errors: {preview}', 'warning')

    return redirect(url_for('users_list'))

@app.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@role_required('super_admin')
def user_toggle(user_id):
    try:
        models.toggle_user_status(user_id)
        flash('User status updated.', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('users_list'))

@app.route('/users/<int:user_id>/edit', methods=['POST'])
@login_required
@role_required('super_admin')
def user_edit(user_id):
    try:
        full_name = request.form.get('full_name', '').strip()
        role = (request.form.get('role') or '').strip()
        cvo_office = (request.form.get('cvo_office') or '').strip() or None
        assigned_cvo_id = parse_optional_int(request.form.get('assigned_cvo_id'))
        phone = request.form.get('phone', '').strip() or None
        email = request.form.get('email', '').strip() or None
        password = request.form.get('password', '').strip() or None

        if not full_name or len(full_name) < 3:
            flash('Officer name must be at least 3 characters.', 'warning')
            return redirect(url_for('users_list'))
        if role not in VALID_USER_ROLES:
            flash('Please select a valid role.', 'warning')
            return redirect(url_for('users_list'))
        if cvo_office and cvo_office not in VALID_CVO_OFFICES:
            flash('Please select a valid office.', 'warning')
            return redirect(url_for('users_list'))
        if password and len(password) < 6:
            flash('Password must be at least 6 characters.', 'warning')
            return redirect(url_for('users_list'))
        if not validate_contact(phone):
            flash('Please provide a valid phone number.', 'warning')
            return redirect(url_for('users_list'))
        if not validate_email(email):
            flash('Please provide a valid email address.', 'warning')
            return redirect(url_for('users_list'))
        if role == 'inspector':
            if not cvo_office:
                flash('Office is required for inspector role.', 'warning')
                return redirect(url_for('users_list'))
            if not assigned_cvo_id:
                flash('Please assign inspector to a CVO/DSP.', 'warning')
                return redirect(url_for('users_list'))
        elif role == 'data_entry':
            if not cvo_office:
                flash('Office is required for Data Entry role.', 'warning')
                return redirect(url_for('users_list'))
            assigned_cvo_id = None
        elif role.startswith('cvo_') or role == 'dsp':
            if not cvo_office:
                flash('Office is required for CVO/DSP role.', 'warning')
                return redirect(url_for('users_list'))
            assigned_cvo_id = None
        else:
            cvo_office = None
            assigned_cvo_id = None
        if assigned_cvo_id:
            cvo_user = models.get_user_by_id(assigned_cvo_id)
            if not cvo_user or cvo_user.get('role') not in ('cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp'):
                flash('Assigned CVO/DSP is invalid.', 'warning')
                return redirect(url_for('users_list'))
        
        models.update_user(user_id, full_name, role, cvo_office, assigned_cvo_id, phone, email, password)
        flash('User updated successfully!', 'success')
    except Exception as e:
        flash(f'Error: {str(e)}', 'danger')
    
    return redirect(url_for('users_list'))

@app.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@role_required('super_admin')
def user_reset_password(user_id):
    try:
        new_password = request.form.get('new_password', '').strip()
        if len(new_password) < 6:
            flash('Password must be at least 6 characters.', 'warning')
            return redirect(url_for('users_list'))
        
        models.set_user_password(user_id, new_password)
        flash('Password reset successfully.', 'success')
    except Exception as e:
        flash(f'Error resetting password: {str(e)}', 'danger')
    
    return redirect(url_for('users_list'))

@app.route('/users/<int:user_id>/reset-username', methods=['POST'])
@login_required
@role_required('super_admin')
def user_reset_username(user_id):
    try:
        new_username = request.form.get('new_username', '').strip()
        if not new_username:
            flash('Username cannot be empty.', 'warning')
            return redirect(url_for('users_list'))
        
        if len(new_username) < 3:
            flash('Username must be at least 3 characters.', 'warning')
            return redirect(url_for('users_list'))
        if not re.match(r'^[A-Za-z0-9_.-]+$', new_username):
            flash('Username can only contain letters, numbers, dot, underscore, and hyphen.', 'warning')
            return redirect(url_for('users_list'))
        
        models.set_username(user_id, new_username)
        flash('Username updated successfully.', 'success')
    except Exception as e:
        error_text = str(e).lower()
        if 'unique' in error_text or 'duplicate key' in error_text:
            flash('Username already exists. Choose a different username.', 'danger')
        else:
            flash(f'Error updating username: {str(e)}', 'danger')
    
    return redirect(url_for('users_list'))


@app.route('/users/<int:user_id>/update-name', methods=['POST'])
@login_required
@role_required('super_admin')
def user_update_name(user_id):
    try:
        full_name = request.form.get('full_name', '').strip()
        if len(full_name) < 3:
            flash('Officer name must be at least 3 characters.', 'warning')
            return redirect(url_for('users_list'))

        models.update_user_full_name(user_id, full_name)
        flash('Officer name updated successfully.', 'success')
    except Exception as e:
        flash(f'Error updating officer name: {str(e)}', 'danger')

    return redirect(url_for('users_list'))


@app.route('/users/<int:user_id>/update-contact', methods=['POST'])
@login_required
@role_required('super_admin')
def user_update_contact(user_id):
    try:
        phone = (request.form.get('phone') or '').strip() or None
        email = (request.form.get('email') or '').strip() or None
        remove_photo = request.form.get('remove_photo') == 'on'
        photo_upload = request.files.get('profile_photo')

        if not validate_contact(phone):
            flash('Please provide a valid phone number.', 'warning')
            return redirect(url_for('users_list'))
        if not validate_email(email):
            flash('Please provide a valid email address.', 'warning')
            return redirect(url_for('users_list'))

        user = models.get_user_by_id(user_id)
        if not user:
            flash('User not found.', 'warning')
            return redirect(url_for('users_list'))

        ok_photo, stored_photo_name, photo_error = validate_profile_photo_upload(photo_upload, user_id)
        if not ok_photo:
            flash(photo_error, 'warning')
            return redirect(url_for('users_list'))

        old_photo = user.get('profile_photo')
        photo_changed = False
        try:
            models.update_user_profile_info(
                user_id,
                user.get('full_name'),
                phone,
                email
            )
            if stored_photo_name and photo_upload:
                ensure_upload_dirs()
                photo_upload.save(os.path.join(PROFILE_UPLOAD_DIR, stored_photo_name))
                models.set_user_profile_photo(user_id, stored_photo_name)
                photo_changed = True
            elif remove_photo and old_photo:
                models.set_user_profile_photo(user_id, None)
                photo_changed = True

            if photo_changed and old_photo and old_photo != stored_photo_name:
                delete_profile_photo_file(old_photo)

            if session.get('user_id') == user_id:
                refresh_session_user()
            flash('User contact/profile photo updated.', 'success')
        except Exception as e:
            if stored_photo_name:
                delete_profile_photo_file(stored_photo_name)
            flash(f'Error updating contact/photo: {str(e)}', 'danger')
    except Exception as e:
        flash(f'Error updating contact/photo: {str(e)}', 'danger')

    return redirect(url_for('users_list'))

@app.route('/users/<int:inspector_id>/map-cvo', methods=['POST'])
@login_required
@role_required('super_admin')
def user_map_cvo(inspector_id):
    try:
        cvo_id_raw = request.form.get('cvo_id', '').strip()
        if not cvo_id_raw:
            flash('Please select a CVO/DSP for mapping.', 'warning')
            return redirect(url_for('users_list'))

        cvo_id = parse_optional_int(cvo_id_raw)
        if not cvo_id:
            flash('Please select a valid CVO/DSP for mapping.', 'warning')
            return redirect(url_for('users_list'))

        cvo_user = models.get_user_by_id(cvo_id)
        if not cvo_user or cvo_user.get('role') not in ('cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp'):
            flash('Selected CVO/DSP mapping is invalid.', 'warning')
            return redirect(url_for('users_list'))

        models.map_inspector_to_cvo(inspector_id, cvo_id)
        flash('Field inspector mapped to CVO/DSP successfully.', 'success')
    except Exception as e:
        flash(f'Error mapping inspector: {str(e)}', 'danger')

    return redirect(url_for('users_list'))

# ========================================
# API ENDPOINTS
# ========================================

@app.route('/api/inspectors/<int:cvo_id>')
@login_required
def api_inspectors(cvo_id):
    inspectors = models.get_inspectors_by_cvo(cvo_id)
    return jsonify([{'id': i['id'], 'full_name': i['full_name']} for i in inspectors])

@app.route('/api/stats')
@login_required
def api_stats():
    stats = models.get_dashboard_stats(session['user_role'], session['user_id'], session.get('cvo_office'))
    return jsonify(stats)


@app.route('/api/dashboard-drilldown')
@login_required
def api_dashboard_drilldown():
    metric = request.args.get('metric', '').strip()
    if not metric:
        return jsonify({'items': []})
    rows = models.get_dashboard_drilldown(
        session['user_role'],
        session['user_id'],
        session.get('cvo_office'),
        metric
    )
    items = []
    for p in rows:
        items.append({
            'id': p.get('id'),
            'sno': p.get('sno'),
            'petitioner_name': p.get('petitioner_name'),
            'subject': p.get('subject'),
            'status': p.get('status'),
            'received_date': p.get('received_date').strftime('%d/%m/%Y') if p.get('received_date') else '-'
        })
    return jsonify({'items': items})


@app.route('/api/dashboard-analytics')
@login_required
def api_dashboard_analytics():
    user_role = session['user_role']
    user_id = session['user_id']
    cvo_office = session.get('cvo_office')
    petitions = get_petitions_for_user_cached(user_id, user_role, cvo_office)
    officer_lookup = {}
    for p in petitions:
        officer_id = p.get('assigned_inspector_id')
        officer_name = (p.get('inspector_name') or '').strip()
        if officer_id and officer_name:
            officer_lookup[int(officer_id)] = officer_name
    dashboard_filter = _extract_dashboard_filters(request.args, officer_lookup)
    filtered_petitions = _apply_dashboard_filters(petitions, dashboard_filter)
    stats = _build_filtered_dashboard_stats(user_role, user_id, petitions, filtered_petitions)
    analytics = _build_dashboard_analytics(filtered_petitions, stats)
    return jsonify({'analytics': analytics, 'summary': analytics.get('summary', {})})

@app.route('/healthz')
def healthz():
    return jsonify({'status': 'ok'}), 200

# ========================================
# RUN
# ========================================

if __name__ == '__main__':
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)

