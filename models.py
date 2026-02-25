import psycopg2
import psycopg2.extras
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import json

config = Config()


def ensure_schema_updates():
    """Apply minimal runtime-safe schema updates required by newer workflow."""
    conn = psycopg2.connect(**config.get_psycopg2_kwargs())
    conn.autocommit = True
    try:
        cur = dict_cursor(conn)
        cur.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'cmd_apspdcl'")
        cur.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'cmd_apepdcl'")
        cur.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'cmd_apcpdcl'")
        cur.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'cgm_hr_transco'")
        cur.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'dsp'")
        cur.execute("ALTER TYPE petition_status ADD VALUE IF NOT EXISTS 'lodged'")
        cur.execute("ALTER TYPE cvo_office ADD VALUE IF NOT EXISTS 'headquarters'")
        cur.execute("""
            ALTER TABLE petitions
            ADD COLUMN IF NOT EXISTS enquiry_type VARCHAR(20) NOT NULL DEFAULT 'detailed'
        """)
        cur.execute("""
            ALTER TABLE petitions
            ADD COLUMN IF NOT EXISTS source_of_petition VARCHAR(20) NOT NULL DEFAULT 'public_individual'
        """)
        cur.execute("""
            ALTER TABLE petitions
            ADD COLUMN IF NOT EXISTS govt_institution_type VARCHAR(80)
        """)
        cur.execute("""
            ALTER TABLE enquiry_reports
            ADD COLUMN IF NOT EXISTS cmd_action_report_file VARCHAR(255)
        """)
        cur.execute("""
            ALTER TABLE enquiry_reports
            ADD COLUMN IF NOT EXISTS cvo_consolidated_report_file VARCHAR(255)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS form_field_configs (
                form_key VARCHAR(100) NOT NULL,
                field_key VARCHAR(100) NOT NULL,
                label VARCHAR(255) NOT NULL,
                field_type VARCHAR(30) NOT NULL,
                is_required BOOLEAN NOT NULL DEFAULT FALSE,
                options_json TEXT,
                updated_by INTEGER REFERENCES users(id),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (form_key, field_key)
            )
        """)
        cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS profile_photo VARCHAR(255)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_signup_requests (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255) NOT NULL,
                requested_role VARCHAR(50) NOT NULL,
                cvo_office VARCHAR(30),
                phone VARCHAR(30),
                email VARCHAR(255),
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                decision_notes TEXT,
                reviewed_by INTEGER REFERENCES users(id),
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_signup_requests_status_created
            ON user_signup_requests (status, created_at DESC)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_requests (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                username VARCHAR(100) NOT NULL,
                requested_password_hash VARCHAR(255) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                decision_notes TEXT,
                reviewed_by INTEGER REFERENCES users(id),
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_password_reset_requests_status_created
            ON password_reset_requests (status, created_at DESC)
        """)
    except Exception:
        raise
    finally:
        conn.close()

def get_db():
    """Get database connection"""
    conn = psycopg2.connect(**config.get_psycopg2_kwargs())
    conn.autocommit = False
    return conn

def dict_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ========================================
# USER OPERATIONS
# ========================================

def create_user(username, password, full_name, role, cvo_office=None, assigned_cvo_id=None, phone=None, email=None):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        password_hash = generate_password_hash(password)
        cur.execute("""
            INSERT INTO users (username, password_hash, full_name, role, cvo_office, assigned_cvo_id, phone, email)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (username, password_hash, full_name, role, cvo_office, assigned_cvo_id, phone, email))
        user_id = cur.fetchone()['id']
        conn.commit()
        return user_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def create_signup_request(username, password, full_name, requested_role, cvo_office=None, phone=None, email=None):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        password_hash = generate_password_hash(password)
        cur.execute("""
            INSERT INTO user_signup_requests
                (username, password_hash, full_name, requested_role, cvo_office, phone, email)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (username, password_hash, full_name, requested_role, cvo_office, phone, email))
        request_id = cur.fetchone()['id']
        conn.commit()
        return request_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_pending_signup_requests():
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT id, username, full_name, requested_role, cvo_office, phone, email, status, created_at
            FROM user_signup_requests
            WHERE status = 'pending'
            ORDER BY created_at ASC
        """)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def approve_signup_request(request_id, reviewer_id):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM user_signup_requests WHERE id = %s FOR UPDATE", (request_id,))
        req = cur.fetchone()
        if not req:
            raise ValueError('Signup request not found.')
        req = dict(req)
        if req.get('status') != 'pending':
            raise ValueError('Signup request is already processed.')

        cur.execute("""
            INSERT INTO users (username, password_hash, full_name, role, cvo_office, assigned_cvo_id, phone, email)
            VALUES (%s, %s, %s, %s, %s, NULL, %s, %s)
            RETURNING id
        """, (
            req.get('username'),
            req.get('password_hash'),
            req.get('full_name'),
            req.get('requested_role'),
            req.get('cvo_office'),
            req.get('phone'),
            req.get('email'),
        ))
        user_id = cur.fetchone()['id']
        cur.execute("""
            UPDATE user_signup_requests
            SET status = 'approved', reviewed_by = %s, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (reviewer_id, request_id))
        conn.commit()
        return user_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def reject_signup_request(request_id, reviewer_id, decision_notes=None):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT status FROM user_signup_requests WHERE id = %s", (request_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError('Signup request not found.')
        if row.get('status') != 'pending':
            raise ValueError('Signup request is already processed.')
        cur.execute("""
            UPDATE user_signup_requests
            SET status = 'rejected', decision_notes = %s, reviewed_by = %s, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, ((decision_notes or '').strip() or None, reviewer_id, request_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def authenticate_user(username, password):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM users WHERE username = %s AND is_active = TRUE", (username,))
        user = cur.fetchone()
        if user and check_password_hash(user['password_hash'], password):
            return dict(user)
        return None
    finally:
        conn.close()


def create_password_reset_request(username, new_password):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT id, username FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        if not user:
            raise ValueError('User not found.')
        password_hash = generate_password_hash(new_password)
        cur.execute("""
            INSERT INTO password_reset_requests (user_id, username, requested_password_hash)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (user['id'], user['username'], password_hash))
        request_id = cur.fetchone()['id']
        conn.commit()
        return request_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_pending_password_reset_requests():
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT pr.id, pr.user_id, pr.username, pr.status, pr.created_at,
                   u.full_name, u.role, u.is_active
            FROM password_reset_requests pr
            LEFT JOIN users u ON u.id = pr.user_id
            WHERE pr.status = 'pending'
            ORDER BY pr.created_at ASC
        """)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def approve_password_reset_request(request_id, reviewer_id):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM password_reset_requests WHERE id = %s FOR UPDATE", (request_id,))
        req = cur.fetchone()
        if not req:
            raise ValueError('Password reset request not found.')
        req = dict(req)
        if req.get('status') != 'pending':
            raise ValueError('Password reset request is already processed.')

        cur.execute("SELECT id FROM users WHERE id = %s", (req['user_id'],))
        user = cur.fetchone()
        if not user:
            raise ValueError('Target user no longer exists.')

        cur.execute("""
            UPDATE users
            SET password_hash = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (req['requested_password_hash'], req['user_id']))
        cur.execute("""
            UPDATE password_reset_requests
            SET status = 'approved', reviewed_by = %s, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (reviewer_id, request_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def reject_password_reset_request(request_id, reviewer_id, decision_notes=None):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT status FROM password_reset_requests WHERE id = %s", (request_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError('Password reset request not found.')
        if row.get('status') != 'pending':
            raise ValueError('Password reset request is already processed.')
        cur.execute("""
            UPDATE password_reset_requests
            SET status = 'rejected', decision_notes = %s, reviewed_by = %s, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, ((decision_notes or '').strip() or None, reviewer_id, request_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def get_user_by_username(username):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def get_all_users():
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT id, username, full_name, role, cvo_office, phone, email, profile_photo, is_active, created_at
            FROM users
            ORDER BY role, full_name
        """)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def get_users_by_role(role, cvo_office=None):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        if cvo_office:
            cur.execute("SELECT * FROM users WHERE role = %s AND cvo_office = %s AND is_active = TRUE", (role, cvo_office))
        else:
            cur.execute("SELECT * FROM users WHERE role = %s AND is_active = TRUE", (role,))
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def get_inspectors_by_cvo(cvo_user_id):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        # Fetch inspectors mapped to this exact CVO/DSP.
        # Fallback: include office-matched inspectors only when explicit mapping is missing.
        cur.execute("SELECT id, role, cvo_office FROM users WHERE id = %s", (cvo_user_id,))
        cvo = cur.fetchone()
        if not cvo:
            return []

        cur.execute("""
            SELECT DISTINCT i.*
            FROM users i
            WHERE i.role = 'inspector'
              AND i.is_active = TRUE
              AND (
                    i.assigned_cvo_id = %s
                    OR (i.assigned_cvo_id IS NULL AND i.cvo_office IS NOT NULL AND i.cvo_office = %s)
              )
            ORDER BY i.full_name
        """, (cvo_user_id, cvo['cvo_office']))
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def get_cvo_users():
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT * FROM users WHERE role IN ('cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp') AND is_active = TRUE")
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def toggle_user_status(user_id):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("UPDATE users SET is_active = NOT is_active, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (user_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def update_user(user_id, full_name, role, cvo_office=None, assigned_cvo_id=None, phone=None, email=None, password=None):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        if password:
            password_hash = generate_password_hash(password)
            cur.execute("""
                UPDATE users SET full_name=%s, role=%s, cvo_office=%s, assigned_cvo_id=%s, 
                phone=%s, email=%s, password_hash=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s
            """, (full_name, role, cvo_office, assigned_cvo_id, phone, email, password_hash, user_id))
        else:
            cur.execute("""
                UPDATE users SET full_name=%s, role=%s, cvo_office=%s, assigned_cvo_id=%s, 
                phone=%s, email=%s, updated_at=CURRENT_TIMESTAMP WHERE id=%s
            """, (full_name, role, cvo_office, assigned_cvo_id, phone, email, user_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def set_user_password(user_id, password):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        password_hash = generate_password_hash(password)
        cur.execute(
            "UPDATE users SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (password_hash, user_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_role_login_users():
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT id, username, full_name, role, is_active
            FROM users
            WHERE role::text IN (
                'super_admin',
                'data_entry',
                'po',
                'cmd_apspdcl',
                'cmd_apepdcl',
                'cmd_apcpdcl',
                'cgm_hr_transco',
                'dsp',
                'cvo_apspdcl',
                'cvo_apepdcl',
                'cvo_apcpdcl',
                'inspector'
            )
            ORDER BY role, full_name
        """)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def set_username(user_id, new_username):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute(
            "UPDATE users SET username = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (new_username, user_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def update_user_full_name(user_id, full_name):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute(
            "UPDATE users SET full_name = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (full_name, user_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def update_user_profile_info(user_id, full_name, phone=None, email=None):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute(
            """
            UPDATE users
            SET full_name = %s,
                phone = %s,
                email = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (full_name, phone, email, user_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def set_user_profile_photo(user_id, profile_photo):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute(
            """
            UPDATE users
            SET profile_photo = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (profile_photo, user_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_inspector_mappings():
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT i.id, i.username, i.full_name, i.is_active,
                   c.id AS mapped_cvo_id, c.full_name AS mapped_cvo_name, c.role AS mapped_cvo_role
            FROM users i
            LEFT JOIN users c ON i.assigned_cvo_id = c.id
            WHERE i.role = 'inspector'
            ORDER BY i.full_name
        """)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def map_inspector_to_cvo(inspector_id, cvo_id):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("""
            UPDATE users
            SET assigned_cvo_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND role = 'inspector'
        """, (cvo_id, inspector_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_form_field_configs():
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT form_key, field_key, label, field_type, is_required, options_json
            FROM form_field_configs
        """)
        result = {}
        for row in cur.fetchall():
            data = dict(row)
            options = []
            raw_options = data.get('options_json')
            if raw_options:
                try:
                    options = json.loads(raw_options)
                except Exception:
                    options = []
            result[f"{data['form_key']}.{data['field_key']}"] = {
                'label': data.get('label'),
                'type': data.get('field_type'),
                'required': bool(data.get('is_required')),
                'options': options
            }
        return result
    finally:
        conn.close()


def upsert_form_field_config(form_key, field_key, label, field_type, is_required, options, updated_by):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        options_json = json.dumps(options or [])
        cur.execute("""
            INSERT INTO form_field_configs
                (form_key, field_key, label, field_type, is_required, options_json, updated_by, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (form_key, field_key)
            DO UPDATE SET
                label = EXCLUDED.label,
                field_type = EXCLUDED.field_type,
                is_required = EXCLUDED.is_required,
                options_json = EXCLUDED.options_json,
                updated_by = EXCLUDED.updated_by,
                updated_at = CURRENT_TIMESTAMP
        """, (form_key, field_key, label, field_type, is_required, options_json, updated_by))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ========================================
# PETITION OPERATIONS
# ========================================

def generate_sno(received_at):
    """Generate serial number like VIG/PO/2025/0001"""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT nextval('petition_sno_seq')")
        seq = cur.fetchone()['nextval']
        
        office_codes = {
            'jmd_office': 'PO',
            'cvo_apspdcl_tirupathi': 'SPDCL',
            'cvo_apepdcl_vizag': 'EPDCL',
            'cvo_apcpdcl_vijayawada': 'CPDCL'
        }
        office = office_codes.get(received_at, 'VIG')
        year = datetime.now().year
        sno = f"VIG/{office}/{year}/{seq:04d}"
        conn.commit()
        return sno
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def create_petition(data, created_by):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        sno = generate_sno(data['received_at'])
        
        cur.execute("""
            INSERT INTO petitions (sno, efile_no, petitioner_name, contact, place, subject, 
                petition_type, source_of_petition, received_at, target_cvo, requires_permission, received_date,
                govt_institution_type, permission_status, enquiry_type, created_by, current_handler_id, status, remarks, ereceipt_no, ereceipt_file)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'received', %s, %s, %s)
            RETURNING id, sno
        """, (
            sno, data.get('efile_no'), data['petitioner_name'], data.get('contact'),
            data.get('place'), data['subject'], data['petition_type'], data.get('source_of_petition', 'public_individual'),
            data['received_at'], data.get('target_cvo'), 
            data.get('requires_permission', False),
            data.get('received_date', date.today()),
            data.get('govt_institution_type'),
            data.get('permission_status', 'pending'),
            data.get('enquiry_type', 'detailed'),
            created_by, created_by, data.get('remarks'),
            data.get('ereceipt_no'),
            data.get('ereceipt_file')
        ))
        result = cur.fetchone()
        
        # Log the creation
        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, from_role, action, status_after, comments)
            VALUES (%s, %s, (SELECT role FROM users WHERE id = %s), 'Petition Created', 'received', %s)
        """, (result['id'], created_by, created_by, f"Petition {sno} created"))
        
        conn.commit()
        return dict(result)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_petition_by_id(petition_id):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT p.*, 
                u1.full_name as created_by_name,
                u2.full_name as inspector_name,
                u3.full_name as handler_name
            FROM petitions p
            LEFT JOIN users u1 ON p.created_by = u1.id
            LEFT JOIN users u2 ON p.assigned_inspector_id = u2.id
            LEFT JOIN users u3 ON p.current_handler_id = u3.id
            WHERE p.id = %s
        """, (petition_id,))
        result = cur.fetchone()
        return dict(result) if result else None
    finally:
        conn.close()

def get_petitions_for_user(user_id, user_role, cvo_office=None, status_filter=None, enquiry_mode='all'):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        base_query = """
            SELECT p.*, 
                u1.full_name as created_by_name,
                u2.full_name as inspector_name,
                u3.full_name as handler_name
            FROM petitions p
            LEFT JOIN users u1 ON p.created_by = u1.id
            LEFT JOIN users u2 ON p.assigned_inspector_id = u2.id
            LEFT JOIN users u3 ON p.current_handler_id = u3.id
        """
        conditions = []
        params = []
        
        if user_role == 'super_admin':
            pass  # See all
        elif user_role == 'data_entry':
            pass  # Data entry sees all petitions for assignment tracking
        elif user_role == 'po':
            conditions.append("(p.status IN ('forwarded_to_po', 'forwarded_to_jmd', 'sent_for_permission', 'action_taken', 'lodged') OR p.current_handler_id = %s OR p.requires_permission = FALSE)")
            params.append(user_id)
        elif user_role in ('cmd_apspdcl', 'cmd_apepdcl', 'cmd_apcpdcl', 'cgm_hr_transco'):
            cmd_office_map = {'cmd_apspdcl': 'apspdcl', 'cmd_apepdcl': 'apepdcl', 'cmd_apcpdcl': 'apcpdcl', 'cgm_hr_transco': 'headquarters'}
            conditions.append("p.target_cvo = %s AND p.status IN ('action_instructed', 'action_taken')")
            params.append(cmd_office_map[user_role])
        elif user_role in ('cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp'):
            office_map = {'cvo_apspdcl': 'apspdcl', 'cvo_apepdcl': 'apepdcl', 'cvo_apcpdcl': 'apcpdcl', 'dsp': 'headquarters'}
            conditions.append("p.target_cvo = %s")
            params.append(office_map[user_role])
        elif user_role == 'inspector':
            conditions.append("p.assigned_inspector_id = %s")
            params.append(user_id)
        
        if enquiry_mode == 'direct':
            conditions.append("p.requires_permission = FALSE")
        elif enquiry_mode == 'permission':
            conditions.append("p.requires_permission = TRUE")

        if status_filter and status_filter != 'all':
            conditions.append("p.status = %s")
            params.append(status_filter)
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        
        base_query += " ORDER BY p.created_at DESC"
        
        cur.execute(base_query, params)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def get_all_petitions(status_filter=None, enquiry_mode='all'):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        query = """
            SELECT p.*, 
                u1.full_name as created_by_name,
                u2.full_name as inspector_name,
                u3.full_name as handler_name
            FROM petitions p
            LEFT JOIN users u1 ON p.created_by = u1.id
            LEFT JOIN users u2 ON p.assigned_inspector_id = u2.id
            LEFT JOIN users u3 ON p.current_handler_id = u3.id
        """
        conditions = []
        params = []
        if enquiry_mode == 'direct':
            conditions.append("p.requires_permission = FALSE")
        elif enquiry_mode == 'permission':
            conditions.append("p.requires_permission = TRUE")

        if status_filter and status_filter != 'all':
            conditions.append("p.status = %s")
            params.append(status_filter)

        if conditions:
            query += " WHERE " + " AND ".join(conditions) + " ORDER BY p.created_at DESC"
            cur.execute(query, params)
        else:
            query += " ORDER BY p.created_at DESC"
            cur.execute(query)
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

# ========================================
# WORKFLOW OPERATIONS
# ========================================

def forward_petition_to_cvo(petition_id, from_user_id, target_cvo, comments=None):
    """Forward petition to respective CVO from current handler"""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT role FROM users WHERE id = %s", (from_user_id,))
        from_user = cur.fetchone()
        from_role = from_user['role'] if from_user else None

        cur.execute("SELECT status FROM petitions WHERE id = %s", (petition_id,))
        petition = cur.fetchone()
        status_before = petition['status'] if petition else None

        # Find the CVO user for this office
        role_map = {'apspdcl': 'cvo_apspdcl', 'apepdcl': 'cvo_apepdcl', 'apcpdcl': 'cvo_apcpdcl', 'headquarters': 'dsp'}
        cvo_role = role_map.get(target_cvo)
        
        cur.execute("SELECT id FROM users WHERE role = %s AND is_active = TRUE LIMIT 1", (cvo_role,))
        cvo_user = cur.fetchone()
        cvo_id = cvo_user['id'] if cvo_user else None
        
        cur.execute("""
            UPDATE petitions SET status = 'forwarded_to_cvo', target_cvo = %s,
                current_handler_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (target_cvo, cvo_id, petition_id))
        
        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, to_user_id, from_role, to_role, 
                action, comments, status_before, status_after)
            VALUES (%s, %s, %s, %s, %s, 'Forwarded to CVO', %s, %s, 'forwarded_to_cvo')
        """, (petition_id, from_user_id, cvo_id, from_role, cvo_role, comments, status_before))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def send_for_permission(petition_id, from_user_id, comments=None):
    """Current handler sends petition to PO for permission"""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT role FROM users WHERE id = %s", (from_user_id,))
        from_user = cur.fetchone()
        from_role = from_user['role'] if from_user else None

        cur.execute("SELECT status FROM petitions WHERE id = %s", (petition_id,))
        petition = cur.fetchone()
        status_before = petition['status'] if petition else None

        cur.execute("SELECT id FROM users WHERE role = 'po' AND is_active = TRUE LIMIT 1")
        po_user = cur.fetchone()
        po_id = po_user['id'] if po_user else None
        
        cur.execute("""
            UPDATE petitions SET status = 'sent_for_permission', requires_permission = TRUE,
                permission_status = 'pending', current_handler_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (po_id, petition_id))
        
        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, to_user_id, from_role, to_role,
                action, comments, status_before, status_after)
            VALUES (%s, %s, %s, %s, 'po', 'Sent for Permission to PO', %s, %s, 'sent_for_permission')
        """, (petition_id, from_user_id, po_id, from_role, comments, status_before))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def cvo_send_receipt_to_po(petition_id, cvo_user_id, comments=None):
    """CVO sends petition with receipt to PO for mandatory permission route."""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT id FROM users WHERE role = 'po' AND is_active = TRUE LIMIT 1")
        po_user = cur.fetchone()
        po_id = po_user['id'] if po_user else None

        cur.execute("SELECT status FROM petitions WHERE id = %s", (petition_id,))
        petition = cur.fetchone()
        status_before = petition['status'] if petition else None

        cur.execute("""
            UPDATE petitions
            SET status = 'sent_for_permission',
                requires_permission = TRUE,
                permission_status = 'pending',
                current_handler_id = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (po_id, petition_id))

        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, to_user_id, from_role, to_role,
                action, comments, status_before, status_after)
            VALUES (%s, %s, %s, (SELECT role FROM users WHERE id = %s), 'po',
                'Receipt Sent to PO for Permission', %s, %s, 'sent_for_permission')
        """, (petition_id, cvo_user_id, po_id, cvo_user_id, comments, status_before))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def approve_permission(petition_id, from_user_id, target_cvo, efile_no=None, comments=None, enquiry_type=None):
    """PO approves permission and sends to CVO"""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        role_map = {'apspdcl': 'cvo_apspdcl', 'apepdcl': 'cvo_apepdcl', 'apcpdcl': 'cvo_apcpdcl', 'headquarters': 'dsp'}
        cvo_role = role_map.get(target_cvo)
        
        cur.execute("SELECT id FROM users WHERE role = %s AND is_active = TRUE LIMIT 1", (cvo_role,))
        cvo_user = cur.fetchone()
        cvo_id = cvo_user['id'] if cvo_user else None
        
        cur.execute("""
            UPDATE petitions SET status = 'permission_approved', permission_status = 'approved',
                target_cvo = %s,
                enquiry_type = CASE
                    WHEN %s IN ('detailed', 'preliminary') THEN %s
                    ELSE enquiry_type
                END,
                efile_no = CASE
                    WHEN COALESCE(BTRIM(efile_no), '') = '' THEN %s
                    ELSE efile_no
                END,
                current_handler_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (target_cvo, enquiry_type, enquiry_type, efile_no, cvo_id, petition_id))
        
        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, to_user_id, from_role, to_role,
                action, comments, status_before, status_after)
            VALUES (%s, %s, %s, 'po', %s, 'Permission Approved - Sent to CVO', %s, 'sent_for_permission', 'permission_approved')
        """, (petition_id, from_user_id, cvo_id, cvo_role, comments))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def reject_permission(petition_id, from_user_id, comments=None):
    """PO rejects permission"""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("""
            UPDATE petitions SET status = 'permission_rejected', permission_status = 'rejected',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (petition_id,))
        
        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, from_role,
                action, comments, status_before, status_after)
            VALUES (%s, %s, 'po', 'Permission Rejected', %s, 'sent_for_permission', 'permission_rejected')
        """, (petition_id, from_user_id, comments))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def assign_to_inspector(petition_id, from_user_id, inspector_id, comments=None, enquiry_type=None):
    """CVO assigns petition to field inspector"""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT status, requires_permission FROM petitions WHERE id = %s", (petition_id,))
        petition = cur.fetchone()
        status_before = petition['status'] if petition else None
        requires_permission = petition['requires_permission'] if petition else True

        cur.execute("""
            UPDATE petitions SET status = 'assigned_to_inspector',
                enquiry_type = CASE
                    WHEN %s IN ('detailed', 'preliminary') THEN %s
                    ELSE enquiry_type
                END,
                assigned_inspector_id = %s,
                current_handler_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (enquiry_type, enquiry_type, inspector_id, inspector_id, petition_id))
        
        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, to_user_id, 
                from_role, to_role, action, comments, status_before, status_after)
            VALUES (%s, %s, %s, (SELECT role FROM users WHERE id = %s), 'inspector', 
                'Assigned to Inspector', %s, 
                %s, 'assigned_to_inspector')
        """, (petition_id, from_user_id, inspector_id, from_user_id, comments, status_before))

        if not requires_permission:
            cur.execute("SELECT id FROM users WHERE role = 'po' AND is_active = TRUE LIMIT 1")
            po_user = cur.fetchone()
            po_id = po_user['id'] if po_user else None
            cur.execute("""
                INSERT INTO petition_tracking (petition_id, from_user_id, to_user_id, from_role, to_role, action, comments, status_before, status_after)
                VALUES (%s, %s, %s, (SELECT role FROM users WHERE id = %s), 'po',
                    'Direct Enquiry Acknowledgement Sent to PO (for E-Office File No)',
                    %s, %s, 'assigned_to_inspector')
            """, (petition_id, from_user_id, po_id, from_user_id, comments, status_before))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def set_ereceipt(petition_id, user_id, ereceipt_no, ereceipt_file=None):
    """CVO updates E-Receipt number and optional uploaded receipt file."""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT ereceipt_no, ereceipt_file, status FROM petitions WHERE id = %s", (petition_id,))
        petition = cur.fetchone()
        previous_receipt = petition['ereceipt_no'] if petition else None
        status_before = petition['status'] if petition else None

        cur.execute("""
            UPDATE petitions
            SET ereceipt_no = %s,
                ereceipt_file = COALESCE(%s, ereceipt_file),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (ereceipt_no, ereceipt_file, petition_id))

        file_note = " with file upload" if ereceipt_file else ""
        comment = f"E-Receipt No updated from '{previous_receipt or '-'}' to '{ereceipt_no}'{file_note}"
        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, from_role, action, comments, status_before, status_after)
            VALUES (%s, %s, (SELECT role FROM users WHERE id = %s), 'E-Receipt Updated', %s, %s, %s)
        """, (petition_id, user_id, user_id, comment, status_before, status_before))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def submit_enquiry_report(petition_id, inspector_id, report_text, findings, recommendation, report_file=None):
    """Inspector submits enquiry report"""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        
        # Get the CVO this inspector reports to
        cur.execute("SELECT assigned_cvo_id FROM users WHERE id = %s", (inspector_id,))
        inspector = cur.fetchone()
        cvo_id = inspector['assigned_cvo_id'] if inspector else None
        
        cur.execute("""
            INSERT INTO enquiry_reports (petition_id, submitted_by, report_text, findings, recommendation, report_file)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (petition_id, inspector_id, report_text, findings, recommendation, report_file))
        
        cur.execute("""
            UPDATE petitions SET status = 'enquiry_report_submitted', 
                current_handler_id = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (cvo_id, petition_id))
        
        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, to_user_id, 
                from_role, to_role, action, comments, status_before, status_after)
            VALUES (%s, %s, %s, 'inspector', (SELECT role FROM users WHERE id = %s), 
                'Enquiry Report Submitted', %s, 
                'assigned_to_inspector', 'enquiry_report_submitted')
        """, (petition_id, inspector_id, cvo_id, cvo_id, 'Report uploaded for CVO review' if report_file else 'Report submitted for CVO review'))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def cvo_add_comments(petition_id, cvo_user_id, cvo_comments):
    """CVO adds comments and forwards to PO"""
    conn = get_db()
    try:
        cur = dict_cursor(conn)

        # Update latest enquiry report row for this petition.
        cur.execute("""
            UPDATE enquiry_reports SET cvo_comments = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT id FROM enquiry_reports WHERE petition_id = %s ORDER BY submitted_at DESC LIMIT 1)
        """, (cvo_comments, petition_id))
        
        cur.execute("SELECT id FROM users WHERE role = 'po' AND is_active = TRUE LIMIT 1")
        po_user = cur.fetchone()
        po_id = po_user['id'] if po_user else None
        
        cur.execute("""
            UPDATE petitions SET status = 'forwarded_to_po', current_handler_id = %s, 
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (po_id, petition_id))
        
        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, to_user_id,
                from_role, to_role, action, comments, status_before, status_after)
            VALUES (%s, %s, %s, (SELECT role FROM users WHERE id = %s), 'po',
                'CVO Comments Added - Forwarded to PO', %s,
                'enquiry_report_submitted', 'forwarded_to_po')
        """, (petition_id, cvo_user_id, po_id, cvo_user_id, cvo_comments))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def cvo_request_detailed_enquiry(petition_id, cvo_user_id, cvo_comments=None):
    """After preliminary report, CVO requests PO permission to continue as detailed enquiry."""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT status FROM petitions WHERE id = %s", (petition_id,))
        petition = cur.fetchone()
        status_before = petition['status'] if petition else None

        if cvo_comments:
            cur.execute("""
                UPDATE enquiry_reports
                SET cvo_comments = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = (SELECT id FROM enquiry_reports WHERE petition_id = %s ORDER BY submitted_at DESC LIMIT 1)
            """, (cvo_comments, petition_id))

        cur.execute("SELECT id FROM users WHERE role = 'po' AND is_active = TRUE LIMIT 1")
        po_user = cur.fetchone()
        po_id = po_user['id'] if po_user else None

        cur.execute("""
            UPDATE petitions
            SET enquiry_type = 'detailed',
                requires_permission = TRUE,
                permission_status = 'pending',
                status = 'sent_for_permission',
                current_handler_id = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (po_id, petition_id))

        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, to_user_id, from_role, to_role,
                action, comments, status_before, status_after)
            VALUES (%s, %s, %s, (SELECT role FROM users WHERE id = %s), 'po',
                'Preliminary Enquiry Completed - Requested PO Permission for Detailed Enquiry',
                %s, %s, 'sent_for_permission')
        """, (petition_id, cvo_user_id, po_id, cvo_user_id, cvo_comments, status_before))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def cvo_upload_consolidated_report(petition_id, cvo_user_id, consolidated_report_file):
    """CVO/DSP uploads consolidated report after inspector report submission."""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT status FROM petitions WHERE id = %s", (petition_id,))
        petition = cur.fetchone()
        status_before = petition['status'] if petition else None

        cur.execute("""
            UPDATE enquiry_reports
            SET cvo_consolidated_report_file = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT id FROM enquiry_reports WHERE petition_id = %s ORDER BY submitted_at DESC LIMIT 1)
        """, (consolidated_report_file, petition_id))

        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, from_role, action, comments, status_before, status_after)
            VALUES (
                %s, %s, (SELECT role FROM users WHERE id = %s),
                'CVO/DSP Consolidated Report Uploaded',
                %s, %s, %s
            )
        """, (petition_id, cvo_user_id, cvo_user_id, consolidated_report_file, status_before, status_before))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def po_give_conclusion(petition_id, po_user_id, efile_no, final_conclusion, instructions=None, conclusion_file=None):
    """PO gives final conclusion and closes petition."""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        
        cur.execute("""
            UPDATE enquiry_reports
            SET po_conclusion = %s,
                po_instructions = %s,
                conclusion_file = COALESCE(%s, conclusion_file),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT id FROM enquiry_reports WHERE petition_id = %s ORDER BY submitted_at DESC LIMIT 1)
        """, (final_conclusion, instructions, conclusion_file, petition_id))
        
        cur.execute("""
            UPDATE petitions SET
                efile_no = CASE
                    WHEN COALESCE(BTRIM(efile_no), '') = '' THEN %s
                    ELSE efile_no
                END,
                status = 'closed', current_handler_id = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (efile_no, po_user_id, petition_id))
        
        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, from_role,
                action, comments, status_before, status_after)
            VALUES (%s, %s, 'po', 'Final Conclusion Given - Petition Closed', %s,
                'forwarded_to_po', 'closed')
        """, (petition_id, po_user_id, final_conclusion))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def po_send_to_cmd(petition_id, po_user_id, instructions=None, efile_no=None):
    """PO forwards case to concerned CMD for action based on petition target CVO."""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT target_cvo, status FROM petitions WHERE id = %s", (petition_id,))
        petition = cur.fetchone()
        if not petition:
            raise Exception("Petition not found.")

        cmd_role_map = {'apspdcl': 'cmd_apspdcl', 'apepdcl': 'cmd_apepdcl', 'apcpdcl': 'cmd_apcpdcl', 'headquarters': 'cgm_hr_transco'}
        cmd_role = cmd_role_map.get(petition['target_cvo'])
        if not cmd_role:
            raise Exception("No CMD role configured for this jurisdiction.")

        cur.execute("SELECT id FROM users WHERE role = %s AND is_active = TRUE LIMIT 1", (cmd_role,))
        cmd_user = cur.fetchone()
        cmd_id = cmd_user['id'] if cmd_user else None
        if not cmd_id:
            raise Exception(f"No active user found for role {cmd_role}.")

        status_before = petition['status']
        cur.execute("""
            UPDATE petitions
            SET status = 'action_instructed',
                efile_no = CASE
                    WHEN COALESCE(BTRIM(efile_no), '') = '' THEN %s
                    ELSE efile_no
                END,
                current_handler_id = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (efile_no, cmd_id, petition_id))

        cur.execute("""
            UPDATE enquiry_reports
            SET po_instructions = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT id FROM enquiry_reports WHERE petition_id = %s ORDER BY submitted_at DESC LIMIT 1)
        """, (instructions, petition_id))

        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, to_user_id, from_role, to_role, action, comments, status_before, status_after)
            VALUES (%s, %s, %s, 'po', %s, 'Forwarded to CMD for Action', %s, %s, 'action_instructed')
        """, (petition_id, po_user_id, cmd_id, cmd_role, instructions, status_before))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def cmd_submit_action_report(petition_id, cmd_user_id, action_taken, action_report_file=None):
    """CMD marks action taken, uploads report copy, and sends it to PO for closure."""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT status FROM petitions WHERE id = %s", (petition_id,))
        petition = cur.fetchone()
        if not petition:
            raise Exception("Petition not found.")

        cur.execute("SELECT id FROM users WHERE role = 'po' AND is_active = TRUE LIMIT 1")
        po_user = cur.fetchone()
        po_id = po_user['id'] if po_user else None
        if not po_id:
            raise Exception("No active PO user found.")

        cur.execute("""
            UPDATE enquiry_reports
            SET action_taken = %s,
                cmd_action_report_file = COALESCE(%s, cmd_action_report_file),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT id FROM enquiry_reports WHERE petition_id = %s ORDER BY submitted_at DESC LIMIT 1)
        """, (action_taken, action_report_file, petition_id))

        cur.execute("""
            UPDATE petitions
            SET status = 'action_taken',
                current_handler_id = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (po_id, petition_id))

        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, to_user_id, from_role, to_role, action, comments, status_before, status_after)
            VALUES (
                %s, %s, %s, (SELECT role FROM users WHERE id = %s), 'po',
                'Action Taken - Copy Sent to PO for Closure', %s, %s, 'action_taken'
            )
        """, (petition_id, cmd_user_id, po_id, cmd_user_id, action_taken, petition['status']))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def po_lodge_petition(petition_id, po_user_id, lodge_remarks=None, efile_no=None):
    """PO lodges and closes petition, either directly or after CMD action report."""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT status FROM petitions WHERE id = %s", (petition_id,))
        petition = cur.fetchone()
        if not petition:
            raise Exception("Petition not found.")
        status_before = petition['status']

        cur.execute("""
            UPDATE petitions
            SET status = 'lodged',
                efile_no = CASE
                    WHEN COALESCE(BTRIM(efile_no), '') = '' THEN %s
                    ELSE efile_no
                END,
                current_handler_id = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (efile_no, po_user_id, petition_id))

        cur.execute("""
            UPDATE enquiry_reports
            SET po_conclusion = COALESCE(%s, po_conclusion),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT id FROM enquiry_reports WHERE petition_id = %s ORDER BY submitted_at DESC LIMIT 1)
        """, (lodge_remarks, petition_id))

        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, from_role, action, comments, status_before, status_after)
            VALUES (%s, %s, 'po', 'Lodged by PO', %s, %s, 'lodged')
        """, (petition_id, po_user_id, lodge_remarks, status_before))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def po_update_efile_number(petition_id, po_user_id, efile_no, remarks=None):
    """PO updates E-Office File No for direct enquiries in parallel."""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT status, efile_no FROM petitions WHERE id = %s", (petition_id,))
        petition = cur.fetchone()
        if not petition:
            raise Exception("Petition not found.")
        status_before = petition['status']
        old_efile = petition.get('efile_no')

        cur.execute("""
            UPDATE petitions
            SET efile_no = CASE
                    WHEN COALESCE(BTRIM(efile_no), '') = '' THEN %s
                    ELSE efile_no
                END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (efile_no, petition_id))
        if cur.rowcount == 0:
            conn.rollback()
            return False
        cur.execute("SELECT efile_no FROM petitions WHERE id = %s", (petition_id,))
        latest = cur.fetchone()
        latest_efile = (latest['efile_no'] if latest else None) or ''
        if old_efile and latest_efile == old_efile:
            conn.rollback()
            return False

        comment = remarks or f"E-Office File No updated from '{old_efile or '-'}' to '{efile_no}'"
        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, from_role, action, comments, status_before, status_after)
            VALUES (%s, %s, 'po', 'PO Updated E-Office File No', %s, %s, %s)
        """, (petition_id, po_user_id, comment, status_before, status_before))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def po_direct_lodge_no_enquiry(petition_id, po_user_id, lodge_remarks=None, efile_no=None):
    """PO directly lodges petition when enquiry/action are not required."""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT status FROM petitions WHERE id = %s", (petition_id,))
        petition = cur.fetchone()
        if not petition:
            raise Exception("Petition not found.")
        status_before = petition['status']

        cur.execute("""
            UPDATE petitions
            SET status = 'lodged',
                efile_no = CASE
                    WHEN COALESCE(BTRIM(efile_no), '') = '' THEN %s
                    ELSE efile_no
                END,
                current_handler_id = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (efile_no, po_user_id, petition_id))

        cur.execute("""
            UPDATE enquiry_reports
            SET po_conclusion = COALESCE(%s, po_conclusion),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT id FROM enquiry_reports WHERE petition_id = %s ORDER BY submitted_at DESC LIMIT 1)
        """, (lodge_remarks, petition_id))

        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, from_role, action, comments, status_before, status_after)
            VALUES (%s, %s, 'po', 'Direct Lodged by PO (No Enquiry/No Action Required)', %s, %s, 'lodged')
        """, (petition_id, po_user_id, lodge_remarks, status_before))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def cvo_take_action(petition_id, cvo_user_id, action_taken):
    """CVO takes necessary action and closes petition"""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        
        cur.execute("""
            UPDATE enquiry_reports SET action_taken = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT id FROM enquiry_reports WHERE petition_id = %s ORDER BY submitted_at DESC LIMIT 1)
        """, (action_taken, petition_id))
        
        cur.execute("""
            UPDATE petitions SET status = 'action_taken', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (petition_id,))
        
        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, from_role,
                action, comments, status_before, status_after)
            VALUES (%s, %s, (SELECT role FROM users WHERE id = %s), 
                'Action Taken', %s, 'action_instructed', 'action_taken')
        """, (petition_id, cvo_user_id, cvo_user_id, action_taken))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def close_petition(petition_id, user_id, comments=None):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT status FROM petitions WHERE id = %s", (petition_id,))
        petition = cur.fetchone()
        status_before = petition['status'] if petition else None

        cur.execute("UPDATE petitions SET status = 'closed', updated_at = CURRENT_TIMESTAMP WHERE id = %s", (petition_id,))
        
        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, from_role,
                action, comments, status_before, status_after)
            VALUES (%s, %s, (SELECT role FROM users WHERE id = %s), 
                'Petition Closed', %s, %s, 'closed')
        """, (petition_id, user_id, user_id, comments, status_before))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def po_update_efile_no(petition_id, user_id, efile_no):
    """PO sets e-office number once without changing petition flow."""
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("SELECT status, current_handler_id FROM petitions WHERE id = %s", (petition_id,))
        petition = cur.fetchone()
        status_before = petition['status'] if petition else None
        to_user_id = petition['current_handler_id'] if petition else None

        cur.execute("""
            UPDATE petitions
            SET efile_no = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND COALESCE(BTRIM(efile_no), '') = ''
        """, (efile_no, petition_id))

        if cur.rowcount == 0:
            conn.rollback()
            return False

        cur.execute("""
            INSERT INTO petition_tracking (petition_id, from_user_id, to_user_id, from_role, to_role,
                action, comments, status_before, status_after)
            VALUES (%s, %s, %s, 'po', (SELECT role FROM users WHERE id = %s),
                'E-Office File Number Updated', %s, %s, %s)
        """, (
            petition_id, user_id, to_user_id, to_user_id,
            f'E-Office File No updated to: {efile_no}', status_before, status_before
        ))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ========================================
