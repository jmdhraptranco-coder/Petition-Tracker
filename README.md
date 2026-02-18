# Petition Tracker

A web-based application to track vigilance petitions across APTRANSCO offices with complete workflow management.

## Features

- Multi-office petition entry - JMD Office, CVO (APSPDCL/APEPDCL/APCPDCL)
- Complete workflow tracking - From receipt to closure
- Role-based access control - Super Admin, Data Entry, JMD, PO, CVO, Field Inspectors
- Permission management - CVO to PO approval workflow
- Enquiry reports - Inspector submission, CVO comments, PO conclusions
- Timeline tracking - Full audit trail of every action
- Dashboard - Role-specific statistics and overview

## Hierarchy

```
Super Admin (controls all logins)
    -> Data Entry Operator (petition entry and assignment to CVO)
        -> JMD (Vigilance and Security)
            -> PO (Personal Officer Vigilance)
                -> CVO APSPDCL (Tirupathi)
                    -> Field Inspectors (CI/SI)
                -> CVO APEPDCL (Vizag)
                    -> Field Inspectors (CI/SI)
                -> CVO APCPDCL (Vijayawada)
                    -> Field Inspectors (CI/SI)
```

## Workflow

1. Petition received at JMD Office or directly at CVO office.
2. Data Entry forwards petition to the respective CVO.
3. CVO sets E-Receipt Number and can upload E-Receipt copy.
4. CVO assigns to Field Inspector (CI/SI) or requests PO permission.
5. PO approves/rejects permission and pushes back to CVO.
6. Inspector uploads enquiry report (and optional file attachment).
7. CVO adds comments and forwards to JMD.
8. JMD reviews and forwards to PO.
9. PO enters E-Office File No, gives final conclusion, and closes the petition.

## Setup Instructions

### 1. Prerequisites
- Python 3.10+
- PostgreSQL 13+
- pip

### 2. Install Dependencies
```bash
cd Petition-Tracker
pip install -r requirements.txt
```

### 3. Create Database
Open pgAdmin or psql and run:
```sql
CREATE DATABASE vigilance_tracker;
```

Then connect to the database and run the schema:
```bash
psql -U postgres -d vigilance_tracker -f database.sql
```

Or paste the contents of `database.sql` into pgAdmin Query Tool.

If your database is already created from an older schema, run:
```sql
ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'data_entry';
ALTER TABLE petitions ADD COLUMN IF NOT EXISTS ereceipt_no VARCHAR(100);
ALTER TABLE petitions ADD COLUMN IF NOT EXISTS ereceipt_file VARCHAR(255);
ALTER TABLE enquiry_reports ADD COLUMN IF NOT EXISTS report_file VARCHAR(255);
```

### 4. Configure Environment Variables
This project auto-loads values from a local `.env` file.

Create `.env` from template:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` (do not hardcode credentials in code):

```bash
# Required for production
APP_ENV=production
SECRET_KEY=replace-with-long-random-secret

# Option A: full URL provided by DBA
DATABASE_URL=postgresql://db_user:db_password@db_host:5432/vigilance_tracker

# Option B: individual DB settings
DB_HOST=db_host
DB_PORT=5432
DB_NAME=vigilance_tracker
DB_USER=db_user
DB_PASSWORD=db_password
DB_SSLMODE=require

# Optional runtime settings
PORT=5000
UPLOAD_BASE_DIR=/var/app/uploads
MAX_UPLOAD_SIZE_MB=10
```

### 5. Create Super Admin User
```bash
python create_admin.py
```

### 5A. Seed CVO + Field Inspectors (Optional)
```bash
python setup_field_inspectors.py
```

### 6. Run the Application (Development)
```bash
python app.py
```

Open: `http://localhost:5000`

### 7. Run the Application (Production)
Use a WSGI server instead of Flask debug server.

```bash
waitress-serve --host=0.0.0.0 --port=5000 wsgi:app
```

Or use the included production runner:

```bash
python serve.py
```

For government deployments, keep TLS at reverse proxy/load balancer and restrict inbound access by firewall.

### 8. Health Check
Use this endpoint for reverse proxy/load balancer health probes:

```bash
GET /healthz
```

## Quality Checks

Run strict local quality checks before deployment:

```bash
python -m py_compile app.py models.py config.py create_admin.py serve.py wsgi.py
python -m ruff check .
python -m pytest
```

Current enforced test rules:
- Warnings are treated as errors.
- Coverage is measured for `app.py` and `models.py`.
- Minimum total coverage required: `90%`.

If all pass, your syntax, lint safety rules, and stricter regression gates are green.

## Petition Fields
- S.No (auto-generated: VIG/JMD/2025/0001)
- E-Receipt No (by CVO)
- E-Office File No (by PO)
- Petitioner Name
- Contact Number
- Place
- Subject
- Type: Bribe, Harassment, Theft of Materials, Adverse News, Procedural Lapses, Other

## Tech Stack
- Backend: Python Flask
- Database: PostgreSQL
- Frontend: HTML, CSS, JavaScript
- Auth: Session-based with Werkzeug password hashing


