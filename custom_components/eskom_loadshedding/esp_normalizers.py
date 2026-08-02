"""Pure normalization helpers for EskomSePush API v3 responses.

This module deliberately has NO Home Assistant imports so it can be unit
tested standalone. All functions convert v3.0 response payloads into the
exact shapes the v2.0-era entity code consumes, or raise EskomAPIError on
unexpected input (so the coordinator marks entities unavailable instead of
freezing them on garbage data).
"""

import re
from datetime import datetime, timedelta, timezone

MAX_STAGES = 8
_STAGE_NOTE_RE = re.compile(r"^Stage (\d+)$")
_ISO_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?([+-]\d{2}:?\d{2})$"
)
_EVENT_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:?\d{2}$")
_HHMM_RE = re.compile(r"^\d{2}:\d{2}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Downstream calendar code re-attaches '+02:00' to bare HH:MM strings, so all
# slot times must be normalized to SAST wall-clock regardless of payload offset
_SAST = timezone(timedelta(hours=2))


class EskomAPIError(Exception):
    """Raised for any ESP API failure (bad status, error body, bad shape)."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class EskomAuthError(EskomAPIError):
    """Raised when the ESP API rejects the token (HTTP 401/403)."""


def ensure_error_free(data, context):
    """Validate a decoded API payload, raising on error bodies or non-dicts."""
    if data is None:
        raise EskomAPIError(f"{context}: empty/undecodable response")
    if not isinstance(data, dict):
        raise EskomAPIError(f"{context}: unexpected payload type {type(data).__name__}")
    if "error" in data:
        raise EskomAPIError(f"{context}: API error: {data['error']}")
    return data


def _z_to_offset(timestamp):
    """Convert a trailing 'Z' UTC designator to '+00:00'."""
    if timestamp.endswith("Z"):
        return timestamp[:-1] + "+00:00"
    return timestamp


def ensure_microseconds(timestamp):
    """Make an ISO timestamp parseable with '%Y-%m-%dT%H:%M:%S.%f%z'.

    Adds '.000000' when fractional seconds are missing and truncates more
    than six fractional digits. Returns falsy/unrecognized input unchanged.
    """
    if not timestamp:
        return timestamp
    match = _ISO_RE.match(_z_to_offset(timestamp))
    if not match:
        return timestamp
    base, frac, offset = match.groups()
    digits = (frac or ".")[1:].ljust(6, "0")[:6]
    return f"{base}.{digits}{offset}"


def strip_fractional(timestamp):
    """Make an ISO timestamp parseable with '%Y-%m-%dT%H:%M:%S%z' (no %f)."""
    if not timestamp:
        return timestamp
    return re.sub(r"(T\d{2}:\d{2}:\d{2})\.\d+", r"\1", _z_to_offset(timestamp))


def normalize_v3_status(data):
    """Normalize a v3 /status payload to the v2 shape the sensors consume.

    v3's shape matches v2 except timestamps may lack fractional seconds.
    Raises on missing/unparseable stage_updated: the status sensor parses it
    with a hard '%f%z' strptime inside a property, and an unparseable value
    would freeze the entity at its last-good state.
    """
    ensure_error_free(data, "/status")
    status = data.get("status")
    if not isinstance(status, dict) or not status:
        raise EskomAPIError("/status: missing 'status' object")
    normalized = {}
    for area_key, area in status.items():
        if not isinstance(area, dict):
            raise EskomAPIError(f"/status: area '{area_key}' is not an object")
        area = dict(area)
        stage_updated = ensure_microseconds(area.get("stage_updated"))
        if not stage_updated or not _ISO_RE.match(stage_updated):
            raise EskomAPIError(
                f"/status: missing/unparseable stage_updated for '{area_key}'"
            )
        area["stage_updated"] = stage_updated
        normalized[area_key] = area
    return {"status": normalized}


def normalize_v3_events(events):
    """Normalize v3 schedule events to the v2 events shape.

    Emits only events whose timestamps parse with the v2 consumers'
    '%Y-%m-%dT%H:%M:%S%z' strptime; skips malformed entries (and tolerates
    JSON null note/start/end) rather than crash downstream.
    """
    if events is None:
        events = []
    if not isinstance(events, list):
        raise EskomAPIError("/schedule: 'events' is not a list")
    normalized = []
    for event in events:
        if not isinstance(event, dict):
            continue
        start = strip_fractional(event.get("start"))
        end = strip_fractional(event.get("end"))
        if not (
            start and end and _EVENT_TS_RE.match(start) and _EVENT_TS_RE.match(end)
        ):
            continue
        normalized.append({"note": event.get("note") or "", "start": start, "end": end})
    return normalized


def _slot_time(value):
    """Extract an SAST 'HH:MM' string from a v3 slot time (ISO or already HH:MM).

    Downstream (calendar.py) re-attaches '+02:00' to these strings, so they
    MUST be SAST wall-clock regardless of the payload's offset.
    """
    if not value or not isinstance(value, str):
        return None
    if _HHMM_RE.match(value):
        return value
    try:
        parsed = datetime.fromisoformat(strip_fractional(value))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(_SAST)
    return parsed.strftime("%H:%M")


def v3_days_to_v2(days):
    """Convert v3 schedule.days[].schedule[] into v2 days[].stages[] lists.

    v3 day:  {"date": "2026-11-18", "name": "Tuesday",
              "schedule": [{"name": "Stage 1", "slots": [{"start": ISO, "end": ISO}]}]}
    v2 day:  {"date": "2026-11-18", "name": "Tuesday",
              "stages": [["HH:MM-HH:MM", ...], ...]}   # 8 lists, index = stage - 1
    """
    if days is None:
        days = []
    if not isinstance(days, list):
        raise EskomAPIError("/schedule: 'days' is not a list")
    v2_days = []
    for day in days:
        if not isinstance(day, dict) or not _DATE_RE.match(day.get("date") or ""):
            # The calendar builds datetimes from the date string; a malformed
            # date would abort its whole event listing
            continue
        stages = [[] for _ in range(MAX_STAGES)]
        for entry in day.get("schedule") or []:
            if not isinstance(entry, dict):
                continue
            match = _STAGE_NOTE_RE.match((entry.get("name") or "").strip())
            if not match:
                continue  # non-stage entries (e.g. "Load Reduction") have no v2 slot
            stage_no = int(match.group(1))
            if not 1 <= stage_no <= MAX_STAGES:
                continue  # v2 consumers only index stages 1-8
            for slot in entry.get("slots") or []:
                if not isinstance(slot, dict):
                    continue
                start = _slot_time(slot.get("start"))
                end = _slot_time(slot.get("end"))
                if start and end:
                    stages[stage_no - 1].append(f"{start}-{end}")
        v2_days.append(
            {
                "date": day.get("date") or "",
                "name": day.get("name") or "",
                "stages": stages,
            }
        )
    return v2_days


def v3_schedule_to_area_information(data, area_info):
    """Build the v2 'area_information' dict from a v3 /schedule payload.

    area_info supplies the static v2 'info' block ({'name': …, 'region': …}),
    sourced from operator-configured options or a cached v3 /area fetch.
    """
    ensure_error_free(data, "/schedule")
    schedule = data.get("schedule") or {}
    if not isinstance(schedule, dict):
        raise EskomAPIError("/schedule: 'schedule' is not an object")
    return {
        "events": normalize_v3_events(data.get("events")),
        "info": {
            "name": (area_info or {}).get("name", ""),
            "region": (area_info or {}).get("region", ""),
        },
        "schedule": {"days": v3_days_to_v2(schedule.get("days"))},
    }


def allowance_from_headers(headers):
    """Synthesize the v2 allowance dict from x-ratelimit-* response headers.

    Returns None when headers are absent or unusable; the quota sensor
    then reports unknown for that cycle.
    """
    if not headers:
        return None
    headers = {str(key).lower(): value for key, value in headers.items()}
    try:
        count = int(headers["x-ratelimit-used"])
        limit = int(headers["x-ratelimit-limit"])
    except (KeyError, TypeError, ValueError):
        return None
    # The v3 headers don't carry the quota period; report "daily", which
    # matches ESP's standard plans
    return {
        "allowance": {"count": count, "limit": limit, "type": "daily"},
        "source": "headers",
    }
