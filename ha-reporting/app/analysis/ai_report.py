from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


HA_AI_TASK_URL = "http://supervisor/core/api/services/ai_task/generate_data?return_response"
AI_TIMEOUT_SECONDS = 180
AI_MAX_CONTEXT_CHARS = 60000


def _stat_value(stats: dict[str, Any], key: str) -> Any:
    value = stats.get(key)
    if isinstance(value, dict):
        return value.get("value")
    return value


def compact_report_context(result: dict[str, Any]) -> dict[str, Any]:
    """Build a bounded, structured context for AI interpretation.

    Raw samples, previews, provider internals and verification traces are deliberately
    excluded. The model receives only statistics and quality/comparison metadata that
    HA Reporting has already computed.
    """

    output: dict[str, Any] = {
        "report": {
            "name": (result.get("report") or {}).get("name"),
            "period": (result.get("resolved_period") or {}).get("label"),
            "timezone": (result.get("resolved_period") or {}).get("timezone"),
        },
        "summary": result.get("summary") or {},
        "catalogs": [],
        "comparisons": [],
    }

    for catalog in result.get("catalogs") or []:
        cat_out = {"name": catalog.get("name"), "devices": []}
        for device in catalog.get("devices") or []:
            info = device.get("device") or {}
            dev_out = {
                "name": info.get("name"),
                "category": info.get("category"),
                "sources": [],
            }
            for source in device.get("sources") or []:
                analysis = source.get("analysis") or {}
                stats = analysis.get("statistics") or {}
                quality = analysis.get("quality") or {}
                metric = source.get("metric")
                values: dict[str, Any] = {}

                if metric == "power":
                    values = {
                        "max": _stat_value(stats, "max"),
                        "p95": stats.get("p95"),
                        "mean": stats.get("mean"),
                    }
                elif metric == "temperature":
                    values = {
                        "min": _stat_value(stats, "min"),
                        "mean": stats.get("mean"),
                        "max": _stat_value(stats, "max"),
                    }
                elif metric in {"energy_total", "runtime", "cycles"}:
                    values = {
                        "delta": stats.get("delta"),
                        "last": _stat_value(stats, "last"),
                        "resets_detected": stats.get("resets_detected"),
                    }
                else:
                    values = {
                        "first": _stat_value(stats, "first"),
                        "last": _stat_value(stats, "last"),
                        "mean": stats.get("mean"),
                    }

                dev_out["sources"].append(
                    {
                        "name": source.get("sensor_key") or source.get("entity_id"),
                        "metric": metric,
                        "unit": source.get("unit"),
                        "status": source.get("status"),
                        "values": values,
                        "quality": {
                            "period_coverage_percent": quality.get("period_coverage_percent"),
                            "sample_density_percent": quality.get("sample_density_percent"),
                            "density_applicable": quality.get("density_applicable"),
                        },
                        "runtime_verified": bool(source.get("verification")),
                        "warnings": (analysis.get("validation") or {}).get("warnings") or [],
                    }
                )
            cat_out["devices"].append(dev_out)
        output["catalogs"].append(cat_out)

    comparisons = result.get("comparisons") or {}
    for target in comparisons.get("targets") or []:
        target_out = {
            "label": target.get("label"),
            "period": (target.get("resolved_period") or {}).get("label"),
            "summary": target.get("summary") or {},
            "catalogs": [],
        }
        for catalog in target.get("catalogs") or []:
            cat_out = {"name": catalog.get("name"), "devices": []}
            for device in catalog.get("devices") or []:
                dev_out = {"name": device.get("name"), "sources": []}
                for source in device.get("sources") or []:
                    dev_out["sources"].append(
                        {
                            "name": source.get("sensor_key") or source.get("entity_id"),
                            "metric": source.get("metric"),
                            "unit": source.get("unit"),
                            "status": source.get("comparison_status"),
                            "reasons": source.get("reasons") or [],
                            "values": source.get("values") or [],
                        }
                    )
                cat_out["devices"].append(dev_out)
            target_out["catalogs"].append(cat_out)
        output["comparisons"].append(target_out)

    return output


