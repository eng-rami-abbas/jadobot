import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager

DB_NAME = "database.db"

# =========================
# DATABASE CONNECTION
# =========================

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# 🔥 مهم
def getDatabaseConnection():
    return sqlite3.connect(DB_NAME)


# =========================
# INIT DATABASE
# =========================

def init_db():
    with get_db() as conn:
        cur = conn.cursor()

        # USERS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            username TEXT,
            balance REAL DEFAULT 0,
            agreed_terms INTEGER DEFAULT 0,
            temp_username TEXT,
            state TEXT,
            ichancy_account TEXT,
            ichancy_password TEXT,
            ichancy_player_id TEXT,
            created_at TEXT
        )
        """)

        # TRANSACTIONS
        cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT,
            type TEXT,
            method TEXT,
            amount REAL,
            transfer_num TEXT,
            status TEXT,
            created_at TEXT
        )
        """)

    migrate_db()


def migrate_db():
    with get_db() as conn:
        cur = conn.cursor()

        try:
            cur.execute("ALTER TABLE users ADD COLUMN agreed_terms INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            cur.execute("ALTER TABLE users ADD COLUMN balance REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            cur.execute("ALTER TABLE users ADD COLUMN temp_username TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cur.execute("ALTER TABLE users ADD COLUMN state TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cur.execute("ALTER TABLE users ADD COLUMN ichancy_account TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cur.execute("ALTER TABLE users ADD COLUMN ichancy_password TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cur.execute("ALTER TABLE users ADD COLUMN ichancy_player_id TEXT")
        except sqlite3.OperationalError:
            pass


# ← إصلاح: تهيئة قاعدة البيانات عند استيراد الموديول
# هذا يضمن أن الجداول موجودة قبل أي عملية إدراج
try:
    init_db()
except Exception as e:
    print(f"Warning: Could not initialize SQLite database: {e}")


# =========================
# USERS
# =========================

def getUserByTelegramId(telegram_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cur.fetchone()
        return dict(user) if user else None


def updateUser(telegram_id, fields):
    if not fields:
        return False

    with get_db() as conn:
        cur = conn.cursor()
        set_clause = ", ".join(f"{key} = ?" for key in fields.keys())
        values = list(fields.values()) + [telegram_id]
        cur.execute(f"UPDATE users SET {set_clause} WHERE telegram_id = ?", values)
        return cur.rowcount > 0


def setUserState(telegram_id, state):
    with get_db() as conn:
        cur = conn.cursor()
        user = getUserByTelegramId(telegram_id)
        if not user:
            cur.execute("INSERT OR IGNORE INTO users (telegram_id, created_at) VALUES (?, ?)",
                        (telegram_id, datetime.now(timezone.utc).isoformat()))
        cur.execute("UPDATE users SET state = ? WHERE telegram_id = ?", (state, telegram_id))


def getUserState(telegram_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT state FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cur.fetchone()
        return row[0] if row else None


def deleteUser(telegram_id):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
        return cur.rowcount > 0


def insertNewUser(telegram_id, username):
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR IGNORE INTO users (telegram_id, username, created_at)
                VALUES (?, ?, ?)
            """, (telegram_id, username, datetime.now(timezone.utc).isoformat()))
    except sqlite3.OperationalError as e:
        print(f"Database error in insertNewUser: {e}")
        # Try to initialize database if table doesn't exist
        if "no such table" in str(e):
            print("Initializing database tables...")
            init_db()
            # Retry the operation
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT OR IGNORE INTO users (telegram_id, username, created_at)
                    VALUES (?, ?, ?)
                """, (telegram_id, username, datetime.now(timezone.utc).isoformat()))


# =========================
# TRANSACTIONS
# =========================

def insertTransaction(telegram_id, value, action_type, provider_type, transfer_num):
    try:
        with get_db() as conn:
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO transactions
                (telegram_id, type, method, amount, transfer_num, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                telegram_id,
                action_type,
                provider_type,
                value,
                transfer_num,
                "pending",
                datetime.utcnow().isoformat()
            ))

            return cur.lastrowid

    except Exception as e:
        print("DB ERROR:", e)
        return None


def add_transaction(user_id, type_, amount):
    return insertTransaction(user_id, amount, type_, "manual", "-")


# 🔥🔥🔥 الإصلاح النهائي - قراءة من Supabase
def get_user_transactions(telegram_id, tx_type=None):
    try:
        import supabase_integration as supa
        client = supa.get_client()

        query = client.table("transactions") \
            .select("*") \
            .eq("telegram_id", telegram_id) \
            .order("created_at", desc=True)

        if tx_type:
            query = query.eq("type", tx_type)

        res = query.execute()
        return res.data if res.data else []
    except Exception as e:
        print(f"❌ get_user_transactions error: {e}")
        return []


# =========================
# ADMIN / DASHBOARD APIs
# =========================

def get_all_users(limit=100):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cur.fetchall()]


def get_transactions_by_type(tx_type):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM transactions
            WHERE type = ?
            ORDER BY id DESC
            LIMIT 100
        """, (tx_type,))
        return [dict(row) for row in cur.fetchall()]


# =========================
# UPDATE STATUS
# =========================

def update_transaction_status(transaction_id, transaction_type, status):
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE transactions
                SET status = ?
                WHERE id = ? AND type = ?
            """, (status, transaction_id, transaction_type))

            return True
    except:
        return False


def get_transaction_by_id(transaction_id, transaction_type):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM transactions
            WHERE id = ? AND type = ?
        """, (transaction_id, transaction_type))

        row = cur.fetchone()
        return dict(row) if row else None


# =========================
# BALANCE
# =========================

def update_user_balance(telegram_id, new_balance):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE users
            SET balance = ?
            WHERE telegram_id = ?
        """, (new_balance, telegram_id))


# =========================
# TERMS SYSTEM
# =========================

def set_user_agreed(telegram_id: int):
    try:
        with get_db() as conn:
            cur = conn.cursor()

            cur.execute("""
                INSERT OR IGNORE INTO users (telegram_id, agreed_terms, created_at)
                VALUES (?, 0, datetime('now'))
            """, (telegram_id,))

            cur.execute("""
                UPDATE users
                SET agreed_terms = 1
                WHERE telegram_id = ?
            """, (telegram_id,))
    except sqlite3.OperationalError as e:
        print(f"Database error in set_user_agreed: {e}")
        # Try to initialize database if table doesn't exist
        if "no such table" in str(e):
            print("Initializing database tables...")
            init_db()
            # Retry the operation
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT OR IGNORE INTO users (telegram_id, agreed_terms, created_at)
                    VALUES (?, 0, datetime('now'))
                """, (telegram_id,))
                cur.execute("""
                    UPDATE users
                    SET agreed_terms = 1
                    WHERE telegram_id = ?
                """, (telegram_id,))


def has_user_agreed(telegram_id: int) -> bool:
    with get_db() as conn:
        cur = conn.cursor()

        try:
            cur.execute("""
                SELECT agreed_terms FROM users
                WHERE telegram_id = ?
            """, (telegram_id,))
        except:
            return False

        row = cur.fetchone()

        if not row:
            return False

        return row["agreed_terms"] == 1
