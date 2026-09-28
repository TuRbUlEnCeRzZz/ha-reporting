import copy
import json
import os
import re
import tempfile
import threading
import unicodedata
from datetime import timedelta
from pathlib import Path

AUTOMATION_FILE = Path('/config/automations.json')
VALID_SCHEDULE_TYPES = {'hourly', 'daily', 'weekly', 'monthly', 'yearly'}
VALID_THEMES = {'dark', 'light'}
HISTORY_LIMIT = 50
_STORE_LOCK = threading.RLock()


def _stable_id(value):
    value = unicodedata.normalize('NFKD', str(value or ''))
    value = value.encode('ascii', 'ignore').decode('ascii').lower().strip()
    return re.sub(r'[^a-z0-9]+', '_', value).strip('_')


def _atomic_write(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except OSError:
            pass


def _read_all():
    if not AUTOMATION_FILE.exists():
        return {'version': 2, 'automations': []}
    data = json.loads(AUTOMATION_FILE.read_text(encoding='utf-8') or '{}')
    if not isinstance(data, dict):
        raise ValueError('Fichier des automatisations invalide')
    data.setdefault('version', 1)
    data.setdefault('automations', [])
    if not isinstance(data['automations'], list):
        raise ValueError('Liste des automatisations invalide')
    return data


def _parse_time(value):
    value = str(value or '05:40').strip()
    match = re.fullmatch(r'(\d{1,2}):(\d{2})', value)
    if not match:
        raise ValueError('Heure invalide, format attendu HH:MM')
    hour = int(match.group(1))
    minute = int(match.group(2))
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError('Heure invalide')
    return f'{hour:02d}:{minute:02d}'


def _normalize_history(raw_history):
    if not isinstance(raw_history, list):
        return []
    history = []
    for item in raw_history[-HISTORY_LIMIT:]:
        if not isinstance(item, dict):
            continue
        history.append({
            'job_id': item.get('job_id'),
            'trigger': str(item.get('trigger') or 'unknown'),
            'attempt': max(0, int(item.get('attempt') or 0)),
            'started_at': item.get('started_at'),
            'finished_at': item.get('finished_at'),
            'status': item.get('status'),
            'duration_seconds': item.get('duration_seconds'),
            'error': item.get('error'),
            'warnings': copy.deepcopy(item.get('warnings') or []),
            'document_id': item.get('document_id'),
            'filename': item.get('filename'),
            'exports': copy.deepcopy(item.get('exports') or {}),
            'ai_status': item.get('ai_status'),
            'progress': copy.deepcopy(item.get('progress')),
        })
    return history


def normalize_automation(payload, automation_id=None):
    payload = copy.deepcopy(payload or {})
    name = str(payload.get('name') or '').strip()
    report_id = str(payload.get('report_id') or '').strip()
    if not name:
        raise ValueError("Nom de l'automatisation requis")
    if not report_id:
        raise ValueError('report_id est obligatoire')

    aid = str(automation_id or payload.get('id') or _stable_id(name) or '').strip()
    if not aid:
        raise ValueError("ID d'automatisation invalide")

    schedule = copy.deepcopy(payload.get('schedule') or {})
    schedule_type = str(schedule.get('type') or 'monthly').strip().lower()
    if schedule_type not in VALID_SCHEDULE_TYPES:
        raise ValueError('Type de planification invalide')
    normalized_schedule = {'type': schedule_type}
    if schedule_type == 'hourly':
        minute = int(schedule.get('minute', 0))
        if not 0 <= minute <= 59:
            raise ValueError('Minute horaire invalide')
        normalized_schedule['minute'] = minute
    else:
        normalized_schedule['time'] = _parse_time(schedule.get('time') or '05:40')
        if schedule_type == 'weekly':
            weekday = int(schedule.get('weekday', 0))
            if not 0 <= weekday <= 6:
                raise ValueError('Jour de semaine invalide')
            normalized_schedule['weekday'] = weekday
        elif schedule_type == 'monthly':
            day = int(schedule.get('day', 1))
            if not 1 <= day <= 31:
                raise ValueError('Jour du mois invalide')
            normalized_schedule['day'] = day
        elif schedule_type == 'yearly':
            month = int(schedule.get('month', 1))
            day = int(schedule.get('day', 1))
            if not 1 <= month <= 12 or not 1 <= day <= 31:
                raise ValueError('Date annuelle invalide')
            normalized_schedule['month'] = month
            normalized_schedule['day'] = day

    pipeline = copy.deepcopy(payload.get('pipeline') or {})
    ai_analysis = pipeline.get('ai_analysis', None)
    if ai_analysis not in (None, True, False):
        raise ValueError('pipeline.ai_analysis doit être true, false ou null')
    generate_pdf = pipeline.get('generate_pdf', True)
    if not isinstance(generate_pdf, bool):
        raise ValueError('pipeline.generate_pdf doit être booléen')
    theme = str(pipeline.get('theme') or 'dark').strip().lower()
    if theme not in VALID_THEMES:
        raise ValueError('Thème invalide')
    destinations = []
    raw_destinations = pipeline.get('destinations') or []
    if not isinstance(raw_destinations, list):
        raise ValueError('pipeline.destinations doit être une liste')
    for item in raw_destinations:
        value = str(item or '').strip().lower()
        if value and value not in destinations:
            destinations.append(value)
    if destinations and not generate_pdf:
        raise ValueError('Le PDF doit être généré pour exporter une destination')

    notification = copy.deepcopy(payload.get('notification') or {})
    persistent = bool(notification.get('persistent', False))
    notify_entity = str(notification.get('notify_entity') or '').strip()
    tts_entity = str(notification.get('tts_entity') or '').strip()
    media_player_entity = str(notification.get('media_player_entity') or '').strip()
    if notify_entity and not notify_entity.startswith('notify.'):
        raise ValueError('notification.notify_entity doit être une entité notify.*')
    if tts_entity and not tts_entity.startswith('tts.'):
        raise ValueError('notification.tts_entity doit être une entité tts.*')
    if media_player_entity and not media_player_entity.startswith('media_player.'):
        raise ValueError('notification.media_player_entity doit être une entité media_player.*')
    if bool(tts_entity) != bool(media_player_entity):
        raise ValueError('TTS nécessite une entité tts et un lecteur media_player')

    retry = copy.deepcopy(payload.get('retry') or {})
    retry_enabled = bool(retry.get('enabled', False))
    max_retries = int(retry.get('max_retries', 1))
    delay_minutes = int(retry.get('delay_minutes', 10))
    if not 0 <= max_retries <= 3:
        raise ValueError('retry.max_retries doit être compris entre 0 et 3')
    if not 1 <= delay_minutes <= 1440:
        raise ValueError('retry.delay_minutes doit être compris entre 1 et 1440')

    runtime = copy.deepcopy(payload.get('runtime') or {})
    return {
        'id': aid,
        'name': name,
        'enabled': bool(payload.get('enabled', True)),
        'report_id': report_id,
        'schedule': normalized_schedule,
        'pipeline': {
            'ai_analysis': ai_analysis,
            'generate_pdf': generate_pdf,
            'theme': theme,
            'destinations': destinations,
        },
        'notification': {
            'persistent': persistent,
            'notify_entity': notify_entity,
            'tts_entity': tts_entity,
            'media_player_entity': media_player_entity,
        },
        'retry': {
            'enabled': retry_enabled,
            'max_retries': max_retries,
            'delay_minutes': delay_minutes,
        },
        'runtime': {
            'last_schedule_key': runtime.get('last_schedule_key'),
            'last_run_at': runtime.get('last_run_at'),
            'last_finished_at': runtime.get('last_finished_at'),
            'last_job_id': runtime.get('last_job_id'),
            'last_status': runtime.get('last_status'),
            'last_progress': copy.deepcopy(runtime.get('last_progress')),
            'last_error': runtime.get('last_error'),
            'last_duration_seconds': runtime.get('last_duration_seconds'),
            'last_warnings': copy.deepcopy(runtime.get('last_warnings') or []),
            'last_document_id': runtime.get('last_document_id'),
            'last_filename': runtime.get('last_filename'),
            'last_exports': copy.deepcopy(runtime.get('last_exports') or {}),
            'last_trigger': runtime.get('last_trigger'),
            'active_job_id': runtime.get('active_job_id'),
            'next_retry_at': runtime.get('next_retry_at'),
            'retry_attempt': max(0, int(runtime.get('retry_attempt') or 0)),
            'consecutive_failures': max(0, int(runtime.get('consecutive_failures') or 0)),
        },
        'history': _normalize_history(payload.get('history')),
    }


def _normalized_items(data):
    output = []
    for item in data.get('automations') or []:
        output.append(normalize_automation(item, automation_id=item.get('id')))
    return output


def list_automations():
    with _STORE_LOCK:
        return copy.deepcopy(_normalized_items(_read_all()))


def get_automation(automation_id):
    automation_id = str(automation_id or '').strip()
    with _STORE_LOCK:
        for item in _read_all()['automations']:
            if item.get('id') == automation_id:
                return normalize_automation(item, automation_id=automation_id)
    raise ValueError("Automatisation introuvable")


def create_automation(payload):
    item = normalize_automation(payload)
    with _STORE_LOCK:
        data = _read_all()
        if any(existing.get('id') == item['id'] for existing in data['automations']):
            raise ValueError("Cet ID d'automatisation existe déjà")
        data['version'] = 2
        data['automations'].append(item)
        _atomic_write(AUTOMATION_FILE, data)
    return copy.deepcopy(item)


def update_automation(automation_id, payload):
    with _STORE_LOCK:
        data = _read_all()
        index = next((i for i, item in enumerate(data['automations']) if item.get('id') == automation_id), None)
        if index is None:
            raise ValueError('Automatisation introuvable')
        current = normalize_automation(data['automations'][index], automation_id=automation_id)
        merged = copy.deepcopy(current)
        for key in ('name', 'enabled', 'report_id', 'schedule', 'pipeline', 'notification', 'retry'):
            if key in (payload or {}):
                merged[key] = copy.deepcopy(payload[key])
        merged['runtime'] = current.get('runtime') or {}
        merged['history'] = current.get('history') or []
        item = normalize_automation(merged, automation_id=automation_id)
        data['version'] = 2
        data['automations'][index] = item
        _atomic_write(AUTOMATION_FILE, data)
    return copy.deepcopy(item)


def delete_automation(automation_id):
    with _STORE_LOCK:
        data = _read_all()
        before = len(data['automations'])
        data['automations'] = [item for item in data['automations'] if item.get('id') != automation_id]
        if len(data['automations']) == before:
            raise ValueError('Automatisation introuvable')
        data['version'] = 2
        _atomic_write(AUTOMATION_FILE, data)
    return {'deleted': automation_id}


def update_runtime(automation_id, **fields):
    with _STORE_LOCK:
        data = _read_all()
        index = next((i for i, item in enumerate(data['automations']) if item.get('id') == automation_id), None)
        if index is None:
            return None
        current = normalize_automation(data['automations'][index], automation_id=automation_id)
        runtime = current.setdefault('runtime', {})
        runtime.update(copy.deepcopy(fields))
        data['version'] = 2
        data['automations'][index] = normalize_automation(current, automation_id=automation_id)
        _atomic_write(AUTOMATION_FILE, data)
        return copy.deepcopy(data['automations'][index])


def append_history(automation_id, record, limit=HISTORY_LIMIT):
    try:
        limit = max(1, min(HISTORY_LIMIT, int(limit)))
    except (TypeError, ValueError):
        limit = HISTORY_LIMIT
    with _STORE_LOCK:
        data = _read_all()
        index = next((i for i, item in enumerate(data['automations']) if item.get('id') == automation_id), None)
        if index is None:
            return None
        current = normalize_automation(data['automations'][index], automation_id=automation_id)
        history = list(current.get('history') or [])
        normalized = _normalize_history([record])
        if normalized:
            history.append(normalized[0])
        current['history'] = history[-limit:]
        data['version'] = 2
        data['automations'][index] = normalize_automation(current, automation_id=automation_id)
        _atomic_write(AUTOMATION_FILE, data)
        return copy.deepcopy(data['automations'][index])


def list_history(automation_id, limit=HISTORY_LIMIT):
    item = get_automation(automation_id)
    try:
        limit = max(1, min(HISTORY_LIMIT, int(limit)))
    except (TypeError, ValueError):
        limit = HISTORY_LIMIT
    return copy.deepcopy((item.get('history') or [])[-limit:][::-1])


def schedule_key(automation, now):
    schedule = automation.get('schedule') or {}
    kind = schedule.get('type')
    if kind == 'hourly':
        return now.strftime('%Y-%m-%dT%H')
    if kind == 'daily':
        return now.strftime('%Y-%m-%d')
    if kind == 'weekly':
        iso = now.isocalendar()
        return f'{iso.year}-W{iso.week:02d}'
    if kind == 'monthly':
        return now.strftime('%Y-%m')
    if kind == 'yearly':
        return now.strftime('%Y')
    return None


def is_due(automation, now):
    if not automation.get('enabled'):
        return False
    schedule = automation.get('schedule') or {}
    kind = schedule.get('type')
    if kind == 'hourly':
        if now.minute != int(schedule.get('minute', 0)):
            return False
    else:
        hour, minute = [int(part) for part in str(schedule.get('time') or '05:40').split(':', 1)]
        if now.hour != hour or now.minute != minute:
            return False
        if kind == 'weekly' and now.weekday() != int(schedule.get('weekday', 0)):
            return False
        if kind == 'monthly' and now.day != int(schedule.get('day', 1)):
            return False
        if kind == 'yearly' and (now.month != int(schedule.get('month', 1)) or now.day != int(schedule.get('day', 1))):
            return False
    key = schedule_key(automation, now)
    return bool(key and (automation.get('runtime') or {}).get('last_schedule_key') != key)


def next_run(automation, now):
    if not automation.get('enabled'):
        return None
    schedule = automation.get('schedule') or {}
    kind = schedule.get('type')
    if kind == 'hourly':
        minute = int(schedule.get('minute', 0))
        candidate = now.replace(minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(hours=1)
        return candidate

    hour, minute = [int(part) for part in str(schedule.get('time') or '05:40').split(':', 1)]
    if kind == 'daily':
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate
    if kind == 'weekly':
        target = int(schedule.get('weekday', 0))
        days = (target - now.weekday()) % 7
        candidate = (now + timedelta(days=days)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=7)
        return candidate
    if kind == 'monthly':
        target_day = int(schedule.get('day', 1))
        year, month = now.year, now.month
        for _ in range(24):
            try:
                candidate = now.replace(year=year, month=month, day=target_day, hour=hour, minute=minute, second=0, microsecond=0)
                if candidate > now:
                    return candidate
            except ValueError:
                pass
            month += 1
            if month > 12:
                month = 1
                year += 1
        return None
    if kind == 'yearly':
        month = int(schedule.get('month', 1))
        day = int(schedule.get('day', 1))
        for year in (now.year, now.year + 1, now.year + 2):
            try:
                candidate = now.replace(year=year, month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
                if candidate > now:
                    return candidate
            except ValueError:
                continue
    return None
