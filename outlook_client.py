# ============================================================================
#  OUTLOOK / HOTMAIL (Microsoft Graph)  —  organiza el inbox. SOLO ORGANIZA.
# ============================================================================
#  Auth: OAuth2 con refresh token (flujo device-code, cliente público SIN
#  secreto). Corre ms_auth.ps1 una vez por cuenta para obtener el token.
#    - Categoría "keep in inbox" -> marca el correo con una categoría (se queda)
#    - Resto                     -> mueve el correo a su carpeta (sale del inbox)
#  Nunca borra.
# ============================================================================
from urllib.parse import quote

import requests

TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
GRAPH = "https://graph.microsoft.com/v1.0"
SCOPE = "Mail.ReadWrite offline_access"


class OutlookClient:
    def __init__(self, address, refresh_token, client_id):
        self.address = address
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.access_token = None
        self._folders = {}   # displayName -> id

    def _headers(self):
        return {"Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"}

    def connect(self):
        r = requests.post(TOKEN_URL, data={
            "client_id": self.client_id,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "scope": SCOPE,
        }, timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"token {r.status_code}: {r.text[:200]}")
        self.access_token = r.json()["access_token"]
        self._load_identity()
        self._load_folders()

    def _load_identity(self):
        """Lee la dirección REAL del token (por si los secrets quedaron cruzados)."""
        try:
            r = requests.get(f"{GRAPH}/me?$select=mail,userPrincipalName",
                             headers=self._headers(), timeout=30)
            if r.status_code == 200:
                d = r.json()
                addr = d.get("mail") or d.get("userPrincipalName")
                if addr:
                    self.address = addr.lower()
        except Exception as e:
            print(f"[outlook] no pude leer /me: {e}")

    def _load_folders(self):
        url = f"{GRAPH}/me/mailFolders?$top=200&$select=id,displayName"
        while url:
            r = requests.get(url, headers=self._headers(), timeout=30)
            r.raise_for_status()
            data = r.json()
            for f in data.get("value", []):
                self._folders[f["displayName"]] = f["id"]
            url = data.get("@odata.nextLink")

    def fetch_inbox(self, limit, only_unread=False):
        # nota: con only_unread no pedimos $orderby (Graph lo rechaza combinado)
        if only_unread:
            url = (f"{GRAPH}/me/mailFolders/inbox/messages?$top=50"
                   "&$filter=isRead eq false"
                   "&$select=id,subject,from,receivedDateTime,bodyPreview,internetMessageId")
        else:
            url = (f"{GRAPH}/me/mailFolders/inbox/messages?$top=50"
                   "&$orderby=receivedDateTime desc"
                   "&$select=id,subject,from,receivedDateTime,bodyPreview,internetMessageId")
        out = []
        while url and len(out) < limit:
            r = requests.get(url, headers=self._headers(), timeout=30)
            r.raise_for_status()
            data = r.json()
            for m in data.get("value", []):
                frm = ((m.get("from") or {}).get("emailAddress")) or {}
                out.append({
                    "id": m["id"],
                    "from_email": (frm.get("address") or "").lower(),
                    "from_name": frm.get("name") or "",
                    "subject": m.get("subject") or "",
                    "snippet": m.get("bodyPreview") or "",
                    "message_id": m.get("internetMessageId") or m["id"],
                })
                if len(out) >= limit:
                    break
            url = data.get("@odata.nextLink")
        return out

    def ensure_folder(self, name):
        if name in self._folders:
            return self._folders[name]
        r = requests.post(f"{GRAPH}/me/mailFolders", headers=self._headers(),
                          json={"displayName": name}, timeout=30)
        r.raise_for_status()
        fid = r.json()["id"]
        self._folders[name] = fid
        return fid

    def apply(self, msg_id, category, archive):
        mid = quote(msg_id, safe="")
        if archive:
            dest = self.ensure_folder(category)
            r = requests.post(f"{GRAPH}/me/messages/{mid}/move",
                              headers=self._headers(),
                              json={"destinationId": dest}, timeout=30)
            r.raise_for_status()
        else:
            # se queda en el inbox: solo le pone una categoría/etiqueta visible
            r = requests.patch(f"{GRAPH}/me/messages/{mid}",
                               headers=self._headers(),
                               json={"categories": [category]}, timeout=30)
            r.raise_for_status()

    def commit(self):
        pass   # Graph aplica cada acción al instante

    def logout(self):
        pass
