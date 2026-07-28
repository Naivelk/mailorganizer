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
#  Cuando la IA NO pudo opinar (rate limit de Groq, error de red), el correo
#  cae aquí en vez de en Personal. Es a propósito: "Sin clasificar" está en
#  PURGE_NEVER, así que jamás se borra algo que nadie llegó a mirar.
UNSORTED_CATEGORY   = "Sin clasificar"
#  Vacío a propósito: en la bandeja SOLO se quedan los blindados de la Capa 0
#  (códigos, alertas de seguridad, avisos legales). Lo que la IA juzgue
#  "Importante" va a su carpeta: si no, se acumulaban ~70 y la bandeja nunca
#  quedaba limpia. Para volver atrás, pon ["Importante"].
KEEP_IN_INBOX       = []
ARCHIVE_AFTER_LABEL = True              # el resto sale del inbox hacia su carpeta

# --- Capa 0: BLINDAJE  (se evalúa ANTES que todo) --------------------------
#  Códigos de acceso, alertas de seguridad y avisos legales/urgentes.
#  Se marcan Importante y NUNCA se archivan: si el bot te esconde un OTP, te
#  quedas sin poder entrar a una cuenta.
PROTECT_CATEGORY = "Importante"
PROTECT_SUBJECT = [
    # códigos / acceso   (ojo: "code" a secas cazaría con "promo code")
    "codigo", "código", "otp", "pin", "one-time", "un solo uso",
    # "your code" salía sobrando: cazaba con promos de claves de juegos (G2A)
    "verification code", "security code", "access code", "login code",
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
                          "buscando talento", "aplica ahora",
                          # en Colombia "convocatoria" suele ser oferta de
                          # empleo o proceso público: iba camino a la papelera
                          "convocatoria", "seleccion de personal",
                          "selección de personal", "proceso de seleccion"]},

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
     # Los de más volumen van explícitos para que ni lleguen a la IA
     # (salieron de tu propio reporte de desuscripción).
     # PRA Group: cobro de cartera real (deuda de la mamá de Kevin) pero
     # escriben a diario con ofertas de descuento. Regla fija para que no
     # oscilen entre Importante y Sospechoso como venía pasando.
     # OJO: la Capa 0 corre ANTES que esto, así que si algún día mandan un
     # embargo, demanda o citación, eso igual salta a Importante.
     "from_contains": ["pragroup", "pra-group", "pracolombia",
                       "newsletter", "noreply", "no-reply", "no_reply", "mailchimp",
                       "sendgrid", "substack", "medium.com", "marketing", "promo",
                       # juegos / entretenimiento
                       "e.ea.com", "epicgames", "nba2k", "ubisoft", "playstation",
                       "steampowered", "riotgames", "xbox", "nintendo", "g2a",
                       "realmadrid", "spotify", "netflix", "disney", "primevideo",
                       "twitch.tv", "rockstargames", "battle.net", "gog.com"],
     "subject_contains": ["oferta", "descuento", "promo", "sale", "% off", "cupon",
                          "cupón", "boletin", "boletín", "newsletter",
                          "unsubscribe", "black friday", "ultimas horas",
                          "últimas horas",
                          "condonacion", "condonación"]},   # ofertas de cartera
]

# --- Capa 2: IA (Groq — gratis, reusa tu GROQ_API_KEY) ---------------------
AI_ENABLED      = True
#  Clasificar en 9 cajones a partir de remitente+asunto es tarea fácil: el
#  modelo chico la hace igual de bien y tiene un límite de tokens/minuto MUY
#  superior. Con el 70b la corrida se iba en esperas por 429 (18 min).
#  Si notas que falla clasificando phishing, vuelve a "llama-3.3-70b-versatile".
GROQ_MODEL      = "llama-3.1-8b-instant"
#  Groq (plan gratis) limita por TOKENS por minuto, no solo por peticiones:
#  lotes de 25 con 600 chars de cuerpo lo reventaban y la mitad de los lotes
#  volvía 429. Lotes más chicos + menos texto + pausa = pasa todo.
AI_BATCH_SIZE   = 15     # correos por llamada a la IA (procesa por lotes)
AI_MAX_BATCHES  = 60     # tope de llamadas por corrida (freno de seguridad)
AI_BODY_CHARS   = 350    # cuánto del cuerpo leer para clasificar
AI_PAUSE        = 2      # segundos entre lotes, para no atropellar la API

# --- Comportamiento --------------------------------------------------------
MAX_FETCH   = 60         # correos por cuenta en la corrida AUTOMÁTICA diaria.
                         # 60 cubre de sobra lo que entra en un día y aún le
                         # come al backlog. (Estaba en 15 para la 1ª prueba.)
                         # Para vaciar el backlog no edites esto: usa el campo
                         # "correos por cuenta" al lanzar el workflow a mano.
MAX_SEEN    = 8000       # ids recordados por cuenta para no reprocesar
ONLY_UNREAD = False      # True = solo no leídos; False = organiza todo el inbox
MARK_SEEN   = False      # False = NO marca como leído al organizar (no te oculta nada)

# --- Purga: manda a la PAPELERA lo viejo que ya no sirve --------------------
#  NUNCA borra de forma permanente: manda a la papelera, que Gmail y Outlook
#  vacían solos a los 30 días. El espacio se libera igual, pero te queda un mes
#  para rescatar cualquier cosa que se haya ido por error.
PURGE_ENABLED     = True    # el barrido corre...
PURGE_DRY_RUN     = False   # ...y ahora SÍ manda a la papelera. Pon True para
                            # volver al simulacro (reporta sin tocar nada).
PURGE_MAX_PER_RUN = 300     # tope por cuenta y corrida (freno de seguridad)

#  Antigüedad a partir de la cual un correo se va a la papelera.
#  Cambia SOLO este número para hacerlo más o menos agresivo.
PURGE_DAYS = 70

#  Por categoría. require_read=False -> lo tumba lo hayas leído o no.
#  (Si algún día quieres ser más suave con una, ponle require_read=True y
#   un "days_unread" mayor: los no leídos esperarían ese tiempo extra.)
PURGE_POLICIES = {
    "Newsletters y Promos": {"days": PURGE_DAYS, "require_read": False},
    "Sospechoso":           {"days": PURGE_DAYS, "require_read": False},
    "Redes sociales":       {"days": PURGE_DAYS, "require_read": False},
    "Personal":             {"days": PURGE_DAYS, "require_read": False},
}

#  Estas NUNCA se tocan, pase lo que pase (respaldo legal, trabajo, empleo).
PURGE_NEVER = ["Importante", "Facturas y pagos", "Empleos", "Clientes",
               "Trabajo Intercoast", UNSORTED_CATEGORY]
PURGE_KEEP_FLAGGED = True   # jamás tumba lo que marcaste con estrella/bandera

# --- Reporte de correos pesados (lo que de verdad libera GB) ---------------
HEAVY_REPORT = True
HEAVY_MIN_MB = 5      # reporta correos de más de N MB
HEAVY_TOP    = 10     # cuántos mostrarte

# --- Reporte de desuscripción (NO se desuscribe solo) ----------------------
#  Solo detecta y te reporta quién te spamea y de quién se puede dar de baja
#  con un clic. La desuscripción real se activa aparte, con tu aprobación.
UNSUB_REPORT = True
UNSUB_TOP    = 8         # cuántos remitentes mostrarte en el resumen
