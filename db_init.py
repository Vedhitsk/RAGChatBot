import sqlite3
import bcrypt

def init_db():
    conn = sqlite3.connect("company_policies.db")
    cursor = conn.cursor()

    # Create Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,         -- 'admin' or 'employee'
            department TEXT NOT NULL    -- 'HR', 'Engineering', 'Finance', etc.
        )
    ''')

    # Insert Mock Users safely if they don't exist
    mock_users = [
        ("admin", "admin123", "admin", "All"),
        ("alice_hr", "securehr", "employee", "HR"),
        ("bob_eng", "devpass", "employee", "Engineering"),
        ("charlie_fin", "money123", "employee", "Finance")
    ]

    for username, plain_password, role, dept in mock_users:
        try:
            hashed = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute(
                "INSERT INTO users (username, password_hash, role, department) VALUES (?, ?, ?, ?)",
                (username, hashed, role, dept)
            )
        except sqlite3.IntegrityError:
            pass # User already exists

    conn.commit()
    conn.close()
    print("Database initialized successfully with mock users.")

if __name__ == "__main__":
    init_db()