# ============================================================================
#  CLASIFICACIÓN CON IA (Groq)  —  decide la categoría de los correos dudosos.
# ============================================================================
#  Usa la API de Groq (compatible con OpenAI), gratis con tu GROQ_API_KEY.
#  Si no hay key o algo falla, devuelve {} y el correo cae en la categoría
#  por defecto (nunca se pierde ni se borra nada).
# ============================================================================
import json
import time

import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _post_retry(payload, headers, timeout, tries=4):
    """Groq (plan gratis) tira 429 seguido. Reintenta respetando su Retry-After.
    Tope de 30s por espera: lo que no pase igual cae en 'Sin clasificar', que
    no se purga, así que no vale la pena quemar 5 minutos en un solo lote."""
    r, wait = None, 5.0
    for n in range(1, tries + 1):
        r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=timeout)
        if r.status_code != 429:
            return r
        try:
            wait = float(r.headers.get("retry-after") or wait)
        except ValueError:
            pass
        wait = min(max(wait, 2.0), 30.0)
        print(f"[ai] 429: espero {wait:.0f}s (intento {n}/{tries})")
        time.sleep(wait)
        wait *= 2
    return r


def classify_with_ai(emails, categories, model, api_key, timeout=60):
    """emails: [{'i','from_email','subject','snippet'}] -> devuelve {i: categoria}."""
    if not api_key or not emails:
        return {}

    listing = [{
        "i": e["i"],
        "from": e.get("from_email", ""),
        "subject": (e.get("subject", "") or "")[:120],
        "preview": (e.get("snippet", "") or "")[:200],
    } for e in emails]

    cats = ", ".join(categories)
    system = ("Eres un asistente que organiza el correo de un usuario. Clasificas cada "
              "correo en EXACTAMENTE una de las categorías dadas. Respondes SOLO con JSON válido.")
    user = (
        f"CATEGORÍAS VÁLIDAS (usa el texto EXACTO): {cats}\n\n"
        f"CORREOS (JSON):\n{json.dumps(listing, ensure_ascii=False)}\n\n"
        "El usuario es Kevin: ingeniero de software full-stack en Neiva (Colombia), "
        "buscando empleo activamente, y encargado del marketing de la aseguradora "
        "Intercoast.\n\n"
        "Guía de categorías:\n"
        "- 'Importante': requiere su atención o respuesta pronto. Personas reales "
        "escribiéndole, avisos de seguridad de sus cuentas, temas legales, bancarios "
        "o médicos, plazos y vencimientos. Ante la duda entre Importante y Personal, "
        "elige Importante: es peor esconderle algo urgente que dejarle un correo de más.\n"
        "- 'Clientes': clientes o prospectos de seguros.\n"
        "- 'Trabajo Intercoast': temas de la aseguradora Intercoast.\n"
        "- 'Empleos': vacantes, alertas de empleo, respuestas a postulaciones, "
        "reclutadores, entrevistas. (Le interesan MUCHO: no las mezcles con promos.)\n"
        "- 'Facturas y pagos': cobros, recibos, bancos, comprobantes, suscripciones.\n"
        "- 'Sospechoso': SOLO fraude real — estafas, chantajes, premios falsos, "
        "remitentes que suplantan a una empresa para robar datos o dinero.\n"
        "  NO marques aquí (son errores que ya cometiste):\n"
        "  · Marketing agresivo de marcas reales (Rappi, Temu, Lenovo, tiendas, "
        "bancos): por molesto que sea, va en 'Newsletters y Promos'.\n"
        "  · Avisos de seguridad legítimos de plataformas conocidas (Meta, Google, "
        "Microsoft): 'iniciaste sesión en un dispositivo nuevo', 'alerta de "
        "seguridad', códigos. Esos van en 'Importante' — marcarlos como phishing "
        "hace que el usuario se pierda un aviso real de que le hackearon la cuenta.\n"
        "  Ante la duda, NO es Sospechoso.\n"
        "- 'Newsletters y Promos': boletines, marketing, promociones legítimas.\n"
        "- 'Redes sociales': notificaciones de redes sociales o apps.\n"
        "- 'Personal': todo lo demás.\n\n"
        "Para CADA correo devuelve {\"i\": índice, \"cat\": \"<una categoría EXACTA de la lista>\"}.\n"
        'Responde EXACTAMENTE con este formato: {"results":[{"i":0,"cat":"Personal"}]}'
    )

    try:
        r = _post_retry(
            {
                "model": model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            {"Authorization": f"Bearer {api_key}",
             "Content-Type": "application/json"},
            timeout,
        )
        r.raise_for_status()
        data = json.loads(r.json()["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"[ai] error: {e}")
        return {}

    valid = set(categories)
    out = {}
    for item in data.get("results", []):
        try:
            cat = str(item.get("cat", "")).strip()
            if cat in valid:
                out[int(item["i"])] = cat
        except (ValueError, KeyError, TypeError):
            continue
    return out
