# ============================================================================
#  ORGANIZADOR DE CORREO  —  CONFIGURACIÓN (ajusta todo aquí)
# ============================================================================
#  Kevin Quimbaya · organiza Gmail + Outlook con reglas + IA (Groq) y te manda
#  un resumen por Telegram. Corre en GitHub Actions. Modo: SOLO ORGANIZAR
#  (mueve/etiqueta y archiva; NUNCA borra ni se desuscribe por su cuenta).
# ============================================================================

# --- Cuentas ---------------------------------------------------------------
GMAIL_ENABLED = True
GMAIL_ADDRESS = "naivelk@gmail.com"           # usa el secret GMAIL_APP_PASSWORD

# Outlook/Hotmail (Microsoft Graph). El client id es público (no secreto).
OUTLOOK_ENABLED = True
OUTLOOK_ACCOUNTS = [
    {"name": "hotmail",    "address": "kevinquimbyto@hotmail.com", "token_env": "MS_REFRESH_TOKEN_1"},
    {"name": "outlook-es", "address": "naivelk@outlook.es",        "token_env": "MS_REFRESH_TOKEN_2"},
]

# --- Categorías (carpetas/etiquetas destino) -------------------------------
#  Nombres planos y SIN tildes: así funcionan igual en Gmail y en Outlook.
CATEGORIES = [
    "Importante",
    "Trabajo Intercoast",
    "Clientes",
    "Empleos",
    "Facturas y pagos",
    "Sospechoso",
    "Newsletters y Promos",
    "Redes sociales",
    "Personal",
]
DEFAULT_CATEGORY    = "Personal"        # si ni las reglas ni la IA deciden
KEEP_IN_INBOX       = ["Importante"]    # estas NO se archivan (quedan visibles)
ARCHIVE_AFTER_LABEL = True              # el resto sale del inbox hacia su carpeta

# --- Capa 0: BLINDAJE  (se evalúa ANTES que todo) --------------------------
#  Códigos de acceso, alertas de seguridad y avisos legales/urgentes.
#  Se marcan Importante y NUNCA se archivan: si el bot te esconde un OTP, te
#  quedas sin poder entrar a una cuenta.
PROTECT_CATEGORY = "Importante"
PROTECT_SUBJECT = [
    # códigos / acceso   (ojo: "code" a secas cazaría con "promo code")
    "codigo", "código", "otp", "pin", "one-time", "un solo uso",
    "verification code", "security code", "access code", "your code",
    "verification", "verificacion", "verificación", "2fa", "two-factor",
    "inicio de sesion", "inicio de sesión", "sign-in", "sign in", "login",
    "was this you", "restablecer", "reset password", "recuperacion", "recuperación",
    # seguridad
    "alerta de seguridad", "security alert", "actividad sospechosa",
    "suspicious activity", "unusual activity", "contrasena expuesta",
    "contraseña expuesta", "data breach",
    # legal / urgente
    "embargo", "demanda", "notificacion judicial", "notificación judicial",
    "cobro juridico", "cobro jurídico", "requerimiento", "citacion", "citación",
]

# --- Capa 1: Reglas (gratis, instantáneas) ---------------------------------
#  Se evalúan EN ORDEN; el primer match gana. Busca texto (en minúsculas) en
#  el remitente (from) y en el asunto (subject).
#  Ojo con el orden: lo específico va ANTES que lo genérico.
RULES = [
    {"category": "Trabajo Intercoast",
     "from_contains": ["intercoast"],
     "subject_contains": ["intercoast", "poliza", "póliza", "cotizacion",
                          "cotización", "vin quote"]},

    # Empleos ANTES que Redes sociales: las alertas de LinkedIn Jobs si no
    # caerían como notificación de red social.
    {"category": "Empleos",
     "from_contains": ["computrabajo", "elempleo", "magneto365", "magneto",
                       "bumeran", "occ.com", "torre.co", "getonbrd", "indeed",
                       "glassdoor", "remoteok", "weworkremotely", "arbeitnow",
                       "jobicy", "himalayas", "remotive",
                       "jobs-noreply@linkedin", "jobalerts-noreply@linkedin",
                       "jobs-listings@linkedin"],
     "subject_contains": ["vacante", "oferta laboral", "hoja de vida",
                          "postulacion", "postulación", "entrevista",
                          "job alert", "new jobs", "empleos para ti",
                          "buscando talento", "aplica ahora"]},

    {"category": "Facturas y pagos",
     "from_contains": ["paypal", "stripe", "bancolombia", "nequi", "daviplata",
                       "davivienda", "bbva", "scotiabank", "facturacion",
                       "facturaelectronica", "billing", "payments"],
     "subject_contains": ["factura", "invoice", "recibo", "pago", "payment",
                          "comprobante", "extracto", "estado de cuenta",
                          "transaccion", "transacción", "purchase", "compra"]},

    {"category": "Redes sociales",
     "from_contains": ["facebookmail", "facebook.com", "instagram", "linkedin.com",
                       "twitter.com", "x.com", "tiktok", "youtube.com", "pinterest",
                       "reddit", "discord", "twitch", "snapchat", "threads"],
     "subject_contains": []},

    {"category": "Newsletters y Promos",
     "from_contains": ["newsletter", "noreply", "no-reply", "no_reply", "mailchimp",
                       "sendgrid", "substack", "medium.com", "marketing", "promo"],
     "subject_contains": ["oferta", "descuento", "promo", "sale", "% off", "cupon",
                          "cupón", "boletin", "boletín", "newsletter",
                          "unsubscribe", "black friday", "ultimas horas",
                          "últimas horas"]},
]

# --- Capa 2: IA (Groq — gratis, reusa tu GROQ_API_KEY) ---------------------
AI_ENABLED      = True
GROQ_MODEL      = "llama-3.3-70b-versatile"   # si Groq lo deprecia, cámbialo aquí
AI_BATCH_SIZE   = 25     # correos por llamada a la IA (procesa por lotes)
AI_MAX_BATCHES  = 40     # tope de llamadas por corrida (freno de seguridad)
AI_BODY_CHARS   = 600    # cuánto del cuerpo leer para clasificar

# --- Comportamiento --------------------------------------------------------
MAX_FETCH   = 15         # correos recientes del inbox a revisar por cuenta/corrida
                         # (para vaciar el backlog no edites esto: usa el campo
                         #  "correos por cuenta" al lanzar el workflow a mano)
MAX_SEEN    = 8000       # ids recordados por cuenta para no reprocesar
ONLY_UNREAD = False      # True = solo no leídos; False = organiza todo el inbox
MARK_SEEN   = False      # False = NO marca como leído al organizar (no te oculta nada)

# --- Reporte de desuscripción (NO se desuscribe solo) ----------------------
#  Solo detecta y te reporta quién te spamea y de quién se puede dar de baja
#  con un clic. La desuscripción real se activa aparte, con tu aprobación.
UNSUB_REPORT = True
UNSUB_TOP    = 8         # cuántos remitentes mostrarte en el resumen
