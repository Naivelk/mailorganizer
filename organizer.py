# ============================================================================
#  ORGANIZADOR DE CORREO  —  principal
# ============================================================================
#  Para cada cuenta (Gmail + Outlook): lee el inbox, clasifica (reglas + IA),
#  mueve/etiqueta a carpetas y te manda un resumen por Telegram.
#  Modo SOLO ORGANIZAR: nunca borra. Corre en GitHub Actions (ver workflow).
# ============================================================================
import json
import os
import sys
import traceback
from collections import Counter

import classify
import config as cfg
import notify
from gmail_client import GmailClient
from outlook_client import OutlookClient

STATE_FILE = "state.json"

_CAT_EMOJI = {
    "Importante": "⭐",
    "Trabajo Intercoast": "💼",
    "Clientes": "🤝",
    "Facturas y pagos": "🧾",
    "Newsletters y Promos": "📰",
    "Redes sociales": "📱",
    "Personal": "👤",
}


# --- Estado (ids ya procesados, para no repetir) ---------------------------
def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    for acc in list(state.keys()):
        state[acc] = state[acc][-cfg.MAX_SEEN:]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


# --- Procesa una cuenta ----------------------------------------------------
def process_account(name, client, get_body, seen_ids):
    seen = set(seen_ids)
    messages = client.fetch_inbox(cfg.MAX_FETCH, cfg.ONLY_UNREAD)
    new = [m for m in messages
           if m.get("message_id") and m["message_id"] not in seen]
    if not new:
        return [], list(seen_ids), Counter()

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    classify.classify(new, get_body, api_key)

    actions, counts = [], Counter()
    for m in new:
        cat = m["category"]
        keep = cat in cfg.KEEP_IN_INBOX
        archive = cfg.ARCHIVE_AFTER_LABEL and not keep
        try:
            client.apply(m.get("uid") or m.get("id"), cat, archive)
            counts[cat] += 1
            actions.append((m, cat, archive))
            seen.add(m["message_id"])
        except Exception as e:
            print(f"[{name}] no pude organizar '{m.get('subject','')[:40]}': {e}")
    client.commit()
    return actions, list(seen), counts


def _acc_summary(address, counts, n):
    if n == 0:
        return f"📭 <b>{notify.esc(address)}</b>: nada nuevo por organizar."
    parts = [f"📬 <b>{notify.esc(address)}</b> — {n} correo(s) organizados:"]
    for cat, c in counts.most_common():
        parts.append(f"   {_CAT_EMOJI.get(cat, '📂')} {notify.esc(cat)}: {c}")
    return "\n".join(parts)


def _send_digest(token, chat_id, total, all_counts, summary_lines):
    if total == 0:
        header = ("🧹 <b>Organizador de correo</b>\n"
                  "Tu bandeja ya estaba al día — nada nuevo que mover. ✅")
    else:
        top = " · ".join(f"{_CAT_EMOJI.get(c, '📂')} {c}: {n}"
                         for c, n in all_counts.most_common(3))
        header = (f"🧹 <b>Tu correo quedó organizado</b> ✅\n"
                  f"Moví <b>{total}</b> correo(s) a sus carpetas.\n"
                  f"<i>Top:</i> {top}")
    notify.send_telegram(token, chat_id, header + "\n\n" + "\n\n".join(summary_lines))


# --- Lógica principal ------------------------------------------------------
def run(token, chat_id):
    state = load_state()
    all_counts = Counter()
    summary_lines = []
    total = 0

    # --- Gmail (IMAP) ---
    if cfg.GMAIL_ENABLED:
        pwd = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
        if not pwd:
            print("Aviso: falta GMAIL_APP_PASSWORD; salto Gmail.")
        else:
            g = GmailClient(cfg.GMAIL_ADDRESS, pwd)
            try:
                g.connect()
                acts, seen, counts = process_account(
                    "gmail", g,
                    lambda m: g.fetch_body(m["uid"], cfg.AI_BODY_CHARS),
                    state.get(cfg.GMAIL_ADDRESS, []))
                state[cfg.GMAIL_ADDRESS] = seen
                all_counts += counts
                total += len(acts)
                summary_lines.append(_acc_summary(cfg.GMAIL_ADDRESS, counts, len(acts)))
            except Exception as e:
                print(traceback.format_exc())
                summary_lines.append(
                    f"⚠️ <b>{notify.esc(cfg.GMAIL_ADDRESS)}</b>: error — "
                    f"{notify.esc(str(e)[:140])}")
            finally:
                g.logout()

    # --- Outlook / Hotmail (Graph) ---
    if cfg.OUTLOOK_ENABLED:
        client_id = os.environ.get("MS_CLIENT_ID", "").strip()
        for acc in cfg.OUTLOOK_ACCOUNTS:
            rt = os.environ.get(acc["token_env"], "").strip()
            if not rt or not client_id:
                print(f"Aviso: falta token/client_id para {acc['address']}; la salto.")
                continue
            o = OutlookClient(acc["address"], rt, client_id)
            try:
                o.connect()
                addr = o.address   # la real del token, no la de config
                acts, seen, counts = process_account(
                    acc["name"], o, None, state.get(addr, []))
                state[addr] = seen
                all_counts += counts
                total += len(acts)
                summary_lines.append(_acc_summary(addr, counts, len(acts)))
            except Exception as e:
                print(traceback.format_exc())
                summary_lines.append(
                    f"⚠️ <b>{notify.esc(acc['address'])}</b>: error — "
                    f"{notify.esc(str(e)[:140])}")

    save_state(state)
    if summary_lines:
        _send_digest(token, chat_id, total, all_counts, summary_lines)


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("ERROR: faltan los secrets TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID")
        sys.exit(1)
    try:
        run(token, chat_id)
    except Exception as e:
        print(traceback.format_exc())
        notify.send_telegram(token, chat_id,
                             "⚠️ <b>El organizador de correo falló</b>\n"
                             f"<code>{notify.esc(str(e))[:500]}</code>")
        sys.exit(1)


if __name__ == "__main__":
    main()
