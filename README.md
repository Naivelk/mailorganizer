# 🧹 Organizador de Correo

Bot que **organiza tu correo automáticamente** (Gmail + Outlook/Hotmail), corriendo
solo en **GitHub Actions** una vez al día, y te manda un **resumen por Telegram**.
Así entras al día siguiente y tienes la bandeja ordenada.

- **Cuentas:** `naivelk@gmail.com`, `kevinquimbyto@hotmail.com`, `naivelk@outlook.es`
- **Modo:** SOLO ORGANIZAR — mueve/etiqueta y archiva. **Nunca borra nada.**
- **Cerebro:** híbrido → reglas (gratis) + IA (Groq, gratis) para los correos dudosos.

## ¿Cómo funciona?

1. Lee los correos recientes del inbox de cada cuenta.
2. **Capa 1 (reglas):** clasifica lo obvio por remitente/asunto (redes, promos, bancos…).
3. **Capa 2 (IA):** los dudosos se los pasa a Groq, que decide la categoría leyendo el contenido.
4. Cada correo se **etiqueta/mueve** a su carpeta. Lo marcado `Importante` se queda en el inbox; el resto se archiva.
5. Te llega un **resumen por Telegram** con cuántos correos movió y a dónde.

Las categorías, reglas y horario se ajustan en [`config.py`](config.py).

---

## 🔧 Setup (una sola vez)

> Tú creas cada *secret* directamente en GitHub — así tus credenciales nunca pasan por otro lado.

### Secrets que vas a necesitar
| Secret | Qué es |
|---|---|
| `GMAIL_APP_PASSWORD` | Contraseña de aplicación de Gmail |
| `MS_CLIENT_ID` | Application (client) ID de la app de Azure (no es secreto, pero va aquí) |
| `MS_REFRESH_TOKEN_1` | Refresh token de `kevinquimbyto@hotmail.com` |
| `MS_REFRESH_TOKEN_2` | Refresh token de `naivelk@outlook.es` |
| `GROQ_API_KEY` | Tu key de Groq (la misma del bot de empleos) |
| `TELEGRAM_BOT_TOKEN` | Token de tu bot (el mismo de tus otros bots) |
| `TELEGRAM_CHAT_ID` | Tu chat id de Telegram |

---

### 1) Gmail — App Password
1. Activa la **verificación en 2 pasos**: https://myaccount.google.com/security
2. Genera una **contraseña de aplicación**: https://myaccount.google.com/apppasswords
   → nómbrala "mail-organizer" → copia los **16 caracteres** (sin espacios).
3. Activa **IMAP** en Gmail: ⚙️ → *Ver toda la configuración* → *Reenvío y correo POP/IMAP* → **Habilitar IMAP** → Guardar.
4. Guarda la contraseña como secret **`GMAIL_APP_PASSWORD`**.

### 2) Microsoft — registrar app + autorizar las 2 cuentas
1. Entra a https://portal.azure.com → busca **App registrations** → **New registration**.
   - **Name:** `Mail Organizer`
   - **Supported account types:** *Accounts in any organizational directory **and personal Microsoft accounts*** ✅ (importante para hotmail/outlook)
   - **Redirect URI:** déjalo vacío → **Register**.
2. Copia el **Application (client) ID** → guárdalo como secret **`MS_CLIENT_ID`**.
3. Menú **Authentication** → baja a *Advanced settings* → **Allow public client flows** → **Yes** → **Save**.
4. Menú **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated permissions** → agrega:
   `Mail.ReadWrite`, `offline_access`, `User.Read` → **Add permissions**.
5. Ejecuta el helper (click derecho → *Ejecutar con PowerShell*):
   ```powershell
   powershell -ExecutionPolicy Bypass -File ms_auth.ps1
   ```
   - Pega el **client ID**, abre el link, ingresa el código y **autoriza con `kevinquimbyto@hotmail.com`**.
   - Copia el refresh token → secret **`MS_REFRESH_TOKEN_1`**.
6. **Corre `ms_auth.ps1` otra vez** y autoriza con **`naivelk@outlook.es`**.
   - Copia el refresh token → secret **`MS_REFRESH_TOKEN_2`**.

### 3) Groq (IA) — reusa tu key
Usa la **misma** `GROQ_API_KEY` del bot de empleos (o saca una nueva en
https://console.groq.com/keys) → secret **`GROQ_API_KEY`**.

### 4) Telegram — reusa tu bot
Usa el **mismo** `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` de tus otros bots.

### 5) Subir a GitHub y activar
1. Crea un repo **privado** `mail-organizer` en GitHub (sin README).
2. Desde esta carpeta:
   ```bash
   git init
   git add .
   git commit -m "feat: organizador de correo Gmail + Outlook"
   git branch -M main
   git remote add origin https://github.com/Naivelk/mail-organizer.git
   git push -u origin main
   ```
3. En el repo → **Settings → Secrets and variables → Actions** → agrega los 7 secrets de la tabla.
4. Pestaña **Actions** → activa los workflows si te lo pide.
5. Corre una prueba: **Actions → Organizador de Correo → Run workflow**. En 1–2 min te llega el resumen a Telegram.

---

## ⚙️ Ajustes rápidos ([`config.py`](config.py))
- **Categorías:** edita `CATEGORIES` (usa nombres planos y sin tildes).
- **Reglas:** agrega remitentes/palabras a `RULES` para no gastar IA en lo obvio.
- **Horario:** cambia el `cron` en [`.github/workflows/organize.yml`](.github/workflows/organize.yml).
  `'0 10 * * *'` = 5:00 AM Colombia. Para 2 veces al día: `'0 10,22 * * *'`.
- **Cuánto revisa:** `MAX_FETCH` (correos por corrida). Súbelo para limpiar backlog más rápido.

## 🛟 Notas
- **No borra nada.** En Gmail "archivar" solo quita la etiqueta *Inbox*; el correo queda bajo su etiqueta y en *Todos*. En Outlook mueve a carpeta. Todo es reversible.
- Si un token de Microsoft deja de funcionar (cambio de contraseña, mucho tiempo sin correr), vuelve a correr `ms_auth.ps1` y actualiza el secret.
- El estado (`state.json`) se guarda solo en el repo para no reprocesar correos.
- Si algo falla, te llega un aviso por Telegram con el error.
