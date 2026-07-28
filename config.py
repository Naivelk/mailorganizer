# ============================================================================
#  ORGANIZADOR DE CORREO  —  CONFIGURACIÓN (ajusta todo aquí)
# ============================================================================
#  Kevin Quimbaya · organiza Gmail + Outlook con reglas + IA (Groq) y te manda
#  un resumen por Telegram. Corre en GitHub Actions. Modo: SOLO ORGANIZAR
#  (mueve/etiqueta y archiva; NUNCA borra nada).
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
#  "Importante" se queda en el inbox; el resto se archiva a su carpeta.
CATEGORIES = [
    "Importante",
    "Trabajo Intercoast",
    "Clientes",
    "Facturas y pagos",
    "Newsletters y Promos",
    "Redes sociales",
    "Personal",
]
DEFAULT_CATEGORY    = "Personal"        # si ni las reglas ni la IA deciden
KEEP_IN_INBOX       = ["Importante"]    # estas NO se archivan (quedan visibles)
ARCHIVE_AFTER_LABEL = True              # el resto sale del inbox hacia su carpeta

# --- Capa 1: Reglas (gratis, instantáneas) ---------------------------------
#  Se evalúan EN ORDEN; el primer match gana. Busca texto (en minúsculas) en
#  el remitente (from) y en el asunto (subject). Agrega/quita lo que quieras.
#  Clientes / Importante / Personal normalmente los decide la IA (capa 2).
RULES = [
    {"category": "Redes sociales",
     "from_contains": ["facebookmail", "facebook.com", "instagram", "linkedin.com",
                        "twitter.com", "x.com", "tiktok", "youtube.com", "pinterest",
                        "reddit", "discord", "notification", "notifications"],
     "subject_contains": []},

    {"category": "Facturas y pagos",
     "from_contains": ["paypal", "stripe", "bancolombia", "nequi", "daviplata",
                       "davivienda", "facturacion", "facturaelectronica", "billing"],
     "subject_contains": ["factura", "invoice", "recibo", "pago", "payment",
                          "comprobante", "extracto", "estado de cuenta"]},

    {"category": "Newsletters y Promos",
     "from_contains": ["newsletter", "noreply", "no-reply", "no_reply", "mailchimp",
                       "sendgrid", "substack", "medium.com", "marketing"],
     "subject_contains": ["oferta", "descuento", "promo", "sale", "% off", "cupon",
                          "boletin", "newsletter", "unsubscribe", "black friday"]},

    {"category": "Trabajo Intercoast",
     "from_contains": ["intercoast"],
     "subject_contains": ["intercoast", "poliza", "cotizacion", "seguro", "vin", "quote"]},
]

# --- Capa 2: IA (Groq — gratis, reusa tu GROQ_API_KEY) ---------------------
AI_ENABLED     = True
GROQ_MODEL     = "llama-3.3-70b-versatile"   # si Groq lo deprecia, cámbialo aquí
AI_MAX_PER_RUN = 40      # tope de correos que pasan a la IA por corrida
AI_BODY_CHARS  = 600     # cuánto del cuerpo leer para clasificar

# --- Comportamiento --------------------------------------------------------
MAX_FETCH   = 80         # correos recientes del inbox a revisar por cuenta/corrida
MAX_SEEN    = 5000       # ids recordados por cuenta para no reprocesar
ONLY_UNREAD = False      # True = solo no leídos; False = organiza todo el inbox
MARK_SEEN   = False      # False = NO marca como leído al organizar (no te oculta nada)
