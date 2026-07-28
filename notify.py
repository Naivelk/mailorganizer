# ============================================================================
#  TELEGRAM  —  envío de mensajes (mismo estilo que tus otros bots)
# ============================================================================
import html as _html
import time

import requests


def esc(s):
    return _html.escape(str(s or ""))


def send_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": chat_id, "text": text,
            "parse_mode": "HTML", "disable_web_page_preview": True,
        }, timeout=30)
        if r.status_code != 200:
            print(f"[telegram] {r.status_code}: {r.text[:300]}")
        return r.status_code == 200
    except Exception as e:
        print(f"[telegram] error: {e}")
        return False


def send_batches(token, chat_id, header, blocks):
    """Agrupa los bloques en mensajes por debajo del límite de Telegram (4096)."""
    chunks, cur, cur_len = [], [], 0
    for block in blocks:
        b = block + "\n\n"
        if cur and cur_len + len(b) > 3500:
            chunks.append("".join(cur))
            cur, cur_len = [], 0
        cur.append(b)
        cur_len += len(b)
    if cur:
        chunks.append("".join(cur))

    for i, ch in enumerate(chunks):
        msg = (header + "\n\n" + ch) if i == 0 else ch
        send_telegram(token, chat_id, msg.strip())
        time.sleep(1)   # respeta el rate limit de Telegram