# TRACKING & REPORTS
# ========================================

def get_petition_tracking(petition_id):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT pt.*, u1.full_name as from_name, u2.full_name as to_name
            FROM petition_tracking pt
            LEFT JOIN users u1 ON pt.from_user_id = u1.id
            LEFT JOIN users u2 ON pt.to_user_id = u2.id
            WHERE pt.petition_id = %s
            ORDER BY pt.created_at ASC
        """, (petition_id,))
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def get_enquiry_report(petition_id):
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT er.*, u.full_name as submitted_by_name
            FROM enquiry_reports er
            LEFT JOIN users u ON er.submitted_by = u.id
            WHERE er.petition_id = %s
            ORDER BY er.submitted_at DESC LIMIT 1
        """, (petition_id,))
        result = cur.fetchone()
        return dict(result) if result else None
    finally:
        conn.close()

def get_dashboard_stats(user_role, user_id=None, cvo_office=None):
    visible_petitions = get_petitions_for_user(user_id, user_role, cvo_office, status_filter=None)
    stats = {}
    stats['total_visible'] = len(visible_petitions)
    stats.update(_get_workflow_stage_stats(visible_petitions))
    stats.update(_get_sla_stats_for_petitions(visible_petitions))
    stats['kpi_cards'] = _build_role_kpi_cards(user_role, visible_petitions, user_id)
    return stats


