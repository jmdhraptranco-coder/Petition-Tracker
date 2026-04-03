# Live Server Technical Specification

## 1. Application Summary

Application name: `Nigaa Petition Tracker`
Client name: `Vigilance`

Purpose:
- Track vigilance petitions from intake through assignment, enquiry, review, action, and closure.
- Support role-based workflow across Super Admin, Data Entry, JMD, PO, CVO offices, inspectors, and management roles.

Technology stack:
- Backend: Python 3.10+ / Flask
- WSGI server: Waitress
- Database: PostgreSQL
- Frontend: Jinja2 templates, HTML, CSS, JavaScript
- Authentication: Server-side session authentication stored in PostgreSQL
- File storage: Filesystem storage under configured upload directory

Code entry points:
- Development: [app.py](c:\Users\AP TRANSCO\OneDrive - APTRANSCO\Pictures\Petition Tracker with chatbot\app.py)
- Production server runner: [serve.py](c:\Users\AP TRANSCO\OneDrive - APTRANSCO\Pictures\Petition Tracker with chatbot\serve.py)
- WSGI entry point: [wsgi.py](c:\Users\AP TRANSCO\OneDrive - APTRANSCO\Pictures\Petition Tracker with chatbot\wsgi.py)
- Database access layer: [models.py](c:\Users\AP TRANSCO\OneDrive - APTRANSCO\Pictures\Petition Tracker with chatbot\models.py)
- Runtime configuration: [config.py](c:\Users\AP TRANSCO\OneDrive - APTRANSCO\Pictures\Petition Tracker with chatbot\config.py)

## 2. Recommended Production Architecture

Recommended topology:
1. Reverse proxy / web gateway
2. Waitress-hosted Flask application
3. PostgreSQL database server
4. Shared or local filesystem for uploads

Recommended production layout:
- OS: Windows Server or Linux server
- Python virtual environment dedicated to this application
- Reverse proxy:
  - Windows: IIS with reverse proxy or ARR
  - Linux: Nginx or Apache
- App listener: `127.0.0.1:5000` or internal server IP
- Public TLS termination at reverse proxy/load balancer

Important runtime behavior:
- App startup executes `models.ensure_schema_updates()` unless `SKIP_SCHEMA_UPDATES=1`.
- That means first production startup requires DB permissions to create/alter application objects if schema is not already aligned.

## 3. Functional Modules

Primary modules:
- Authentication and login
- Password recovery integration
- Petition creation and workflow tracking
- Petition bulk import from Excel
- Enquiry report submission and review
- Dashboard and analytics APIs
- User and role management
- Help center resource management
- System settings and form field configuration
- Embedded chatbot API for petition assistance

Main HTTP endpoints:
- `/login`
- `/dashboard`
- `/petitions`
- `/petitions/new`
- `/petitions/import`
- `/users`
- `/form-management`
- `/system-settings`
- `/help-center`
- `/api/*`
- `/healthz`

Health endpoint:
- `GET /healthz`
- Current implementation returns `{"status":"ok"}` and does not validate DB connectivity.

## 4. Runtime and Dependency Specification

Minimum software:
- Python 3.10 or higher
- PostgreSQL 13 or higher
- pip

Python package dependencies from [requirements.txt](c:\Users\AP TRANSCO\OneDrive - APTRANSCO\Pictures\Petition Tracker with chatbot\requirements.txt):
- `flask`
- `psycopg2-binary`
- `werkzeug`
- `waitress`
- `python-dotenv`
- `openpyxl`
- `pytest`
- `pytest-cov`
- `ruff`
- `rapidfuzz`

Production-relevant libraries:
- `Flask`: web framework
- `psycopg2-binary`: PostgreSQL connectivity
- `waitress`: WSGI server
- `openpyxl`: Excel import handling
- `rapidfuzz`: chatbot fuzzy matching

## 5. Environment Variable Specification

Source:
- Local `.env` file auto-loaded by [config.py](c:\Users\AP TRANSCO\OneDrive - APTRANSCO\Pictures\Petition Tracker with chatbot\config.py)

Mandatory for production:
- `APP_ENV=production`
- `SECRET_KEY=<strong-random-secret>`
- Either `DATABASE_URL` or full DB field set

