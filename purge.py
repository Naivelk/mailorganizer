# ============================================================================
#  PURGA  —  decide qué correos viejos se van a la PAPELERA
# ============================================================================
#  NUNCA borra de forma permanente: mueve a la papelera, que Gmail y Outlook
#  vacían solos a los ~30 días. Así se libera el espacio igual, pero queda un
#  mes para rescatar lo que se haya ido por error.
#  Arranca en simulacro (cfg.PURGE_DRY_RUN = True): solo reporta.
# ============================================================================
from datetime import datetime, timedelta

import config as cfg

_IMAP_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _imap_date(dt):
    return f"{dt.day:02d}-{_IMAP_MONTHS[dt.month - 1]}-{dt.year}"


def _expired(msg, pol, now):
    """True si este correo ya cumplió su tiempo y puede irse a la papelera."""
    d = msg.get("date")
    if not d:
        return False                 # sin fecha fiable, no lo tocamos
    age = (now - d).days
    if pol.get("require_read") and not msg.get("read"):
        # no lo has abierto: esperamos más antes de tumbarlo
        return age >= pol.get("days_unread", pol["days"])
    return age >= pol["days"]


def run(client, kind):
    """Barre las carpetas purgables. Si no es simulacro, manda a papelera.
    kind: 'gmail' (fechas IMAP) u 'outlook' (fechas ISO)."""
    if not cfg.PURGE_ENABLED:
        return {"by_cat": {}, "samples": [], "total": 0, "trashed": 0}

    now = datetime.utcnow()
    budget = cfg.PURGE_MAX_PER_RUN
    by_cat, samples, trashed = {}, [], 0

    for cat, pol in cfg.PURGE_POLICIES.items():
        if cat in cfg.PURGE_NEVER or budget <= 0:
            continue
        # Consultamos con el corte MÁS LAXO y afinamos después: si los no
        # leídos esperan más días, la búsqueda debe partir del menor.
        days = min(pol["days"], pol.get("days_unread", pol["days"]))
        cut = now - timedelta(days=days)
        cutoff = (_imap_date(cut) if kind == "gmail"
                  else cut.strftime("%Y-%m-%dT%H:%M:%SZ"))
        try:
            found = client.sweep(cat, cutoff, budget, cfg.PURGE_KEEP_FLAGGED)
        except Exception as e:
            print(f"[purga] {cat}: {e}")
            continue

        picked = [m for m in found if _expired(m, pol, now)][:budget]
        if not picked:
            continue
        by_cat[cat] = len(picked)
        samples.extend((cat, m) for m in picked[:3])
        budget -= len(picked)

        if not cfg.PURGE_DRY_RUN:
            ids = [m.get("uid") or m.get("id") for m in picked]
            trashed += client.trash(ids)

    return {"by_cat": by_cat, "samples": samples[:8],
            "total": sum(by_cat.values()), "trashed": trashed}


def heavy(client):
    """Los correos más pesados: lo que de verdad ocupa tu almacenamiento."""
    if not cfg.HEAVY_REPORT:
        return []
    try:
        return client.heavy(cfg.HEAVY_MIN_MB * 1024 * 1024, cfg.HEAVY_TOP)
    except Exception as e:
        print(f"[pesados] {e}")
        return []
