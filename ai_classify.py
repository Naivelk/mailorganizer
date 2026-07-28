# ============================================================================
#  CLASIFICACIÓN CON IA (Groq)  —  decide la categoría de los correos dudosos.
# ============================================================================
#  Usa la API de Groq (compatible con OpenAI), gratis con tu GROQ_API_KEY.
#  Si no hay key o algo falla, devuelve {} y el correo cae en la categoría
#  por defecto (nunca se pierde ni se borra nada).
# ============================================================================
import json

import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def classify_with_ai(emails, categories, model, api_key, timeout=60):
    """emails: [{'i','from_email','subject','snippet'}] -> devuelve {i: categoria}."""
    if not api_key or not emails:
        return {}

    listing = [{
        "i": e["i"],
        "from": e.get("from_email", ""),
        "subject": (e.get("subject", "") or "")[:160],
        "preview": (e.get("snippet", "") or "")[:400],
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
        "- 'Sospechoso': phishing, estafas, chantajes, premios falsos, remitentes que "
        "suplantan a una empresa, links o adjuntos raros, urgencia artificial para que "
        "entregue datos o dinero. Marca aquí SOLO si de verdad parece un intento de "
        "fraude; el marketing molesto pero legítimo va en Newsletters y Promos.\n"
        "- 'Newsletters y Promos': boletines, marketing, promociones legítimas.\n"
        "- 'Redes sociales': notificaciones de redes sociales o apps.\n"
        "- 'Personal': todo lo demás.\n\n"
        "Para CADA correo devuelve {\"i\": índice, \"cat\": \"<una categoría EXACTA de la lista>\"}.\n"
        'Responde EXACTAMENTE con este formato: {"results":[{"i":0,"cat":"Personal"}]}'
    )

    try:
        r = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=timeout,
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
