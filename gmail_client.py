# ============================================================================
#  GMAIL (IMAP)  —  lee el inbox, crea etiquetas y archiva. SOLO ORGANIZA.
# ============================================================================
#  Auth: IMAP + App Password (con verificación en 2 pasos ON). No usa la API
#  de Google ni OAuth. En Gmail, cada "carpeta" IMAP es una etiqueta.
#    - Etiquetar        = COPY del mensaje a la carpeta/etiqueta
#    - Archivar         = quitarlo del INBOX (UID EXPUNGE tras marcar \Deleted)
#  Nunca borra: expulsar del INBOX solo quita la etiqueta "Inbox"; el correo
#  queda guardado bajo su etiqueta y en "Todos".
# ============================================================================
import email
import imaplib
import re
from datetime import datetime
from email.header import decode_header
from email.utils import parseaddr

IMAP_HOST = "imap.gmail.com"

_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def _internaldate(raw):
    """Fecha real del servidor, sacada de la respuesta FETCH."""
    m = re.search(r'INTERNALDATE "(\d{1,2})-(\w{3})-(\d{4})', raw)
    if not m or m.group(2).lower() not in _MONTHS:
        return None
    return datetime(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)))


def _decode(s):
    """Decodifica encabezados MIME (=?utf-8?...?=) a texto plano."""
    if not s:
        return ""
    out = []
    for part, enc in decode_header(s):
        if isinstance(part, bytes):
            try:
                out.append(part.decode(enc or "utf-8", "replace"))
            except (LookupError, TypeError):
                out.append(part.decode("utf-8", "replace"))
        else:
            out.append(part)
    return "".join(out).strip()


def _strip_html(raw):
    raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = raw.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", raw).strip()


def _quote(name):
    return '"' + name.replace('"', "") + '"'


