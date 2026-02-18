from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from functools import wraps
from config import Config
import models
from datetime import datetime
from collections import Counter
import os
import io
import csv
import re
import copy
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
MAX_UPLOAD_SIZE_BYTES = config.MAX_UPLOAD_SIZE_MB * 1024 * 1024
VALID_RECEIVED_AT = {'jmd_office', 'cvo_apspdcl_tirupathi', 'cvo_apepdcl_vizag', 'cvo_apcpdcl_vijayawada'}
VALID_TARGET_CVO = {'apspdcl', 'apepdcl', 'apcpdcl', 'headquarters'}
VALID_ENQUIRY_TYPES = {'detailed', 'preliminary'}
VALID_SOURCE_OF_PETITION = {'media', 'public_individual', 'govt', 'sumoto'}
VALID_GOVT_INSTITUTIONS = {
    'aprc',
    'governor',
    'cs_energy_department',
    'cmd_aptransco',
    'cmo',
    'energy_department',
}
VALID_PETITION_TYPES = {'bribe', 'harassment', 'theft_of_materials', 'adverse_news', 'procedural_lapses', 'other'}
VALID_PERMISSION_REQUEST_TYPES = {'direct_enquiry', 'permission_required'}
DIRECT_ENQUIRY_EFILE_EDITABLE_STATUSES = {'received', 'forwarded_to_cvo', 'assigned_to_inspector', 'enquiry_in_progress'}
VALID_USER_ROLES = {
    'super_admin', 'data_entry', 'po',
    'cmd_apspdcl', 'cmd_apepdcl', 'cmd_apcpdcl',
    'cgm_hr_transco',
    'dsp', 'cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'inspector'
}
VALID_CVO_OFFICES = {'apspdcl', 'apepdcl', 'apcpdcl', 'headquarters'}
PHONE_RE = re.compile(r'^[0-9+\-\s()]{7,20}$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
VALID_DYNAMIC_FIELD_TYPES = {'text', 'textarea', 'select', 'date', 'tel', 'email', 'file'}

DEFAULT_FORM_FIELD_CONFIGS = {
    'deo_petition.petitioner_name': {'label': 'Petitioner Name', 'type': 'text', 'required': False, 'options': []},
    'deo_petition.contact': {'label': 'Contact Number', 'type': 'tel', 'required': False, 'options': []},
    'deo_petition.place': {'label': 'Place', 'type': 'text', 'required': False, 'options': []},
    'deo_petition.subject': {'label': 'Subject', 'type': 'textarea', 'required': True, 'options': []},
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
    'cvo_review.cvo_comments': {'label': 'CVO Comments on Enquiry Report', 'type': 'textarea', 'required': True, 'options': []},
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
    'cvo_review': 'CVO Review Form',
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


def get_effective_form_field_configs():
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
    return merged


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
        'cvo_apspdcl': 'CVO - APSPDCL (Tirupathi)',
        'cvo_apepdcl': 'CVO - APEPDCL (Vizag)',
        'cvo_apcpdcl': 'CVO - APCPDCL (Vijayawada)',
        'inspector': 'Field Inspector (CI/SI)'
    }
    status_labels = {
        'received': 'Received',
        'forwarded_to_cvo': 'Forwarded to CVO',
        'sent_for_permission': 'Sent for Permission',
        'permission_approved': 'Permission Approved',
        'permission_rejected': 'Permission Rejected',
        'assigned_to_inspector': 'Assigned to Inspector',
        'enquiry_in_progress': 'Enquiry In Progress',
        'enquiry_report_submitted': 'Enquiry Report Submitted',
        'cvo_comments_added': 'CVO Comments Added',
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
    petition_types = {
        'bribe': 'Bribe',
        'harassment': 'Harassment',
        'theft_of_materials': 'Theft of Materials',
        'adverse_news': 'Adverse News',
        'procedural_lapses': 'Procedural Lapses',
        'other': 'Other'
    }
    petition_sources = {
        'media': 'Media',
        'public_individual': 'Public (Individual)',
        'govt': 'Govt',
        'sumoto': 'Sumoto'
    }
    cfg = get_effective_form_field_configs()
    govt_options = cfg.get('deo_petition.govt_institution_type', {}).get('options', [])
    govt_labels = {o.get('value'): o.get('label') for o in govt_options if isinstance(o, dict)}
    return dict(
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
        current_user_name=session.get('full_name'),
        current_user_id=session.get('user_id'),
        now=datetime.now()
    )

# ========================================
# AUTH ROUTES
# ========================================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = models.authenticate_user(username, password)
        if user:
            if user['role'] == 'jmd':
                flash('JMD login is disabled. Please login using PO credentials.', 'warning')
                return redirect(url_for('login'))
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['user_role'] = user['role']
            session['cvo_office'] = user.get('cvo_office')
            flash(f'Welcome, {user["full_name"]}!', 'success')
            try:
                visible_petitions = models.get_petitions_for_user(
                    user['id'],
                    user['role'],
                    user.get('cvo_office')
                )
                pending_count = sum(1 for p in visible_petitions if p.get('status') != 'closed')
                if pending_count > 0:
                    flash(f'Notification: {pending_count} petition(s) are currently pending in your login.', 'info')
            except Exception:
                # Notification fetch should never block login.
                pass
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')

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
    
    stats = models.get_dashboard_stats(user_role, user_id, cvo_office)
    petitions = models.get_petitions_for_user(user_id, user_role, cvo_office)
    analytics = _build_dashboard_analytics(petitions, stats)
    
    return render_template('dashboard.html', stats=stats, petitions=petitions, analytics=analytics)


def _build_dashboard_analytics(petitions, stats):
    status_labels = {
        'received': 'Received',
        'forwarded_to_cvo': 'Forwarded to CVO/DSP',
        'sent_for_permission': 'Sent for Permission',
        'permission_approved': 'Permission Approved',
        'permission_rejected': 'Permission Rejected',
        'assigned_to_inspector': 'Assigned to Field Officer',
        'enquiry_in_progress': 'Enquiry In Progress',
        'enquiry_report_submitted': 'Report Submitted',
        'cvo_comments_added': 'CVO/DSP Comments Added',
        'forwarded_to_po': 'Forwarded to PO',
        'action_instructed': 'Action Pending at CMD',
        'action_taken': 'Action Taken by CMD',
        'lodged': 'Lodged',
        'closed': 'Closed'
    }
    petition_type_labels = {
        'bribe': 'Bribe',
        'harassment': 'Harassment',
        'theft_of_materials': 'Theft',
        'adverse_news': 'Adverse News',
        'procedural_lapses': 'Procedural Lapses',
        'other': 'Other'
    }
    source_labels = {
        'media': 'Media',
        'public_individual': 'Public',
        'govt': 'Govt',
        'sumoto': 'Sumoto'
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

    return {
        'monthly_trend': {
            'labels': [m['label'] for m in months],
            'values': [m['value'] for m in months]
        },
        'status_split': _counter_to_series(status_counts, limit=10),
        'type_split': _counter_to_series(type_counts, limit=8),
        'source_split': _counter_to_series(source_counts, limit=8),
        'enquiry_mode_split': _counter_to_series(permission_mode_counts, limit=0),
        'office_split': _counter_to_series(office_counts, limit=6),
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
        is_jmd_received = (received_at == 'jmd_office')
        received_date_raw = request.form.get('received_date')
        received_date = parse_date_input(received_date_raw)
        remarks = request.form.get('remarks', '').strip()
        petition_cfg = get_effective_form_field_configs()
        cfg_petitioner = petition_cfg.get('deo_petition.petitioner_name', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.petitioner_name'])
        cfg_contact = petition_cfg.get('deo_petition.contact', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.contact'])
        cfg_place = petition_cfg.get('deo_petition.place', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.place'])
        cfg_subject = petition_cfg.get('deo_petition.subject', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.subject'])
        cfg_remarks = petition_cfg.get('deo_petition.remarks', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.remarks'])
        cfg_govt_institution = petition_cfg.get('deo_petition.govt_institution_type', DEFAULT_FORM_FIELD_CONFIGS['deo_petition.govt_institution_type'])

        if not received_date:
            flash('Please provide a valid received date.', 'warning')
            return render_template('petition_form.html')
        if received_at not in VALID_RECEIVED_AT:
            flash('Please select a valid received-at office.', 'warning')
            return render_template('petition_form.html')
        if not subject:
            flash(f"{cfg_subject.get('label', 'Subject')} is required.", 'warning')
            return render_template('petition_form.html')
        if petition_type not in VALID_PETITION_TYPES:
            flash('Please select a valid petition type.', 'warning')
            return render_template('petition_form.html')
        if source_of_petition not in VALID_SOURCE_OF_PETITION:
            flash('Please select a valid source of petition.', 'warning')
            return render_template('petition_form.html')
        govt_option_values = {o.get('value') for o in cfg_govt_institution.get('options', []) if isinstance(o, dict)}
        if source_of_petition == 'govt' and cfg_govt_institution.get('required') and not govt_institution_type:
            flash(f"Please select {cfg_govt_institution.get('label', 'Type of Institution')}.", 'warning')
            return render_template('petition_form.html')
        if source_of_petition == 'govt' and govt_institution_type and govt_institution_type not in govt_option_values:
            flash('Please select a valid Govt institution type.', 'warning')
            return render_template('petition_form.html')
        if cfg_petitioner.get('required') and not petitioner_name:
            flash(f"{cfg_petitioner.get('label', 'Petitioner Name')} is required.", 'warning')
            return render_template('petition_form.html')
        if cfg_contact.get('required') and not contact:
            flash(f"{cfg_contact.get('label', 'Contact Number')} is required.", 'warning')
            return render_template('petition_form.html')
        if cfg_place.get('required') and not place:
            flash(f"{cfg_place.get('label', 'Place')} is required.", 'warning')
            return render_template('petition_form.html')
        if cfg_remarks.get('required') and not remarks:
            flash(f"{cfg_remarks.get('label', 'Remarks')} is required.", 'warning')
            return render_template('petition_form.html')
        if not is_jmd_received:
            if permission_request_type not in VALID_PERMISSION_REQUEST_TYPES:
                flash('Please select a valid permission request type.', 'warning')
                return render_template('petition_form.html')
            if target_cvo not in VALID_TARGET_CVO:
                flash('Please select a valid Target CVO Jurisdiction.', 'warning')
                return render_template('petition_form.html')
        if petitioner_name and len(petitioner_name) > 255:
            flash('Petitioner name is too long.', 'warning')
            return render_template('petition_form.html')
        if len(subject) > 5000:
            flash('Subject is too long.', 'warning')
            return render_template('petition_form.html')
        if len(place) > 255:
            flash('Place is too long.', 'warning')
            return render_template('petition_form.html')
        if not validate_contact(contact):
            flash('Please provide a valid contact number.', 'warning')
            return render_template('petition_form.html')
        if ereceipt_no and len(ereceipt_no) > 100:
            flash('E-Receipt No is too long.', 'warning')
            return render_template('petition_form.html')
        if len(remarks) > 5000:
            flash('Remarks are too long.', 'warning')
            return render_template('petition_form.html')

        if ereceipt_file and ereceipt_file.filename:
            ok, upload_result = validate_pdf_upload(ereceipt_file, 'DEO e-receipt file')
            if not ok:
                flash(upload_result, 'danger')
                return render_template('petition_form.html')
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
            'received_date': received_date,
            'remarks': remarks,
            'ereceipt_no': ereceipt_no,
            'ereceipt_file': ereceipt_filename
        }
        
        try:
            if data['permission_request_type'] == 'direct_enquiry':
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
                    comments='Auto-forwarded to concerned CVO from Data Entry'
                )
                flash(f'Petition {result["sno"]} created and auto-forwarded to CVO successfully!', 'success')
            return redirect(url_for('petition_view', petition_id=result['id']))
        except Exception as e:
            flash(f'Error creating petition: {str(e)}', 'danger')
    
    return render_template('petition_form.html')

@app.route('/petitions/<int:petition_id>')
@login_required
def petition_view(petition_id):
    petition = models.get_petition_by_id(petition_id)
    if not petition:
        flash('Petition not found.', 'danger')
        return redirect(url_for('petitions_list'))
    
    tracking = models.get_petition_tracking(petition_id)
    report = models.get_enquiry_report(petition_id)
    
    # Get inspectors for CVO roles
    inspectors = []
    cvo_users = []
    if session['user_role'] in ('cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp'):
        inspectors = models.get_inspectors_by_cvo(session['user_id'])
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
                flash('You are not allowed to forward petitions to CVO.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            target_cvo = (request.form.get('target_cvo') or '').strip()
            if target_cvo not in VALID_TARGET_CVO:
                flash('Please select a valid target CVO.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            models.forward_petition_to_cvo(petition_id, user_id, target_cvo, comments)
            flash('Petition forwarded to CVO successfully.', 'success')
            
        elif action == 'send_for_permission':
            if user_role not in ('super_admin', 'po'):
                flash('Only PO can send petitions for permission routing.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            models.send_for_permission(petition_id, user_id, comments)
            flash('Petition sent to PO for permission.', 'success')

        elif action == 'send_receipt_to_po':
            if user_role not in ('super_admin', 'cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp'):
                flash('Only CVO can send receipt to PO.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            petition = models.get_petition_by_id(petition_id)
            if petition and not petition.get('requires_permission'):
                flash('This petition is marked as Direct Enquiry. Permission request is not required.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            models.cvo_send_receipt_to_po(petition_id, user_id, comments)
            flash('Receipt sent to PO for permission processing.', 'success')
            
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
                flash('Please select a valid target CVO.', 'warning')
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
            flash('Permission granted and pushed to respective CVO.', 'success')

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
            if user_role not in ('super_admin', 'cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp'):
                flash('Only CVO can assign inspectors.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            petition = models.get_petition_by_id(petition_id)
            if petition and petition.get('requires_permission') and petition.get('status') != 'permission_approved':
                flash('Permission is compulsory. PO approval required before assigning inspector.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if petition and not petition.get('requires_permission') and petition.get('status') != 'forwarded_to_cvo':
                flash('For Direct Enquiry, inspector can be assigned only when petition is at CVO.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            inspector_id = parse_optional_int(request.form.get('inspector_id'))
            if not inspector_id:
                flash('Please select a valid field inspector.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            enquiry_type_decision = None
            if petition and not petition.get('requires_permission'):
                enquiry_type_decision = (request.form.get('enquiry_type_decision') or '').strip()
                if enquiry_type_decision not in VALID_ENQUIRY_TYPES:
                    flash('Please select enquiry type decision (Detailed/Preliminary).', 'warning')
                    return redirect(url_for('petition_view', petition_id=petition_id))
            models.assign_to_inspector(petition_id, user_id, inspector_id, comments, enquiry_type_decision)
            flash('Petition assigned to inspector.', 'success')

        elif action == 'submit_report':
            if user_role not in ('super_admin', 'inspector'):
                flash('Only inspectors can upload enquiry report.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            form_cfg = get_effective_form_field_configs()
            cfg_report_text = form_cfg.get('inspector_report.report_text', DEFAULT_FORM_FIELD_CONFIGS['inspector_report.report_text'])
            cfg_recommendation = form_cfg.get('inspector_report.recommendation', DEFAULT_FORM_FIELD_CONFIGS['inspector_report.recommendation'])
            cfg_report_file = form_cfg.get('inspector_report.report_file', DEFAULT_FORM_FIELD_CONFIGS['inspector_report.report_file'])
            report_text = request.form.get('report_text', '').strip()
            recommendation = request.form.get('recommendation', '').strip()
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
            report_file = request.files.get('report_file')
            if cfg_report_file.get('required') and (not report_file or not report_file.filename):
                flash('Enquiry report file (PDF) is compulsory.', 'warning')
                return redirect(url_for('petition_view', petition_id=petition_id))
            if not report_file or not report_file.filename:
                report_filename = None
                models.submit_enquiry_report(petition_id, user_id, report_text, '', recommendation, report_filename)
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
            models.submit_enquiry_report(petition_id, user_id, report_text, '', recommendation, report_filename)
            flash('Enquiry report uploaded successfully.', 'success')
            
        elif action == 'cvo_comments':
            if user_role not in ('super_admin', 'cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp'):
                flash('Only CVO can enter remarks.', 'danger')
                return redirect(url_for('petition_view', petition_id=petition_id))
            form_cfg = get_effective_form_field_configs()
            cfg_cvo_comments = form_cfg.get('cvo_review.cvo_comments', DEFAULT_FORM_FIELD_CONFIGS['cvo_review.cvo_comments'])
            cfg_cvo_file = form_cfg.get('cvo_review.consolidated_report_file', DEFAULT_FORM_FIELD_CONFIGS['cvo_review.consolidated_report_file'])
            cvo_comments = request.form.get('cvo_comments', '').strip()
            if cfg_cvo_comments.get('required') and not cvo_comments:
                flash(f"{cfg_cvo_comments.get('label', 'CVO comments')} are required.", 'warning')
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

        elif action == 'upload_consolidated_report':
            if user_role not in ('super_admin', 'cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp'):
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
            if user_role not in ('super_admin', 'cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp'):
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
    return render_template(
        'users.html',
        users=users,
        cvo_users=cvo_users,
        role_login_users=role_login_users,
        inspector_mappings=inspector_mappings
    )

@app.route('/form-management', methods=['GET', 'POST'])
@login_required
@role_required('super_admin')
def form_management():
    if request.method == 'POST':
        form_key = (request.form.get('form_key') or '').strip()
        field_key = (request.form.get('field_key') or '').strip()
        config_key = f'{form_key}.{field_key}'
        if config_key not in DEFAULT_FORM_FIELD_CONFIGS:
            flash('Invalid form field selection.', 'danger')
            return redirect(url_for('form_management'))

        label = (request.form.get('label') or '').strip() or DEFAULT_FORM_FIELD_CONFIGS[config_key]['label']
        field_type = (request.form.get('field_type') or '').strip()
        if field_type not in VALID_DYNAMIC_FIELD_TYPES:
            flash('Invalid field type.', 'danger')
            return redirect(url_for('form_management'))

        is_required = request.form.get('is_required') == 'on'
        options = []
        if DEFAULT_FORM_FIELD_CONFIGS[config_key]['type'] == 'select' or field_type == 'select':
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
                options = DEFAULT_FORM_FIELD_CONFIGS[config_key].get('options', [])

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

@app.route('/users/<int:inspector_id>/map-cvo', methods=['POST'])
@login_required
@role_required('super_admin')
def user_map_cvo(inspector_id):
    try:
        cvo_id_raw = request.form.get('cvo_id', '').strip()
        if not cvo_id_raw:
            flash('Please select a CVO for mapping.', 'warning')
            return redirect(url_for('users_list'))

        cvo_id = parse_optional_int(cvo_id_raw)
        if not cvo_id:
            flash('Please select a valid CVO for mapping.', 'warning')
            return redirect(url_for('users_list'))

        cvo_user = models.get_user_by_id(cvo_id)
        if not cvo_user or cvo_user.get('role') not in ('cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp'):
            flash('Selected CVO/DSP mapping is invalid.', 'warning')
            return redirect(url_for('users_list'))

        models.map_inspector_to_cvo(inspector_id, cvo_id)
        flash('Field inspector mapped to CVO successfully.', 'success')
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

@app.route('/healthz')
def healthz():
    return jsonify({'status': 'ok'}), 200

# ========================================
# RUN
# ========================================

if __name__ == '__main__':
    app.run(debug=config.DEBUG, host=config.HOST, port=config.PORT)

