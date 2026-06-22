import json
import time
import requests
from config import TURSO_URL, TURSO_TOKEN

# Convert libsql:// to https:// for HTTP API
BASE_URL = TURSO_URL.replace("libsql://", "https://") + "/v2/pipeline"
HEADERS = {"Authorization": f"Bearer {TURSO_TOKEN}", "Content-Type": "application/json"}


def _execute(statements: list) -> list:
    payload = {"requests": [{"type": "execute", "stmt": {"sql": s["sql"], "args": s.get("args", [])}} for s in statements] + [{"type": "close"}]}
    response = requests.post(BASE_URL, headers=HEADERS, json=payload)
    response.raise_for_status()
    return response.json()["results"]


def _q(sql: str, args: list = []) -> list:
    results = _execute([{"sql": sql, "args": [{"type": "text", "value": str(a)} for a in args]}])
    rows = results[0].get("response", {}).get("result", {}).get("rows", [])
    cols = [c["name"] for c in results[0].get("response", {}).get("result", {}).get("cols", [])]
    return [dict(zip(cols, [v["value"] for v in row])) for row in rows]


def _run(sql: str, args: list = []):
    _execute([{"sql": sql, "args": [{"type": "text", "value": str(a)} for a in args]}])


def init_db():
    _run("""CREATE TABLE IF NOT EXISTS users (
        user_id     INTEGER PRIMARY KEY,
        username    TEXT,
        tier        TEXT DEFAULT 'free',
        expires_at  INTEGER DEFAULT 0,
        msg_credits INTEGER DEFAULT 10,
        img_credits INTEGER DEFAULT 2,
        active_char TEXT,
        age_verified INTEGER DEFAULT 0,
        nsfw_allowed INTEGER DEFAULT 0
    )""")
    _run("""CREATE TABLE IF NOT EXISTS conversations (
        user_id   INTEGER,
        character TEXT,
        history   TEXT DEFAULT '[]',
        PRIMARY KEY (user_id, character)
    )""")


# ── Users ──────────────────────────────────────────────────────────────────────

def get_user(user_id: int) -> dict | None:
    rows = _q("SELECT * FROM users WHERE user_id = ?", [user_id])
    return rows[0] if rows else None


def create_user(user_id: int, username: str):
    _run("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", [user_id, username or ""])


def get_or_create_user(user_id: int, username: str) -> dict:
    create_user(user_id, username)
    return get_user(user_id)


def update_user(user_id: int, **kwargs):
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]
    _run(f"UPDATE users SET {fields} WHERE user_id = ?", values)


def decrement_message_credit(user_id: int):
    _run("UPDATE users SET msg_credits = msg_credits - 1 WHERE user_id = ?", [user_id])


def decrement_image_credit(user_id: int):
    _run("UPDATE users SET img_credits = img_credits - 1 WHERE user_id = ?", [user_id])


def set_subscription(user_id: int, tier: str, days: int = 30):
    expires_at = int(time.time()) + days * 86400
    msg_credits = 1000 if tier == "premium" else 5000
    img_credits = 50 if tier == "premium" else 200
    update_user(user_id, tier=tier, expires_at=expires_at, msg_credits=msg_credits, img_credits=img_credits)


def get_all_users() -> list:
    return _q("SELECT * FROM users")


def count_users() -> int:
    return int(_q("SELECT COUNT(*) as c FROM users")[0]["c"])


def count_premium() -> int:
    return int(_q("SELECT COUNT(*) as c FROM users WHERE tier != 'free'")[0]["c"])


# ── Conversations ──────────────────────────────────────────────────────────────

def get_conversation_history(user_id: int, character: str) -> list:
    rows = _q("SELECT history FROM conversations WHERE user_id = ? AND character = ?", [user_id, character])
    return json.loads(rows[0]["history"]) if rows else []


def save_conversation(user_id: int, character: str, user_message: str, bot_reply: str):
    history = get_conversation_history(user_id, character)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": bot_reply})
    history = history[-20:]
    _run(
        "INSERT INTO conversations (user_id, character, history) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, character) DO UPDATE SET history = excluded.history",
        [user_id, character, json.dumps(history)]
    )


def count_conversations() -> int:
    return int(_q("SELECT COUNT(*) as c FROM conversations")[0]["c"])


init_db()
