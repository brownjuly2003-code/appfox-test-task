"""Telegram-бот управления пайплайном — на чистом requests long-polling.

Зачем не python-telegram-bot: httpx в нём на Win11 IPv6-first, висит на get_me.
requests с IPv4-резолвом не имеет этого баги. Меньше зависимостей, проще.

Команды:
  /start           справка + список команд
  /run             запуск пайплайна (фон)
  /status          текущий шаг + хвост лога
  /export csv|md|queries|state|raw   выгрузить артефакт
  /seeds           отдать seeds.yaml
  /upload_seeds    (caption: confirm) — заменить seeds.yaml после валидации

Запуск: python -m bot.tg  (TG_BOT_TOKEN + TG_ALLOWED_CHAT_IDS в .env)
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()


PROJECT_ROOT = Path(__file__).parent.parent
SEEDS_PATH = PROJECT_ROOT / "data" / "seeds.yaml"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
STATE_PATH = PROJECT_ROOT / "data" / "state" / "core.json"

API_BASE = "https://api.telegram.org/bot{token}/{method}"


@dataclass
class RunState:
    status: str = "idle"
    step: str = ""
    started_at: float = 0.0
    finished_at: float = 0.0
    last_lines: list[str] = field(default_factory=list)
    returncode: int | None = None


STATE = RunState()
ALLOWED: set[int] = set()
RUN_LOCK = threading.Lock()
TOKEN = ""


def api(method: str, **kwargs):
    url = API_BASE.format(token=TOKEN, method=method)
    try:
        r = requests.post(url, timeout=35, **kwargs)
        return r.json()
    except requests.RequestException as e:
        print(f"[api:err] {method}: {e}", flush=True)
        return {"ok": False, "error": str(e)}


def send_msg(chat_id: int, text: str, parse_mode: str | None = None):
    data = {"chat_id": chat_id, "text": text[:4000], "disable_web_page_preview": True}
    if parse_mode:
        data["parse_mode"] = parse_mode
    return api("sendMessage", data=data)


def send_doc(chat_id: int, path: Path, filename: str | None = None):
    with path.open("rb") as f:
        return api(
            "sendDocument",
            data={"chat_id": chat_id},
            files={"document": (filename or path.name, f)},
        )


def get_file(file_id: str) -> bytes | None:
    info = api("getFile", data={"file_id": file_id})
    if not info.get("ok"):
        return None
    file_path = info["result"]["file_path"]
    r = requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{file_path}", timeout=30)
    return r.content if r.ok else None


def allowed(chat_id: int) -> bool:
    if not ALLOWED:
        return False  # deny by default
    return chat_id in ALLOWED


def _run_pipeline_thread(chat_id: int):
    STATE.status = "running"
    STATE.step = "starting"
    STATE.started_at = time.time()
    STATE.last_lines = []
    STATE.returncode = None
    send_msg(chat_id, "Запускаю пайплайн… /status для прогресса.")

    cmd = [
        sys.executable, "run.py",
        "--config", str(SEEDS_PATH),
        "--out", str(OUTPUT_DIR),
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdout
    for line in proc.stdout:
        line = line.rstrip()
        if not line:
            continue
        STATE.last_lines.append(line)
        if len(STATE.last_lines) > 50:
            STATE.last_lines = STATE.last_lines[-50:]
        for marker in ("Шаг 1:", "Шаг 2:", "Шаг 3:", "Шаг 4:", "Шаг 5:", "Шаг 6:"):
            if marker in line:
                STATE.step = line.strip()
                break
    proc.wait()
    STATE.finished_at = time.time()
    STATE.returncode = proc.returncode
    STATE.status = "done" if proc.returncode == 0 else "error"
    elapsed = STATE.finished_at - STATE.started_at
    send_msg(
        chat_id,
        f"Пайплайн завершён: exit={proc.returncode}, {elapsed:.1f}s.\n"
        f"Готово к /export csv | md | queries | state.",
    )


# ---------- handlers ----------

def cmd_start(chat_id: int, args: str):
    send_msg(
        chat_id,
        "Appfox SEO Semcore Agent — прототип агента семантического ядра.\n\n"
        "/run — запустить пайплайн на текущем seeds.yaml\n"
        "/status — текущий шаг + хвост лога\n"
        "/export csv|md|queries|state|raw — выгрузить артефакт\n"
        "/seeds — текущий seeds.yaml\n"
        "/upload_seeds — заменить seeds.yaml (отправь файл с caption 'confirm')\n",
    )


def cmd_status(chat_id: int, args: str):
    elapsed = ""
    if STATE.status == "running":
        elapsed = f"  ({time.time() - STATE.started_at:.0f}s)"
    elif STATE.finished_at:
        elapsed = f"  (closed {time.time() - STATE.finished_at:.0f}s ago, exit={STATE.returncode})"
    text = f"status: {STATE.status}\nstep: {STATE.step or '—'}{elapsed}\n"
    if STATE.last_lines:
        tail = "\n".join(STATE.last_lines[-10:])
        text += f"\n--- лог ---\n{tail}"
    send_msg(chat_id, text)


def cmd_run(chat_id: int, args: str):
    if not RUN_LOCK.acquire(blocking=False):
        send_msg(chat_id, f"Уже идёт прогон ({time.time() - STATE.started_at:.0f}s). /status.")
        return
    def worker():
        try:
            _run_pipeline_thread(chat_id)
        finally:
            RUN_LOCK.release()
    threading.Thread(target=worker, daemon=True).start()


def cmd_export(chat_id: int, args: str):
    kind = (args.strip().split() or ["csv"])[0].lower()
    files = {
        "csv": OUTPUT_DIR / "decisions.csv",
        "md": OUTPUT_DIR / "decisions.md",
        "queries": OUTPUT_DIR / "queries.csv",
        "state": STATE_PATH,
        "raw": OUTPUT_DIR / "raw_cleaned.json",
    }
    f = files.get(kind)
    if not f or not f.exists():
        send_msg(chat_id, f"Артефакт {kind!r} ещё не сгенерирован. Запусти /run.")
        return
    send_doc(chat_id, f)


def cmd_seeds(chat_id: int, args: str):
    if not SEEDS_PATH.exists():
        send_msg(chat_id, "seeds.yaml не найден")
        return
    send_doc(chat_id, SEEDS_PATH)


def cmd_upload_seeds(chat_id: int, msg: dict):
    doc = msg.get("document")
    if not doc:
        send_msg(chat_id,
                 "Отправь .yaml/.yml файлом и в подписи укажи `confirm` — "
                 "заменю seeds.yaml после валидации.")
        return
    caption = (msg.get("caption") or "").lower()
    if "confirm" not in caption:
        send_msg(chat_id, "Подпись должна содержать `confirm` — без этого замены нет.")
        return
    fname = (doc.get("file_name") or "").lower()
    if not fname.endswith((".yaml", ".yml")):
        send_msg(chat_id, "Только .yaml/.yml.")
        return
    if doc.get("file_size", 0) > 200_000:
        send_msg(chat_id, "Файл слишком большой (>200 КБ).")
        return
    data = get_file(doc["file_id"])
    if not data:
        send_msg(chat_id, "Не удалось скачать файл из TG.")
        return
    try:
        import yaml
        parsed = yaml.safe_load(data.decode("utf-8"))
        for k in ("business_context", "seeds", "modifiers"):
            if k not in parsed:
                raise ValueError(f"missing required key: {k}")
    except Exception as e:
        send_msg(chat_id, f"Невалидный YAML: {e}")
        return
    if SEEDS_PATH.exists():
        SEEDS_PATH.replace(SEEDS_PATH.with_suffix(".yaml.bak"))
    SEEDS_PATH.write_bytes(data)
    send_msg(chat_id, f"seeds.yaml обновлён ({len(data)} байт). /run для прогона.")


COMMANDS = {
    "/start": cmd_start,
    "/help": cmd_start,
    "/run": cmd_run,
    "/status": cmd_status,
    "/export": cmd_export,
    "/seeds": cmd_seeds,
}


def handle_update(upd: dict):
    msg = upd.get("message") or upd.get("edited_message")
    if not msg:
        return
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if not chat_id:
        return
    if not allowed(int(chat_id)):
        # silently ignore non-allowed users (no info leak)
        return

    if msg.get("document"):
        # accept document upload only with /upload_seeds caption
        caption = (msg.get("caption") or "").strip()
        if caption.startswith("/upload_seeds"):
            cmd_upload_seeds(chat_id, msg)
        return

    text = (msg.get("text") or "").strip()
    if not text.startswith("/"):
        return
    parts = text.split(maxsplit=1)
    cmd = parts[0].split("@")[0]  # /run@bot → /run
    args = parts[1] if len(parts) > 1 else ""
    handler = COMMANDS.get(cmd)
    if handler:
        try:
            handler(chat_id, args)
        except Exception as e:
            send_msg(chat_id, f"err: {type(e).__name__}: {e}")
            print(f"[handler:err] {cmd}: {e}", flush=True)
    elif cmd == "/upload_seeds":
        cmd_upload_seeds(chat_id, msg)


def main():
    global TOKEN
    TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
    if not TOKEN:
        raise SystemExit("Set TG_BOT_TOKEN in .env")
    allow_raw = os.getenv("TG_ALLOWED_CHAT_IDS", "").strip()
    if allow_raw:
        for x in allow_raw.split(","):
            x = x.strip()
            if x.lstrip("-").isdigit():
                ALLOWED.add(int(x))
    if not ALLOWED:
        print("[warn] TG_ALLOWED_CHAT_IDS пуст — все запросы будут игнорироваться", flush=True)

    # verify token
    me = api("getMe")
    if not me.get("ok"):
        raise SystemExit(f"Невалидный TG_BOT_TOKEN: {me}")
    print(f"[tg-bot] live as @{me['result']['username']} (allowed: {sorted(ALLOWED)})", flush=True)

    # clear pending updates (drop backlog)
    offset = 0
    while True:
        resp = api("getUpdates", data={"offset": offset, "timeout": 30, "allowed_updates": json.dumps(["message", "edited_message"])})
        if not resp.get("ok"):
            print(f"[poll:err] {resp}", flush=True)
            time.sleep(5)
            continue
        updates = resp.get("result", [])
        for upd in updates:
            offset = upd["update_id"] + 1
            try:
                handle_update(upd)
            except Exception as e:
                print(f"[upd:err] {e}", flush=True)


if __name__ == "__main__":
    main()
