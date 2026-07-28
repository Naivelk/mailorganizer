# ============================================================================
#  CLASIFICADOR HÍBRIDO  —  Capa 1: reglas (gratis) · Capa 2: IA Groq (dudosos)
# ============================================================================
import ai_classify
import config as cfg


def _match_rules(msg):
    frm = msg.get("from_email", "").lower()
    subj = msg.get("subject", "").lower()
    for rule in cfg.RULES:
        if any(k in frm for k in rule.get("from_contains", [])):
            return rule["category"]
        if any(k in subj for k in rule.get("subject_contains", [])):
            return rule["category"]
    return None


def classify(messages, get_body, api_key):
    """Asigna 'category' (y 'by') a cada mensaje.
    get_body(msg)->str: obtiene el cuerpo para la IA (Gmail); None si ya hay snippet.
    """
    undecided = []
    for m in messages:
        cat = _match_rules(m)
        if cat:
            m["category"], m["by"] = cat, "regla"
        else:
            undecided.append(m)

    if cfg.AI_ENABLED and api_key and undecided:
        batch = undecided[:cfg.AI_MAX_PER_RUN]
        payload = []
        for idx, m in enumerate(batch):
            snippet = m.get("snippet")
            if snippet is None and get_body:
                snippet = get_body(m)
            payload.append({"i": idx,
                            "from_email": m.get("from_email", ""),
                            "subject": m.get("subject", ""),
                            "snippet": snippet or ""})
        result = ai_classify.classify_with_ai(
            payload, cfg.CATEGORIES, cfg.GROQ_MODEL, api_key)
        for idx, m in enumerate(batch):
            if idx in result:
                m["category"], m["by"] = result[idx], "IA"

    # lo que la IA no alcanzó a ver (tope o IA off) -> categoría por defecto
    for m in undecided:
        if "category" not in m:
            m["category"], m["by"] = cfg.DEFAULT_CATEGORY, "default"
    return messages