Database variables:
- `DATABASE_URL`
- `DB_HOST`
- `DB_PORT`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_SSLMODE`
- `DB_CONNECT_TIMEOUT`
- `DB_SCHEMA`

Application/runtime variables:
- `HOST`
- `PORT`
- `FILE_STORAGE_PATH` or `UPLOAD_BASE_DIR`
- `MAX_UPLOAD_SIZE_MB`
- `SESSION_LIFETIME_MINUTES`
- `TRUST_PROXY_HEADERS`

Security/rate limit variables:
- `LOGIN_RATE_LIMIT_WINDOW_SECONDS`
- `LOGIN_RATE_LIMIT_MAX_ATTEMPTS`
- `LOGIN_RATE_LIMIT_BLOCK_SECONDS`
- `PETITION_USER_RATE_LIMIT_WINDOW_SECONDS`
- `PETITION_USER_RATE_LIMIT_MAX_SUBMISSIONS`
- `PETITION_USER_RATE_LIMIT_BLOCK_SECONDS`
- `PETITION_IP_RATE_LIMIT_WINDOW_SECONDS`
- `PETITION_IP_RATE_LIMIT_MAX_SUBMISSIONS`
- `PETITION_IP_RATE_LIMIT_BLOCK_SECONDS`

Branding variables:
- `BRAND_NAME`
- `BRAND_SUBTITLE`
- `BRAND_LOGO_FILE`
- `BRAND_LOGO_FALLBACK`

Password recovery settings now use the main application configuration.

Current repo-local DB pattern observed in `.env`:
- `DB_NAME=postgres`
- `DB_SCHEMA=vigilance_tracker`

Interpretation:
- The application can run either in its own database or inside a dedicated PostgreSQL schema within an existing database.
- In the current local configuration, application tables are expected inside schema `vigilance_tracker` of database `postgres`.

## 6. File Storage Specification

Base upload directory:
- Resolved from `FILE_STORAGE_PATH` or `UPLOAD_BASE_DIR`

Subdirectories used by the application:
- `e_receipts`
- `enquiry_reports`
- `profile_photos`
- `help_resources`

Operational requirement:
- The application service account must have read/write/create permissions on the upload base directory.

Recommended production approach:
- Keep uploads outside the code deployment folder if possible.
- Use a dedicated disk path or managed file share.
- Back up uploads together with the database.

## 7. Database Specification

### 7.1 Database Engine

Database engine:
- PostgreSQL

Connection behavior:
- `config.get_psycopg2_kwargs()` sets PostgreSQL `search_path` to `<DB_SCHEMA>,public`
- This allows logical isolation by schema

### 7.2 Base Schema Source

Base DDL file:
- [database.sql](c:\Users\AP TRANSCO\OneDrive - APTRANSCO\Pictures\Petition Tracker with chatbot\database.sql)

Runtime schema alignment:
- [models.py](c:\Users\AP TRANSCO\OneDrive - APTRANSCO\Pictures\Petition Tracker with chatbot\models.py) function `ensure_schema_updates()`

Important note:
- `database.sql` is not the full final schema by itself.
- Production DB must include both the base objects from `database.sql` and the additional changes created by `ensure_schema_updates()`.

### 7.3 PostgreSQL Enums

`user_role`:
- `super_admin`
- `data_entry`
- `jmd`
- `po`
- `cmd_apspdcl`
- `cmd_apepdcl`
- `cmd_apcpdcl`
- `cgm_hr_transco`
- `dsp`
- `cvo_apspdcl`
- `cvo_apepdcl`
- `cvo_apcpdcl`
- `inspector`

`petition_status`:
- `received`
- `forwarded_to_cvo`
- `sent_for_permission`
- `permission_approved`
- `permission_rejected`
- `assigned_to_inspector`
- `sent_back_for_reenquiry`
- `enquiry_in_progress`
- `enquiry_report_submitted`
- `cvo_comments_added`
- `forwarded_to_jmd`
- `forwarded_to_po`
- `conclusion_given`
- `action_instructed`
- `action_taken`
- `lodged`
- `closed`

`petition_type`:
- `bribe`
- `corruption`
- `harassment`
- `electrical_accident`
- `misconduct`
- `works_related`
- `irregularities_in_tenders`
- `illegal_assets`
- `fake_certificates`
- `theft_of_materials`
- `theft_misappropriation_materials`
- `adverse_news`
- `procedural_lapses`
- `other`

`receiving_office`:
- `jmd_office`
- `cvo_apspdcl_tirupathi`
- `cvo_apepdcl_vizag`
- `cvo_apcpdcl_vijayawada`

`cvo_office`:
- `apspdcl`
- `apepdcl`
- `apcpdcl`
- `headquarters`

### 7.4 Core Tables

`users`
- Stores login accounts and role assignment
- Primary key: `id`
- Important columns:
  - `username` unique
  - `password_hash`
  - `full_name`
  - `role`
  - `cvo_office`
  - `assigned_cvo_id`
  - `phone`
  - `email`
  - `profile_photo`
  - `must_change_password`
  - `session_version`
  - `is_active`

`petitions`
- Core petition transaction table
- Primary key: `id`
- Important columns:
  - `sno` unique
  - `efile_no`
  - `ereceipt_no`
  - `ereceipt_file`
  - `petitioner_name`
  - `contact`
  - `place`
  - `subject`
  - `petition_type`
  - `source_of_petition`
  - `govt_institution_type`
  - `organization`
  - `enquiry_type`
  - `received_at`
  - `target_cvo`
  - `status`
  - `requires_permission`
  - `permission_status`
  - `received_date`
  - `created_by`
  - `assigned_inspector_id`
  - `current_handler_id`
  - `conclusion_file`
  - `is_overdue_escalated`
  - `remarks`

`petition_tracking`
- Audit trail / workflow history
- Primary key: `id`
- Important columns:
  - `petition_id`
  - `from_user_id`
  - `to_user_id`
  - `from_role`
  - `to_role`
  - `action`
  - `comments`
  - `status_before`
  - `status_after`
  - `attachment_file`
  - `created_at`

`enquiry_reports`
- Stores enquiry output and later-stage review artifacts
- Primary key: `id`
- Important columns:
  - `petition_id`
  - `submitted_by`
  - `report_text`
  - `findings`
  - `recommendation`
  - `report_file`
  - `accident_type`
  - `deceased_category`
  - `non_departmental_type`
  - `departmental_type`
  - `deceased_count`
  - `general_public_count`
  - `animals_count`
  - `cvo_consolidated_report_file`
  - `cvo_comments`
  - `po_conclusion`
  - `po_instructions`
  - `conclusion_file`
  - `cmd_action_report_file`
  - `jmd_remarks`
  - `action_taken`

`help_resources`
- Help-center content metadata
- Primary key: `id`

### 7.5 Supporting Tables Added at Runtime

`form_field_configs`
- Admin-managed configuration for petition form labels, field types, required flags, and option lists

`user_signup_requests`
- Pending signup requests requiring review/approval

`password_reset_requests`
- Pending password reset requests requiring review/approval

`schema_migrations`
- One-time migration tracking table

`rate_limit_counters`
- Persistent counters for login/petition throttling

`system_settings`
- Server-side configurable application settings

`server_sessions`
- Database-backed Flask session store

### 7.6 Key Relationships

Relationship summary:
- `petitions.created_by -> users.id`
- `petitions.assigned_inspector_id -> users.id`
- `petitions.current_handler_id -> users.id`
- `petition_tracking.petition_id -> petitions.id`
- `petition_tracking.from_user_id -> users.id`
- `petition_tracking.to_user_id -> users.id`
- `enquiry_reports.petition_id -> petitions.id`
- `enquiry_reports.submitted_by -> users.id`
- `help_resources.uploaded_by -> users.id`
- `password_reset_requests.user_id -> users.id`
- `server_sessions.user_id -> users.id`

### 7.7 Indexing

Existing indexes cover:
- petition status
- petition received date / received office
- target CVO
- assigned inspector
- current handler
- petition type + source
- help resource activity/order
- signup/password-reset request review queues
- session expiry / session user lookup
- rate-limit cleanup access

### 7.8 Database Preparation for Live Server

Recommended DBA sequence:
1. Create database or confirm shared database choice.
2. Create dedicated schema, for example `vigilance_tracker`.
3. Create application DB user with permissions on that schema.
4. Run `database.sql` with search path pointing to target schema.
5. Start the app once with schema-alter permissions enabled so `ensure_schema_updates()` can complete.
6. Validate all expected tables/enums/indexes exist.

## 8. Security and Session Model

Implemented controls:
- Password hashing with Werkzeug
- Server-side sessions stored in PostgreSQL
- CSRF validation for state-changing requests
- Secure filename handling for uploads
- Request size limits using `MAX_CONTENT_LENGTH`
- Login and petition submission rate limiting
- Production session cookie secure flag when `APP_ENV=production`

Go-live recommendations:
- Use HTTPS only
- Put a strong random `SECRET_KEY`
- Restrict DB access by IP/network ACL
- Restrict upload directory OS permissions
- Schedule DB and file backups
- Monitor application availability and password recovery flow

## 9. Production Deployment Procedure

Recommended deployment steps:
1. Provision application server and PostgreSQL access.
2. Install Python and create virtual environment.
3. Copy application source to deployment folder.
4. Install dependencies from `requirements-lock.txt` if reproducibility is required.
5. Create and populate `.env` with production values.
6. Create upload storage directory and subfolder permissions.
7. Prepare database schema and privileges.
8. Run `python create_admin.py` to create the initial super admin account.
9. Optionally run `python setup_field_inspectors.py`.
10. Start the app with `python serve.py` or `waitress-serve --host=0.0.0.0 --port=5000 wsgi:app`.
11. Put reverse proxy in front of the application.
12. Verify `/healthz`, login, file upload, and petition workflow.

## 10. Cutover Validation Checklist

Before go-live, verify:
- Application starts without schema or permission errors
- Login works
- Sessions persist across requests
- Petition create/view/update works
- File uploads open correctly
- Excel import works if required
- User management screens load
- Dashboard APIs return data
- Help-center uploads/downloads work
- Password recovery flow works
- Backups are configured for DB and uploads

## 11. Operational Risks / Known Notes

Important notes for live deployment:
- `healthz` does not check database connectivity; consider enhancing it later.
- Initial startup may modify schema automatically; coordinate that with DBA policy.
- The repo contains both a base schema file and runtime schema evolution logic; they must stay aligned.
- Current `.env` indicates a schema-based deployment model inside database `postgres`, not necessarily a separate database named `vigilance_tracker`.

## 12. Recommended Server Specification

For small to medium internal usage:
- CPU: 2 to 4 vCPU
- RAM: 4 to 8 GB
- Disk: 50 GB+ depending on attachment volume
- PostgreSQL storage sized separately based on retention and uploaded files

Scale considerations:
- Main growth drivers are uploaded files, petition volume, and concurrent users.
- If attachments become large, move upload storage to a managed shared location.