def _extract_service_response(payload: Any) -> tuple[Any, str | None]:
    """Extract ai_task.generate_data response across REST response shapes."""
    if not isinstance(payload, dict):
        raise RuntimeError("Réponse Home Assistant AI Task invalide")

    response = payload.get("service_response", payload)
    if not isinstance(response, dict):
        raise RuntimeError("Réponse AI Task absente")

    if "data" in response:
        return response.get("data"), response.get("conversation_id")

    # Some response-producing services namespace their response under an entity key.
    for value in response.values():
        if isinstance(value, dict) and "data" in value:
            return value.get("data"), value.get("conversation_id")

    raise RuntimeError("AI Task n'a retourné aucune donnée")


def _instructions(context_json: str) -> str:
    return f"""Tu analyses un rapport domotique calculé par HA Reporting.
Réponds directement et brièvement en français, sans afficher de raisonnement interne.
N'invente aucun chiffre et ne recalcule pas les données : utilise exclusivement les statistiques fournies.
Distingue clairement un fait calculé d'une interprétation. Respecte les limites de qualité et de couverture ; une comparaison partielle ou indisponible ne doit jamais être présentée comme complète.
Ignore les identifiants techniques lorsqu'un nom lisible est disponible.

Produis exactement ces trois sections, en texte simple :
SYNTHÈSE
2 à 4 phrases sur les faits principaux de la période.

POINTS D'ATTENTION
0 à 5 puces commençant par "- ". Ne signale que des éléments réellement étayés par les données, y compris les limites de couverture si elles affectent l'interprétation. Écris "- Aucun point d'attention notable." si nécessaire.

RECOMMANDATIONS
0 à 4 puces commençant par "- ". Reste prudent et concret. N'invente pas de diagnostic de panne. Écris "- Aucune recommandation particulière." si nécessaire.

Données structurées validées par HA Reporting :
{context_json}
"""


def analyze_report_with_ai(
    result: dict[str, Any],
    config: dict[str, Any] | None,
    token: str | None = None,
) -> dict[str, Any]:
    config = config or {}
    if not bool(config.get("enabled")):
        return {"enabled": False, "status": "disabled"}

    token = token if token is not None else os.environ.get("SUPERVISOR_TOKEN", "")
    entity_id = str(config.get("entity_id") or "").strip()
    started = time.time()

    base = {
        "enabled": True,
        "status": "error",
        "entity_id": entity_id or None,
        "mode": "no_thinking_expected",
        "mode_control": "ai_task_entity_configuration",
        "started_at_epoch": started,
    }

    if not token:
        return {
            **base,
            "finished_at_epoch": time.time(),
            "error": "SUPERVISOR_TOKEN indisponible pour appeler AI Task",
        }

    try:
        context = compact_report_context(result)
        context_json = json.dumps(context, ensure_ascii=False, separators=(",", ":"))
        if len(context_json) > AI_MAX_CONTEXT_CHARS:
            raise RuntimeError(
                f"Contexte IA trop volumineux ({len(context_json)} caractères, limite {AI_MAX_CONTEXT_CHARS})"
            )

        service_data: dict[str, Any] = {
            "task_name": f"HA Reporting · {(result.get('report') or {}).get('name') or 'rapport'}",
            "instructions": _instructions(context_json),
        }
        if entity_id:
            service_data["entity_id"] = entity_id

        body = json.dumps(service_data, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            HA_AI_TASK_URL,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=AI_TIMEOUT_SECONDS) as response:
            response_payload = json.loads(response.read() or b"{}")

        data, conversation_id = _extract_service_response(response_payload)
        if isinstance(data, (dict, list)):
            text = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            text = str(data or "").strip()
        if not text:
            raise RuntimeError("AI Task a retourné un texte vide")

        finished = time.time()
        return {
            **base,
            "status": "completed",
            "finished_at_epoch": finished,
            "duration_seconds": finished - started,
            "conversation_id": conversation_id,
            "text": text,
            "input": {
                "context_characters": len(context_json),
                "sources": (result.get("summary") or {}).get("sources_total", 0),
                "comparison_targets": (result.get("comparisons") or {}).get("target_count", 0),
            },
        }
    except urllib.error.HTTPError as exc:
        try:
            details = exc.read().decode("utf-8", "replace")
        except Exception:
            details = ""
        finished = time.time()
        return {
            **base,
            "finished_at_epoch": finished,
            "duration_seconds": finished - started,
            "error": f"AI Task HTTP {exc.code}: {details[:500] or exc.reason}",
        }
    except Exception as exc:
        finished = time.time()
        return {
            **base,
            "finished_at_epoch": finished,
            "duration_seconds": finished - started,
            "error": str(exc),
        }
