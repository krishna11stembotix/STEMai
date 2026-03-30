import os, sqlite3, json
DB = os.getenv("APP_DB", "./teacher.db")

def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS progress(
          user_id TEXT PRIMARY KEY,
          data TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS users(
          id TEXT PRIMARY KEY,
          email TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL,
          role TEXT NOT NULL CHECK(role IN ('student','teacher')),
          created_at INTEGER NOT NULL
        )""")

def get_progress(user_id: str):
    with sqlite3.connect(DB) as con:
        row = con.execute("SELECT data FROM progress WHERE user_id=?", (user_id,)).fetchone()
        return json.loads(row[0]) if row else {"user_id": user_id, "skills": {}, "history": []}

def save_progress(user_id: str, data: dict):
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT INTO progress(user_id,data) VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET data=excluded.data",
            (user_id, json.dumps(data))
        )


def get_user_by_email(email: str):
    with sqlite3.connect(DB) as con:
        row = con.execute(
            "SELECT id, email, password_hash, role, created_at FROM users WHERE email=?",
            (email.lower().strip(),)
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "email": row[1],
            "password_hash": row[2],
            "role": row[3],
            "created_at": row[4],
        }


def get_user_by_id(user_id: str):
    with sqlite3.connect(DB) as con:
        row = con.execute(
            "SELECT id, email, password_hash, role, created_at FROM users WHERE id=?",
            (user_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "email": row[1],
            "password_hash": row[2],
            "role": row[3],
            "created_at": row[4],
        }


def create_user(user_id: str, email: str, password_hash: str, role: str, created_at: int):
    with sqlite3.connect(DB) as con:
        con.execute(
            "INSERT INTO users(id,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
            (user_id, email.lower().strip(), password_hash, role, created_at),
        )
