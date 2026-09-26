from __future__ import annotations

import json
import os
import time
from typing import Any

import websocket


HA_AI_TASK_WS_URL = "ws://supervisor/core/websocket"
AI_WS_HEARTBEAT_SECONDS = 20
AI_DEFAULT_TIMEOUT_SECONDS = 600
AI_MIN_TIMEOUT_SECONDS = 60
AI_MAX_TIMEOUT_SECONDS = 1800
AI_MAX_CONTEXT_CHARS = 60000


def _stat_value(stats: dict[str, Any], key: str) -> Any:
    value = stats.get(key)
    if isinstance(value, dict):
        return value.get("value")
    return value


def _comparison_quality_snapshot(quality: Any) -> dict[str, Any]:
    quality = quality if isinstance(quality, dict) else {}
    return {
        "availability": quality.get("availability"),
        "source_status": quality.get("source_status"),
        "period_coverage_percent": quality.get("period_coverage_percent"),
        "sample_density_percent": quality.get("sample_density_percent"),
        "counter_mode": quality.get("counter_mode"),
        "warnings": quality.get("warnings") or [],
    }


def _comparison_interpretation(source: dict[str, Any]) -> dict[str, Any]:
    status = source.get("comparison_status")
    base_quality = _comparison_quality_snapshot(source.get("base_quality"))
    reference_quality = _comparison_quality_snapshot(source.get("reference_quality"))
    base_coverage = base_quality.get("period_coverage_percent")
    reference_coverage = reference_quality.get("period_coverage_percent")

    coverage_limited = any(
        isinstance(value, (int, float)) and value < 80.0
        for value in (base_coverage, reference_coverage)
    )
    return {
        "status": status,
        "coverage_limited": coverage_limited,
        "full_period_change_supported": bool(status == "comparable" and not coverage_limited),
    }


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
                            "base_quality": _comparison_quality_snapshot(source.get("base_quality")),
                            "reference_quality": _comparison_quality_snapshot(source.get("reference_quality")),
                            "interpretation": _comparison_interpretation(source),
                            "values": source.get("values") or [],
                        }
                    )
                cat_out["devices"].append(dev_out)
            target_out["catalogs"].append(cat_out)
        output["comparisons"].append(target_out)

    return output


def _extract_ai_task_payload(payload: Any) -> tuple[Any, str | None]:
    """Extract ai_task.generate_data data from direct or entity-namespaced payloads."""
    if not isinstance(payload, dict):
        raise RuntimeError("Réponse AI Task absente")

    if "data" in payload:
        return payload.get("data"), payload.get("conversation_id")

    for value in payload.values():
        if isinstance(value, dict) and "data" in value:
            return value.get("data"), value.get("conversation_id")

    raise RuntimeError("AI Task n'a retourné aucune donnée")


def _extract_service_response(payload: Any) -> tuple[Any, str | None]:
    """Backward-compatible extractor for REST response shapes."""
    if not isinstance(payload, dict):
        raise RuntimeError("Réponse Home Assistant AI Task invalide")
    return _extract_ai_task_payload(payload.get("service_response", payload))


def _recv_json(ws) -> dict[str, Any]:
    raw = ws.recv()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    message = json.loads(raw)
    if not isinstance(message, dict):
        raise RuntimeError("Message WebSocket Home Assistant invalide")
    return message


def _websocket_error_message(message: dict[str, Any]) -> str:
    error = message.get("error") or {}
    if isinstance(error, dict):
        code = error.get("code")
        text = error.get("message")
        if code and text:
            return f"{code}: {text}"
        return str(text or code or error)
    return str(error or "Erreur WebSocket Home Assistant")

def _sanitize_ai_text(text: str) -> str:
    """Remove internally contradictory boilerplate without rewriting AI meaning."""
    lines = str(text or "").splitlines()
    recommendation_index = next(
        (i for i, line in enumerate(lines) if line.strip().upper() == "RECOMMANDATIONS"),
        None,
    )
    if recommendation_index is None:
        return str(text or "").strip()

    recommendation_lines = lines[recommendation_index + 1 :]
    substantive_bullets = [
        line
        for line in recommendation_lines
        if line.strip().startswith("-")
        and line.strip().lower() != "- aucune recommandation particulière."
    ]
    if substantive_bullets:
        lines = [
            line
            for i, line in enumerate(lines)
            if not (
                i > recommendation_index
                and line.strip().lower() == "- aucune recommandation particulière."
            )
        ]
    return "\n".join(lines).strip()


