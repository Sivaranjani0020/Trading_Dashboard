import sqlite3
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "trading_dashboard.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ============================================================
    # ADMIN DETAILS
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userid TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # ============================================================
    # XTS LOGIN CREDENTIALS
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS xt_login_credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT UNIQUE NOT NULL,

            interactive_api_key TEXT,
            interactive_api_secret TEXT,

            market_api_key TEXT,
            market_api_secret TEXT,

            static_ip_username TEXT,
            static_ip_password TEXT,
            static_ip_host TEXT,
            static_ip_port INTEGER,

            interactive_token TEXT,
            market_token TEXT,
            token_date TEXT
        )
    """)

    # ============================================================
    # ENABLED CLIENTS
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS enabled_clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT UNIQUE NOT NULL,
            enabled_flag INTEGER DEFAULT 0,
            lots INTEGER DEFAULT 1
        )
    """)

    # ============================================================
    # MASTER CLIENT
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS master_client (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT UNIQUE NOT NULL,
            enabled INTEGER DEFAULT 0
        )
    """)

    # ============================================================
    # PROGRAM LOGS
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS program_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            event TEXT,
            details TEXT
        )
    """)

    # ============================================================
    # ORDER LOGS
    # ============================================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            client_id TEXT,
            action TEXT,
            symbol TEXT,
            token TEXT,
            side TEXT,
            qty INTEGER,
            sl REAL,
            target REAL,
            response TEXT
        )
    """)

    conn.commit()
    conn.close()


# ================================================================
# GENERIC HELPERS
# ================================================================

def fetch_one(query, params=()):
    conn = get_connection()

    try:
        cursor = conn.execute(query, params)
        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        conn.close()


def fetch_all(query, params=()):
    conn = get_connection()

    try:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


def execute(query, params=()):
    conn = get_connection()

    try:
        cursor = conn.execute(query, params)
        conn.commit()

        return cursor.lastrowid

    finally:
        conn.close()


# ================================================================
# ADMIN
# ================================================================

def get_admin(userid):
    return fetch_one(
        """
        SELECT userid, password
        FROM admin_details
        WHERE userid = ?
        """,
        (userid,)
    )

# ================================================================
# ADMIN MANAGEMENT
# ================================================================



def update_admin_password(userid, password):
    execute(
        """
        UPDATE admin_details
        SET password = ?
        WHERE userid = ?
        """,
        (password, userid)
    )




# ================================================================
# CLIENT CREDENTIALS
# ================================================================

def get_client_credentials(client_id):
    return fetch_one(
        """
        SELECT *
        FROM xt_login_credentials
        WHERE client_id = ?
        """,
        (client_id,)
    )


def get_all_client_credentials():
    return fetch_all(
        """
        SELECT *
        FROM xt_login_credentials
        ORDER BY client_id
        """
    )


def update_client_credentials(
    client_id,
    interactive_api_key,
    interactive_api_secret,
    market_api_key,
    market_api_secret,
    static_ip_username=None,
    static_ip_password=None,
    static_ip_host=None,
    static_ip_port=None
):
    execute(
        """
        UPDATE xt_login_credentials
        SET
            interactive_api_key = ?,
            interactive_api_secret = ?,
            market_api_key = ?,
            market_api_secret = ?,
            static_ip_username = ?,
            static_ip_password = ?,
            static_ip_host = ?,
            static_ip_port = ?,

            -- Credentials changed, so old tokens
            -- must not be reused.
            interactive_token = NULL,
            market_token = NULL,
            token_date = NULL

        WHERE client_id = ?
        """,
        (
            interactive_api_key,
            interactive_api_secret,
            market_api_key,
            market_api_secret,
            static_ip_username,
            static_ip_password,
            static_ip_host,
            static_ip_port,
            client_id
        )
    )

def update_client_tokens(
    client_id,
    interactive_token,
    market_token,
    token_date
):
    execute(
        """
        UPDATE xt_login_credentials
        SET
            interactive_token = ?,
            market_token = ?,
            token_date = ?
        WHERE client_id = ?
        """,
        (
            interactive_token,
            market_token,
            token_date,
            client_id
        )
    )


# ================================================================
# ENABLED CLIENTS
# ================================================================

def get_enabled_clients():
    return fetch_all(
        """
        SELECT client_id, lots
        FROM enabled_clients
        WHERE enabled_flag = 1
        ORDER BY client_id
        """
    )


def get_all_enabled_client_rows():
    return fetch_all(
        """
        SELECT *
        FROM enabled_clients
        ORDER BY client_id
        """
    )


def get_enabled_client(client_id):
    return fetch_one(
        """
        SELECT *
        FROM enabled_clients
        WHERE client_id = ?
        """,
        (client_id,)
    )


def set_client_enabled(client_id, enabled):
    existing = get_enabled_client(client_id)

    if existing:
        execute(
            """
            UPDATE enabled_clients
            SET enabled_flag = ?
            WHERE client_id = ?
            """,
            (
                1 if enabled else 0,
                client_id
            )
        )
    else:
        execute(
            """
            INSERT INTO enabled_clients
            (
                client_id,
                enabled_flag,
                lots
            )
            VALUES (?, ?, ?)
            """,
            (
                client_id,
                1 if enabled else 0,
                1
            )
        )


def set_client_lots(client_id, lots):
    existing = get_enabled_client(client_id)

    if existing:
        execute(
            """
            UPDATE enabled_clients
            SET lots = ?
            WHERE client_id = ?
            """,
            (
                lots,
                client_id
            )
        )
    else:
        execute(
            """
            INSERT INTO enabled_clients
            (
                client_id,
                enabled_flag,
                lots
            )
            VALUES (?, ?, ?)
            """,
            (
                client_id,
                0,
                lots
            )
        )


# ================================================================
# MASTER CLIENT
# ================================================================

def get_enabled_master_client():
    return fetch_one(
        """
        SELECT client_id
        FROM master_client
        WHERE enabled = 1
        LIMIT 1
        """
    )


# ================================================================
# LOGGING
# ================================================================

def insert_program_log(timestamp, event, details):
    execute(
        """
        INSERT INTO program_logs
        (
            timestamp,
            event,
            details
        )
        VALUES (?, ?, ?)
        """,
        (
            timestamp,
            event,
            json.dumps(details or {})
        )
    )


def insert_order_log(
    timestamp,
    client_id,
    action,
    symbol,
    token,
    side,
    qty,
    sl,
    target,
    response
):
    execute(
        """
        INSERT INTO order_logs
        (
            timestamp,
            client_id,
            action,
            symbol,
            token,
            side,
            qty,
            sl,
            target,
            response
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            timestamp,
            client_id,
            action,
            symbol,
            token,
            side,
            qty,
            sl,
            target,
            str(response)
        )
    )