def _count_statuses(petitions):
    counts = {}
    for p in petitions:
        s = p.get('status')
        counts[s] = counts.get(s, 0) + 1
    return counts


def _count_multi(counts, statuses):
    return sum(counts.get(s, 0) for s in statuses)


def _get_po_permission_given_count(po_user_id):
    if not po_user_id:
        return 0
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT COUNT(DISTINCT petition_id) AS c
            FROM petition_tracking
            WHERE from_user_id = %s
              AND action = 'Permission Approved - Sent to CVO'
        """, (po_user_id,))
        row = cur.fetchone()
        return row['c'] if row else 0
    finally:
        conn.close()


def _build_role_kpi_cards(user_role, petitions, user_id=None):
    counts = _count_statuses(petitions)
    is_cvo_like = user_role in ('cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp')

    if user_role in ('super_admin',):
        return [
            {'label': 'Received', 'value': counts.get('received', 0), 'metric': 'status:received', 'style': 'stat-primary'},
            {'label': 'Forwarded to CVO/DSP', 'value': counts.get('forwarded_to_cvo', 0), 'metric': 'status:forwarded_to_cvo', 'style': 'stat-info'},
            {'label': 'Sent for Permission', 'value': counts.get('sent_for_permission', 0), 'metric': 'status:sent_for_permission', 'style': 'stat-warning'},
            {'label': 'Enquiry In Process', 'value': _count_multi(counts, ['assigned_to_inspector', 'enquiry_in_progress']), 'metric': 'multi:assigned_to_inspector,enquiry_in_progress', 'style': 'stat-warning'},
            {'label': 'Reports at PO', 'value': _count_multi(counts, ['forwarded_to_po', 'forwarded_to_jmd']), 'metric': 'multi:forwarded_to_po,forwarded_to_jmd', 'style': 'stat-info'},
            {'label': 'Action Initiated', 'value': counts.get('action_instructed', 0), 'metric': 'status:action_instructed', 'style': 'stat-success'},
            {'label': 'Action Taken', 'value': counts.get('action_taken', 0), 'metric': 'status:action_taken', 'style': 'stat-success'},
            {'label': 'Lodged', 'value': counts.get('lodged', 0), 'metric': 'status:lodged', 'style': 'stat-amber'},
            {'label': 'Closed', 'value': counts.get('closed', 0), 'metric': 'status:closed', 'style': 'stat-violet'},
        ]
    if user_role == 'po':
        return [
            {'label': 'Permission Pending', 'value': counts.get('sent_for_permission', 0), 'metric': 'status:sent_for_permission', 'style': 'stat-warning'},
            {'label': 'Permission Given', 'value': _get_po_permission_given_count(user_id), 'metric': 'po_permission_given', 'style': 'stat-success'},
            {'label': 'Reports Received', 'value': _count_multi(counts, ['forwarded_to_po', 'forwarded_to_jmd']), 'metric': 'multi:forwarded_to_po,forwarded_to_jmd', 'style': 'stat-info'},
            {'label': 'Action Initiated', 'value': counts.get('action_instructed', 0), 'metric': 'status:action_instructed', 'style': 'stat-primary'},
            {'label': 'Action Taken', 'value': counts.get('action_taken', 0), 'metric': 'status:action_taken', 'style': 'stat-success'},
            {'label': 'Lodged', 'value': counts.get('lodged', 0), 'metric': 'status:lodged', 'style': 'stat-amber'},
        ]
    if is_cvo_like:
        return [
            {'label': 'Received', 'value': counts.get('forwarded_to_cvo', 0), 'metric': 'status:forwarded_to_cvo', 'style': 'stat-primary'},
            {'label': 'Permission Approved', 'value': counts.get('permission_approved', 0), 'metric': 'status:permission_approved', 'style': 'stat-success'},
            {'label': 'Assigned to Field Officers', 'value': counts.get('assigned_to_inspector', 0), 'metric': 'status:assigned_to_inspector', 'style': 'stat-warning'},
            {'label': 'Enquiry Reports Received', 'value': counts.get('enquiry_report_submitted', 0), 'metric': 'status:enquiry_report_submitted', 'style': 'stat-info'},
            {'label': 'Forwarded to PO', 'value': _count_multi(counts, ['forwarded_to_po', 'forwarded_to_jmd']), 'metric': 'multi:forwarded_to_po,forwarded_to_jmd', 'style': 'stat-violet'},
        ]
    if user_role in ('cmd_apspdcl', 'cmd_apepdcl', 'cmd_apcpdcl', 'cgm_hr_transco'):
        return [
            {'label': 'Pending for Action', 'value': counts.get('action_instructed', 0), 'metric': 'status:action_instructed', 'style': 'stat-warning'},
            {'label': 'Action Report Submitted', 'value': counts.get('action_taken', 0), 'metric': 'status:action_taken', 'style': 'stat-success'},
        ]
    if user_role == 'inspector':
        return [
            {'label': 'Assigned', 'value': counts.get('assigned_to_inspector', 0), 'metric': 'status:assigned_to_inspector', 'style': 'stat-primary'},
            {'label': 'Enquiry In Process', 'value': counts.get('enquiry_in_progress', 0), 'metric': 'status:enquiry_in_progress', 'style': 'stat-warning'},
            {'label': 'Report Submitted', 'value': counts.get('enquiry_report_submitted', 0), 'metric': 'status:enquiry_report_submitted', 'style': 'stat-success'},
        ]
    if user_role == 'data_entry':
        return [
            {'label': 'Received', 'value': counts.get('received', 0), 'metric': 'status:received', 'style': 'stat-primary'},
            {'label': 'Forwarded to CVO/DSP', 'value': counts.get('forwarded_to_cvo', 0), 'metric': 'status:forwarded_to_cvo', 'style': 'stat-info'},
            {'label': 'Sent for Permission', 'value': counts.get('sent_for_permission', 0), 'metric': 'status:sent_for_permission', 'style': 'stat-warning'},
        ]
    return [
        {'label': 'Total', 'value': len(petitions), 'metric': 'all', 'style': 'stat-primary'},
    ]


def _get_workflow_stage_stats(petitions):
    stage_map = {
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
    counts = {f'stage_{i}': 0 for i in range(1, 7)}
    for p in petitions:
        stage = stage_map.get(p.get('status'), 1)
        counts[f'stage_{stage}'] += 1
    return counts


def get_dashboard_drilldown(user_role, user_id, cvo_office, metric):
    petitions = get_petitions_for_user(user_id, user_role, cvo_office, status_filter=None)
    stage_map = {
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

    if metric == 'all':
        return petitions[:500]

    if metric == 'active':
        return [p for p in petitions if (p.get('status') or '') != 'closed'][:500]

    if metric in {f'stage_{i}' for i in range(1, 7)}:
        stage_num = int(metric.split('_')[1])
        filtered = [p for p in petitions if stage_map.get(p.get('status'), 1) == stage_num]
        return filtered[:500]

    if metric.startswith('status:'):
        wanted = metric.split(':', 1)[1]
        return [p for p in petitions if p.get('status') == wanted][:500]

    if metric.startswith('multi:'):
        wanted = set(metric.split(':', 1)[1].split(','))
        return [p for p in petitions if p.get('status') in wanted][:500]

    if metric.startswith('petition_type:'):
        wanted = metric.split(':', 1)[1]
        return [p for p in petitions if (p.get('petition_type') or '') == wanted][:500]

    if metric.startswith('source:'):
        wanted = metric.split(':', 1)[1]
        return [p for p in petitions if (p.get('source_of_petition') or '') == wanted][:500]

    if metric.startswith('mode:'):
        wanted = metric.split(':', 1)[1]
        if wanted == 'permission':
            return [p for p in petitions if bool(p.get('requires_permission'))][:500]
        if wanted == 'direct':
            return [p for p in petitions if not bool(p.get('requires_permission'))][:500]
        return []

    if metric.startswith('received_at:'):
        wanted = metric.split(':', 1)[1]
        return [p for p in petitions if (p.get('received_at') or '') == wanted][:500]

    if metric.startswith('officer:'):
        raw_wanted = metric.split(':', 1)[1]
        try:
            wanted = int(raw_wanted)
        except (TypeError, ValueError):
            return []
        return [p for p in petitions if int(p.get('assigned_inspector_id') or 0) == wanted][:500]

    if metric.startswith('month:'):
        wanted = metric.split(':', 1)[1]
        return [
            p for p in petitions
            if p.get('received_date') and p.get('received_date').strftime('%Y-%m') == wanted
        ][:500]

    if metric == 'po_permission_given':
        conn = get_db()
        try:
            cur = dict_cursor(conn)
            cur.execute("""
                SELECT DISTINCT petition_id
                FROM petition_tracking
                WHERE from_user_id = %s
                  AND action = 'Permission Approved - Sent to CVO'
            """, (user_id,))
            ids = [r['petition_id'] for r in cur.fetchall()]
            if not ids:
                return []
            cur.execute("""
                SELECT p.*
                FROM petitions p
                WHERE p.id = ANY(%s)
                ORDER BY p.created_at DESC
            """, (ids,))
            return [dict(r) for r in cur.fetchall()][:500]
        finally:
            conn.close()

    if metric not in {'sla_total', 'sla_in_progress', 'sla_within', 'sla_breached'}:
        return []

    return _get_sla_filtered_petitions(petitions, metric)[:500]


def _get_sla_stats_for_petitions(petitions):
    return {
        'sla_total': len(_get_sla_filtered_petitions(petitions, 'sla_total')),
        'sla_in_progress': len(_get_sla_filtered_petitions(petitions, 'sla_in_progress')),
        'sla_within': len(_get_sla_filtered_petitions(petitions, 'sla_within')),
        'sla_breached': len(_get_sla_filtered_petitions(petitions, 'sla_breached')),
    }


def _get_sla_filtered_petitions(petitions, metric):
    if not petitions:
        return []
    petition_ids = [p['id'] for p in petitions if p.get('id')]
    if not petition_ids:
        return []

    tracking_index = {}
    conn = get_db()
    try:
        cur = dict_cursor(conn)
        cur.execute("""
            SELECT
                petition_id,
                MIN(CASE WHEN status_after = 'assigned_to_inspector' THEN created_at END) AS assigned_at,
                MIN(CASE WHEN status_after = 'closed' THEN created_at END) AS closed_at
            FROM petition_tracking
            WHERE petition_id = ANY(%s)
            GROUP BY petition_id
        """, (petition_ids,))
        for row in cur.fetchall():
            tracking_index[row['petition_id']] = dict(row)
    finally:
        conn.close()

    now = datetime.now()
    out = []
    for p in petitions:
        t = tracking_index.get(p['id']) or {}
        assigned_at = t.get('assigned_at')
        closed_at = t.get('closed_at')
        if not assigned_at:
            continue

        sla_days = 7 if (p.get('enquiry_type') == 'preliminary') else 45
        end_time = closed_at or now
        elapsed_days = (end_time - assigned_at).days
        is_within = closed_at and elapsed_days <= sla_days
        is_breached = (closed_at and elapsed_days > sla_days) or (not closed_at and elapsed_days > sla_days)
        is_in_progress = (not closed_at and elapsed_days <= sla_days)

        include = (
            metric == 'sla_total'
            or (metric == 'sla_within' and is_within)
            or (metric == 'sla_breached' and is_breached)
            or (metric == 'sla_in_progress' and is_in_progress)
        )
        if include:
            out.append(p)
    return out


def _get_sla_stats(conn, user_role, user_id=None):
    """
    SLA window: 7 days (preliminary) / 45 days (detailed) from assignment to petition closure.
    """
    cur = dict_cursor(conn)
    query = """
        SELECT
            p.id,
            p.enquiry_type,
            MIN(CASE WHEN pt.status_after = 'assigned_to_inspector' THEN pt.created_at END) AS assigned_at,
            MIN(CASE WHEN pt.status_after = 'closed' THEN pt.created_at END) AS closed_at
        FROM petitions p
        LEFT JOIN petition_tracking pt ON pt.petition_id = p.id
    """
    conditions = []
    params = []

    if user_role in ('cvo_apspdcl', 'cvo_apepdcl', 'cvo_apcpdcl', 'dsp'):
        office_map = {'cvo_apspdcl': 'apspdcl', 'cvo_apepdcl': 'apepdcl', 'cvo_apcpdcl': 'apcpdcl', 'dsp': 'headquarters'}
        conditions.append("p.target_cvo = %s")
        params.append(office_map[user_role])
    elif user_role == 'inspector' and user_id:
        conditions.append("p.assigned_inspector_id = %s")
        params.append(user_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " GROUP BY p.id"
    cur.execute(query, params)
    rows = cur.fetchall()

    total = 0
    within = 0
    breached = 0
    in_progress = 0
    now = datetime.now()

    for row in rows:
        assigned_at = row.get('assigned_at')
        closed_at = row.get('closed_at')
        enquiry_type = row.get('enquiry_type') or 'detailed'
        sla_days = 7 if enquiry_type == 'preliminary' else 45
        if not assigned_at:
            continue

        total += 1
        end_time = closed_at or now
        elapsed_days = (end_time - assigned_at).days

        if closed_at:
            if elapsed_days <= sla_days:
                within += 1
            else:
                breached += 1
        else:
            if elapsed_days > sla_days:
                breached += 1
            else:
                in_progress += 1

    return {
        'sla_total': total,
        'sla_within': within,
        'sla_breached': breached,
        'sla_in_progress': in_progress,
    }

