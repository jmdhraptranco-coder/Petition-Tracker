"""
Create Super Admin User
Run this after setting up the database:
    python create_admin.py
"""
import psycopg2
from werkzeug.security import generate_password_hash
from config import Config

config = Config()

def create_admin():
    print("=" * 50)
    print("Petition Tracker - Admin Setup")
    print("=" * 50)
    
    username = input("Enter admin username [superadmin]: ").strip() or "superadmin"
    password = input("Enter admin password [admin123]: ").strip() or "admin123"
    full_name = input("Enter full name [Super Administrator]: ").strip() or "Super Administrator"

    if config.IS_PRODUCTION and password == "admin123":
        print("\nError: default password is not allowed in production.")
        return
    
    password_hash = generate_password_hash(password)
    
    try:
        conn = psycopg2.connect(**config.get_psycopg2_kwargs())
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            cur.execute(
                "UPDATE users SET password_hash = %s, full_name = %s WHERE username = %s",
                (password_hash, full_name, username)
            )
            print(f"\nUser '{username}' updated successfully!")
        else:
            cur.execute(
                """INSERT INTO users (username, password_hash, full_name, role, is_active)
                   VALUES (%s, %s, %s, 'super_admin', TRUE)""",
                (username, password_hash, full_name)
            )
            print(f"\nUser '{username}' created successfully!")
        
        conn.commit()
        conn.close()
        
        print("\nLogin credentials:")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        print("\nDevelopment start: python app.py")
        print("Production start:  python serve.py")
        print("Access at: http://localhost:5000")
        
    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure PostgreSQL is running and the database exists.")
        print("Run database.sql first to create the database and tables.")

if __name__ == '__main__':
    create_admin()