# ================================================================
# INITIALIZE DATABASE
# ================================================================

init_db()

def add_admin(userid, password):
    execute(
        """
        INSERT INTO admin_details (userid, password)
        VALUES (?, ?)
        """,
        (userid, password)
    )


def delete_admin(userid):
    execute(
        """
        DELETE FROM admin_details
        WHERE userid = ?
        """,
        (userid,)
    )


def get_all_admins():
    return fetch_all(
        """
        SELECT id, userid
        FROM admin_details
        ORDER BY userid
        """
    )


def add_client(
    client_id,
    interactive_api_key,
    interactive_api_secret,
    market_api_key,
    market_api_secret,
    static_ip_username=None,
    static_ip_password=None,
    static_ip_host=None,
    static_ip_port=None,
    lots=1
):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO xt_login_credentials (
                client_id,
                interactive_api_key,
                interactive_api_secret,
                market_api_key,
                market_api_secret,
                static_ip_username,
                static_ip_password,
                static_ip_host,
                static_ip_port,
                interactive_token,
                market_token,
                token_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)
            """,
            (
                client_id,
                interactive_api_key,
                interactive_api_secret,
                market_api_key,
                market_api_secret,
                static_ip_username,
                static_ip_password,
                static_ip_host,
                static_ip_port
            )
        )

        cursor.execute(
            """
            INSERT INTO enabled_clients (
                client_id,
                enabled_flag,
                lots
            )
            VALUES (?, 0, ?)
            """,
            (client_id, lots)
        )

        conn.commit()

    finally:
        conn.close()


def delete_client(client_id):
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM xt_login_credentials
            WHERE client_id = ?
            """,
            (client_id,)
        )

        cursor.execute(
            """
            DELETE FROM enabled_clients
            WHERE client_id = ?
            """,
            (client_id,)
        )

        conn.commit()

    finally:
        conn.close()