def _instructions(context_json: str) -> str:
    return f"""Tu analyses un rapport domotique calculé par HA Reporting.
Réponds directement et brièvement en français, sans afficher de raisonnement interne.
N'invente aucun chiffre et ne recalcule pas les données : utilise exclusivement les statistiques fournies.
Distingue clairement un fait calculé d'une interprétation. Ignore les identifiants techniques lorsqu'un nom lisible est disponible.

Règles impératives pour les comparaisons N/N-x :
- Une source `unavailable` ne permet aucune conclusion d'évolution.
- Une source `partial` ou `reconstructed`, ou une comparaison dont `interpretation.coverage_limited` vaut true, ne doit jamais être formulée comme une hausse/baisse réelle de la période complète.
- Dans ce cas, formule plutôt : « sur les données disponibles, l'écart calculé est de ... », puis précise qu'il n'est pas directement interprétable comme une variation complète à cause de la couverture/qualité indiquée.
- N'utilise pas un pourcentage relatif issu d'une comparaison incomplète pour affirmer une dérive, une surconsommation ou une amélioration.
- Une recommandation fondée seulement sur une comparaison partielle/reconstruite doit rester proportionnée : privilégie « surveiller », « poursuivre la collecte » ou « recontrôler quand la couverture sera suffisante ». Ne demande pas d'en rechercher les causes sauf si les données de la période courante montrent, indépendamment de la comparaison, une anomalie étayée.

Produis exactement ces trois sections, en texte simple :
SYNTHÈSE
2 à 4 phrases sur les faits principaux de la période.

POINTS D'ATTENTION
0 à 5 puces commençant par "- ". Ne signale que des éléments réellement étayés par les données, y compris les limites de couverture si elles affectent l'interprétation. Écris "- Aucun point d'attention notable." si nécessaire.

RECOMMANDATIONS
0 à 4 puces commençant par "- ". Reste prudent et concret. N'invente pas de diagnostic de panne.
Écris "- Aucune recommandation particulière." uniquement s'il n'y a aucune autre recommandation. Ne combine jamais cette phrase avec d'autres puces.

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
    try:
        timeout_seconds = int(config.get("timeout_seconds", AI_DEFAULT_TIMEOUT_SECONDS) or AI_DEFAULT_TIMEOUT_SECONDS)
    except (TypeError, ValueError):
        timeout_seconds = AI_DEFAULT_TIMEOUT_SECONDS
    timeout_seconds = max(AI_MIN_TIMEOUT_SECONDS, min(AI_MAX_TIMEOUT_SECONDS, timeout_seconds))
    started = time.time()

    base = {
        "enabled": True,
        "status": "error",
        "entity_id": entity_id or None,
        "mode": "no_thinking_expected",
        "mode_control": "ai_task_entity_configuration",
        "timeout_seconds": timeout_seconds,
        "transport": "home_assistant_websocket",
        "websocket_url": HA_AI_TASK_WS_URL,
        "heartbeat_interval_seconds": AI_WS_HEARTBEAT_SECONDS,
        "started_at_epoch": started,
    }

    if not token:
        return {
            **base,
            "finished_at_epoch": time.time(),
            "error": "SUPERVISOR_TOKEN indisponible pour appeler AI Task",
        }

    ws = None
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

        # The Supervisor exposes Home Assistant's WebSocket API at this internal URL.
        # Keep the connect timeout short; the configured AI timeout applies to the service call itself.
        connect_timeout = min(30, max(5, timeout_seconds))
        ws = websocket.create_connection(
            HA_AI_TASK_WS_URL,
            timeout=connect_timeout,
            http_proxy_host=None,
            http_proxy_port=None,
        )

        auth_required = _recv_json(ws)
        if auth_required.get("type") != "auth_required":
            raise RuntimeError(f"Handshake WebSocket inattendu: {auth_required.get('type')}")

        ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth_result = _recv_json(ws)
        if auth_result.get("type") != "auth_ok":
            if auth_result.get("type") == "auth_invalid":
                raise RuntimeError(f"Authentification WebSocket refusée: {auth_result.get('message') or 'token invalide'}")
            raise RuntimeError(f"Authentification WebSocket inattendue: {auth_result.get('type')}")

        command_id = 1
        next_id = 2
        ws.send(
            json.dumps(
                {
                    "id": command_id,
                    "type": "call_service",
                    "domain": "ai_task",
                    "service": "generate_data",
                    "service_data": service_data,
                    "return_response": True,
                },
                ensure_ascii=False,
            )
        )

        deadline = time.monotonic() + timeout_seconds
        heartbeat_count = 0
        response_payload = None

        while response_payload is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Analyse IA interrompue après {timeout_seconds} s (délai maximal configuré).")

            ws.settimeout(min(AI_WS_HEARTBEAT_SECONDS, max(1, remaining)))
            try:
                message = _recv_json(ws)
            except websocket.WebSocketTimeoutException:
                ping_id = next_id
                next_id += 1
                heartbeat_count += 1
                ws.send(json.dumps({"id": ping_id, "type": "ping"}))
                continue

            # Ignore unrelated results such as our heartbeat pongs.
            if message.get("type") != "result" or message.get("id") != command_id:
                continue

            if not message.get("success"):
                raise RuntimeError(f"AI Task WebSocket: {_websocket_error_message(message)}")

            result_payload = message.get("result") or {}
            if not isinstance(result_payload, dict):
                raise RuntimeError("Réponse WebSocket AI Task invalide")
            response_payload = result_payload.get("response")

        data, conversation_id = _extract_ai_task_payload(response_payload)
        if isinstance(data, (dict, list)):
            text = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            text = str(data or "").strip()
        if not text:
            raise RuntimeError("AI Task a retourné un texte vide")
        text = _sanitize_ai_text(text)

        finished = time.time()
        return {
            **base,
            "status": "completed",
            "finished_at_epoch": finished,
            "duration_seconds": finished - started,
            "conversation_id": conversation_id,
            "heartbeat_count": heartbeat_count,
            "text": text,
            "input": {
                "context_characters": len(context_json),
                "sources": (result.get("summary") or {}).get("sources_total", 0),
                "comparison_targets": (result.get("comparisons") or {}).get("target_count", 0),
            },
        }
    except TimeoutError as exc:
        finished = time.time()
        return {
            **base,
            "finished_at_epoch": finished,
            "duration_seconds": finished - started,
            "error": str(exc),
        }
    except websocket.WebSocketException as exc:
        finished = time.time()
        return {
            **base,
            "finished_at_epoch": finished,
            "duration_seconds": finished - started,
            "error": f"WebSocket Home Assistant: {exc}",
        }
    except Exception as exc:
        finished = time.time()
        return {
            **base,
            "finished_at_epoch": finished,
            "duration_seconds": finished - started,
            "error": str(exc),
        }
    finally:
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass

