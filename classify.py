# ============================================================================
#  CLASIFICADOR HÍBRIDO
#    Capa 0: blindaje (códigos, seguridad, legal) — nunca se archivan
#    Capa 1: reglas por remitente/asunto (gratis)
#    Capa 2: IA Groq por lotes (los dudosos)
# ============================================================================
import re
import time

import ai_classify
import config as cfg

# Los términos de blindaje se buscan como PALABRA, no como subcadena: si no,
# "pin" caza con "shopping" y "code" con "barcode", y medio boletín de compras
# acabaría marcado como Importante. El límite va solo al inicio, para que
# "codigo" siga cazando con "codigos".
_PROTECT_RE = re.compile(
    "|".join(r"\b" + re.escape(k) for k in cfg.PROTECT_SUBJECT), re.IGNORECASE)


def _is_protected(msg):
    """True si es un código de acceso, alerta de seguridad o aviso legal."""
    return bool(_PROTECT_RE.search(msg.get("subject", "")))


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
    """Asigna 'category', 'by' y 'protected' a cada mensaje.
    get_body(msg)->str: obtiene el cuerpo para la IA (Gmail); None si ya hay snippet.
    """
    undecided = []
    for m in messages:
        if _is_protected(m):
            m["category"], m["by"], m["protected"] = cfg.PROTECT_CATEGORY, "blindaje", True
            continue
        cat = _match_rules(m)
        if cat:
            m["category"], m["by"] = cat, "regla"
        else:
            undecided.append(m)

    # --- Capa 2: la IA procesa POR LOTES (no trunca: si hay 300 dudosos,
    #     hace 12 llamadas de 25 en vez de clasificar solo los primeros) ----
    ai_ran = cfg.AI_ENABLED and api_key and undecided
    if ai_ran:
        size = max(1, cfg.AI_BATCH_SIZE)
        batches = [undecided[i:i + size] for i in range(0, len(undecided), size)]
        for n, batch in enumerate(batches[:cfg.AI_MAX_BATCHES], 1):
            if n > 1 and cfg.AI_PAUSE:
                time.sleep(cfg.AI_PAUSE)   # no atropellamos el límite de Groq
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
            print(f"[ai] lote {n}/{min(len(batches), cfg.AI_MAX_BATCHES)}: "
                  f"{len(result)}/{len(batch)} clasificados")
            for idx, m in enumerate(batch):
                if idx in result:
                    m["category"], m["by"] = result[idx], "IA"

    # Lo que la IA no resolvió. Si la IA sí corrió pero este correo se quedó
    # afuera (429, error, tope de lotes), va a "Sin clasificar": nunca se
    # purga, porque nadie lo miró. Si la IA está apagada, va al default.
    fallback = cfg.UNSORTED_CATEGORY if ai_ran else cfg.DEFAULT_CATEGORY
    pending = 0
    for m in undecided:
        if "category" not in m:
            m["category"], m["by"] = fallback, "sin-ia"
            pending += 1
    if pending:
        print(f"[ai] {pending} correo(s) sin clasificar -> '{fallback}'")
    return messages
