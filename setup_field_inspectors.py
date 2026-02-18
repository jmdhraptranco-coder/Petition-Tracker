"""
Seed CVO and Field Inspector Accounts
Run after DB setup:
    python setup_field_inspectors.py
"""
import psycopg2
from werkzeug.security import generate_password_hash
from config import Config

config = Config()


# Default password for seeded accounts. Change after first login.
DEFAULT_PASSWORD = "Change@123"

# Role, office, full name, username
CVO_DEFS = [
    ("cvo_apspdcl", "apspdcl", "CVO APSPDCL", "cvo_apspdcl"),
    ("cvo_apcpdcl", "apcpdcl", "CVO APCPDCL", "cvo_apcpdcl"),
    ("cvo_apepdcl", "apepdcl", "CVO APEPDCL", "cvo_apepdcl"),
]

# CVO role -> list of (inspector full name, username)
INSPECTOR_MAP = {
    "cvo_apspdcl": [
        ("CI / Ananthapuramu", "ci_ananthapuramu"),
        ("CI / Kurnool", "ci_kurnool"),
        ("CI / Kadapa", "ci_kadapa"),
        ("CI / Tirupati", "ci_tirupati"),
        ("CI / Nellore", "ci_nellore"),
    ],
    "cvo_apcpdcl": [
        ("CI / Ongole", "ci_ongole"),
        ("CI / Guntur", "ci_guntur"),
        ("CI / Vijayawada", "ci_vijayawada"),
    ],
    "cvo_apepdcl": [
        ("CI / Eluru", "ci_eluru"),
        ("CI / Rajahmundry", "ci_rajahmundry"),
        ("CI / Visakhapatnam", "ci_visakhapatnam"),
        ("CI / Vizianagaram", "ci_vizianagaram"),
        ("CI / Srikakulam", "ci_srikakulam"),
    ],
}


def upsert_cvo(cur, role, office, full_name, username):
    cur.execute("SELECT id FROM users WHERE role = %s LIMIT 1", (role,))
    row = cur.fetchone()
    password_hash = generate_password_hash(DEFAULT_PASSWORD)

    if row:
        cvo_id = row[0]
        cur.execute(
            """
            UPDATE users
            SET full_name = %s, cvo_office = %s, is_active = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (full_name, office, cvo_id),
        )
        return cvo_id, "updated"

    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    by_username = cur.fetchone()
    if by_username:
        cvo_id = by_username[0]
        cur.execute(
            """
            UPDATE users
            SET full_name = %s, role = %s, cvo_office = %s, is_active = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (full_name, role, office, cvo_id),
        )
        return cvo_id, "updated"

    cur.execute(
        """
        INSERT INTO users (username, password_hash, full_name, role, cvo_office, is_active)
        VALUES (%s, %s, %s, %s, %s, TRUE)
        RETURNING id
        """,
        (username, password_hash, full_name, role, office),
    )
    return cur.fetchone()[0], "created"


def upsert_inspector(cur, full_name, username, cvo_id):
    password_hash = generate_password_hash(DEFAULT_PASSWORD)

    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    if row:
        cur.execute(
            """
            UPDATE users
            SET full_name = %s, role = 'inspector', assigned_cvo_id = %s, is_active = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (full_name, cvo_id, row[0]),
        )
        return "updated"

    cur.execute(
        """
        INSERT INTO users (username, password_hash, full_name, role, assigned_cvo_id, is_active)
        VALUES (%s, %s, %s, 'inspector', %s, TRUE)
        """,
        (username, password_hash, full_name, cvo_id),
    )
    return "created"


def main():
    print("=" * 60)
    print("Petition Tracker - Seed CVO and Field Inspectors")
    print("=" * 60)

    conn = psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )
    try:
        cur = conn.cursor()
        cvo_ids = {}

        print("\nCVO accounts:")
        for role, office, full_name, username in CVO_DEFS:
            cvo_id, result = upsert_cvo(cur, role, office, full_name, username)
            cvo_ids[role] = cvo_id
            print(f"  - {full_name} ({username}) -> {result}")

        print("\nField inspector accounts:")
        for cvo_role, inspectors in INSPECTOR_MAP.items():
            cvo_id = cvo_ids[cvo_role]
            print(f"  {cvo_role}:")
            for full_name, username in inspectors:
                result = upsert_inspector(cur, full_name, username, cvo_id)
                print(f"    - {full_name} ({username}) -> {result}")

        conn.commit()

        print("\nDone.")
        print(f"Default password for newly created users: {DEFAULT_PASSWORD}")
        print("Reset these passwords after first login from Super Admin -> User Management.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()