class GmailClient:
    def __init__(self, address, app_password):
        self.address = address
        self.app_password = app_password
        self.conn = None
        self._labels = set()
        self._special = {}
        self._to_archive = []

    def connect(self):
        self.conn = imaplib.IMAP4_SSL(IMAP_HOST, 993)
        self.conn.login(self.address, self.app_password)
        self.conn.select("INBOX")           # read-write (default)
        typ, data = self.conn.list()
        if typ == "OK":
            for line in data:
                # ej: (\HasNoChildren) "/" "Facturas y pagos"
                s = line.decode("utf-8", "replace")
                m = re.search(r'"([^"]*)"\s*$', s)
                if not m:
                    continue
                self._labels.add(m.group(1))
                # La papelera se llama "Papelera" en español y "Trash" en inglés:
                # la ubicamos por su marca especial, no por el nombre.
                for flag in ("\\Trash", "\\All"):
                    if flag.lower() in s.lower():
                        self._special[flag] = m.group(1)

    def fetch_inbox(self, limit, only_unread=False):
        crit = "UNSEEN" if only_unread else "ALL"
        typ, data = self.conn.uid("SEARCH", None, crit)
        if typ != "OK" or not data or not data[0]:
            return []
        uids = data[0].split()[-limit:]     # los más recientes
        msgs = []
        for uid in uids:
            typ, d = self.conn.uid(
                "FETCH", uid,
                "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID "
                "LIST-UNSUBSCRIBE LIST-UNSUBSCRIBE-POST)])")
            if typ != "OK" or not d or not d[0]:
                continue
            hdr = email.message_from_bytes(d[0][1])
            name, addr = parseaddr(_decode(hdr.get("From", "")))
            msgs.append({
                "uid": uid.decode(),
                "from_email": addr.lower(),
                "from_name": name,
                "subject": _decode(hdr.get("Subject", "")),
                "date": _decode(hdr.get("Date", "")),
                "message_id": (hdr.get("Message-ID", "") or "").strip(),
                "unsub": (hdr.get("List-Unsubscribe", "") or "").strip(),
                "unsub_oneclick": "one-click" in
                                  (hdr.get("List-Unsubscribe-Post", "") or "").lower(),
            })
        return msgs

    def fetch_body(self, uid, max_chars=600):
        """Snippet del cuerpo (solo para la IA). BODY.PEEK no marca como leído."""
        try:
            typ, d = self.conn.uid("FETCH", uid, "(BODY.PEEK[]<0.8000>)")
            if typ != "OK" or not d or not d[0]:
                return ""
            msg = email.message_from_bytes(d[0][1])
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    if ctype in ("text/plain", "text/html"):
                        payload = part.get_payload(decode=True) or b""
                        body = payload.decode(part.get_content_charset() or "utf-8", "replace")
                        if ctype == "text/plain":
                            break
            else:
                payload = msg.get_payload(decode=True) or b""
                body = payload.decode(msg.get_content_charset() or "utf-8", "replace")
            return _strip_html(body)[:max_chars]
        except Exception as e:
            print(f"[gmail] body {uid}: {e}")
            return ""

    def ensure_label(self, name):
        if name in self._labels:
            return
        self.conn.create(_quote(name))
        self._labels.add(name)

    def apply(self, uid, label, archive):
        """Etiqueta el correo y, si archive=True, lo saca del inbox."""
        self.ensure_label(label)
        u = uid.encode() if isinstance(uid, str) else uid
        self.conn.uid("COPY", u, _quote(label))
        if archive:
            self.conn.uid("STORE", u, "+FLAGS", r"(\Deleted)")
            self._to_archive.append(u)

    def commit(self):
        """Confirma los archivados (UID EXPUNGE preciso; no toca otros correos)."""
        if not self._to_archive:
            return
        uidset = b",".join(self._to_archive)
        typ, _ = self.conn.uid("EXPUNGE", uidset)
        if typ != "OK":
            self.conn.expunge()   # fallback si el servidor no soporta UID EXPUNGE
        self._to_archive = []

    # --- Purga / reportes --------------------------------------------------
    def sweep(self, folder, cutoff, limit, keep_flagged=True):
        """Correos de 'folder' anteriores a 'cutoff' (dd-Mon-yyyy), sin estrella.
        Devuelve uid, asunto, remitente, si está leído y su antigüedad real."""
        if folder not in self._labels:
            return []
        typ, _ = self.conn.select(_quote(folder))
        if typ != "OK":
            return []
        crit = ["BEFORE", cutoff]
        if keep_flagged:
            crit.append("UNFLAGGED")     # respeta lo que marcaste con estrella
        typ, data = self.conn.uid("SEARCH", None, *crit)
        if typ != "OK" or not data or not data[0]:
            return []

        out = []
        for uid in data[0].split()[:limit]:
            typ, d = self.conn.uid(
                "FETCH", uid,
                "(FLAGS INTERNALDATE BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
            if typ != "OK" or not d:
                continue
            raw = b" ".join(p if isinstance(p, bytes) else p[0]
                            for p in d if p).decode("utf-8", "replace")
            hdr_bytes = next((p[1] for p in d if isinstance(p, tuple)), b"")
            hdr = email.message_from_bytes(hdr_bytes)
            _n, addr = parseaddr(_decode(hdr.get("From", "")))
            out.append({
                "uid": uid.decode(),
                "subject": _decode(hdr.get("Subject", "")),
                "from_email": addr.lower(),
                "read": "\\Seen" in raw,
                "date": _internaldate(raw),
            })
        return out

    def trash(self, uids):
        """Mueve a la papelera (recuperable ~30 días). No borra permanentemente."""
        if not uids:
            return 0
        dest = self._special.get("\\Trash") or "[Gmail]/Trash"
        us = [u.encode() if isinstance(u, str) else u for u in uids]
        uidset = b",".join(us)
        self.conn.uid("COPY", uidset, _quote(dest))
        self.conn.uid("STORE", uidset, "+FLAGS", r"(\Deleted)")
        typ, _ = self.conn.uid("EXPUNGE", uidset)
        if typ != "OK":
            self.conn.expunge()
        return len(us)

    def heavy(self, min_bytes, limit):
        """Los correos más pesados (lo que de verdad ocupa tu almacenamiento)."""
        folder = self._special.get("\\All")
        if not folder:
            return []
        typ, _ = self.conn.select(_quote(folder), readonly=True)
        if typ != "OK":
            return []
        typ, data = self.conn.uid("SEARCH", None, "LARGER", str(min_bytes))
        if typ != "OK" or not data or not data[0]:
            return []
        out = []
        for uid in data[0].split()[-400:]:      # los más recientes que pesan
            typ, d = self.conn.uid(
                "FETCH", uid,
                "(RFC822.SIZE BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])")
            if typ != "OK" or not d:
                continue
            raw = b" ".join(p if isinstance(p, bytes) else p[0]
                            for p in d if p).decode("utf-8", "replace")
            m = re.search(r"RFC822\.SIZE\s+(\d+)", raw)
            hdr_bytes = next((p[1] for p in d if isinstance(p, tuple)), b"")
            hdr = email.message_from_bytes(hdr_bytes)
            out.append({
                "size": int(m.group(1)) if m else 0,
                "subject": _decode(hdr.get("Subject", "")),
                "from_email": parseaddr(_decode(hdr.get("From", "")))[1].lower(),
            })
        out.sort(key=lambda x: x["size"], reverse=True)
        return out[:limit]

    def logout(self):
        for fn in (self.conn.close, self.conn.logout):
            try:
                fn()
            except Exception:
                pass
