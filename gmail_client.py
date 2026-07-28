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
from email.header import decode_header
from email.utils import parseaddr

IMAP_HOST = "imap.gmail.com"


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
        self._to_archive = []

    def connect(self):
        self.conn = imaplib.IMAP4_SSL(IMAP_HOST, 993)
        self.conn.login(self.address, self.app_password)
        self.conn.select("INBOX")           # read-write (default)
        typ, data = self.conn.list()
        if typ == "OK":
            for line in data:
                # ej: (\HasNoChildren) "/" "Facturas y pagos"
                m = re.search(r'"([^"]*)"\s*$', line.decode("utf-8", "replace"))
                if m:
                    self._labels.add(m.group(1))

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

    def logout(self):
        for fn in (self.conn.close, self.conn.logout):
            try:
                fn()
            except Exception:
                pass
