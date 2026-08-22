"""Unit tests for esp_normalizers — pure stdlib, no Home Assistant imports.

Run with: python3 -m pytest tests/ -v
"""

import importlib.util
import sys
from datetime import datetime
from pathlib import Path

import pytest

_MODULE_PATH = (
    Path(__file__).parent.parent
    / "custom_components"
    / "eskom_loadshedding"
    / "esp_normalizers.py"
)
_spec = importlib.util.spec_from_file_location("esp_normalizers", _MODULE_PATH)
esp_normalizers = importlib.util.module_from_spec(_spec)
sys.modules["esp_normalizers"] = esp_normalizers
_spec.loader.exec_module(esp_normalizers)

EskomAPIError = esp_normalizers.EskomAPIError

V2_STATUS_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
V2_EVENT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


# --- ensure_microseconds -------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-04-25T00:00:00.150529+02:00", "2026-04-25T00:00:00.150529+02:00"),
        ("2026-04-25T00:00:00+02:00", "2026-04-25T00:00:00.000000+02:00"),
        ("2026-04-25T00:00:00.1+02:00", "2026-04-25T00:00:00.100000+02:00"),
        ("2026-04-25T00:00:00.1234567+02:00", "2026-04-25T00:00:00.123456+02:00"),
        ("2026-04-25T00:00:00Z", "2026-04-25T00:00:00.000000+00:00"),
        ("2026-04-25T00:00:00+0200", "2026-04-25T00:00:00.000000+0200"),
    ],
)
def test_ensure_microseconds_parseable(value, expected):
    result = esp_normalizers.ensure_microseconds(value)
    assert result == expected
    datetime.strptime(result, V2_STATUS_TIME_FORMAT)


@pytest.mark.parametrize("value", [None, "", "garbage", "2026-04-25"])
def test_ensure_microseconds_passthrough_unrecognized(value):
    assert esp_normalizers.ensure_microseconds(value) == value


# --- strip_fractional -----------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-08-08T20:00:00+02:00", "2026-08-08T20:00:00+02:00"),
        ("2026-08-08T20:00:00.123456+02:00", "2026-08-08T20:00:00+02:00"),
        ("2026-08-08T20:00:00.5Z", "2026-08-08T20:00:00+00:00"),
    ],
)
def test_strip_fractional(value, expected):
    result = esp_normalizers.strip_fractional(value)
    assert result == expected
    datetime.strptime(result, V2_EVENT_TIME_FORMAT)


# --- normalize_v3_status --------------------------------------------------


def _v3_status(stage_updated="2026-05-15T22:00:00.748588+02:00"):
    return {
        "status": {
            "eskom": {
                "name": "National",
                "next_stages": [],
                "stage": "0",
                "stage_updated": stage_updated,
            },
            "capetown": {
                "name": "Cape Town",
                "next_stages": [],
                "stage": "1",
                "stage_updated": stage_updated,
            },
        }
    }


def test_normalize_v3_status_passthrough():
    result = esp_normalizers.normalize_v3_status(_v3_status())
    assert set(result["status"]) == {"eskom", "capetown"}
    # stage must stay a string: the sensor's `if value:` truthiness relies on
    # "0" being a truthy non-empty string
    assert result["status"]["eskom"]["stage"] == "0"
    assert isinstance(result["status"]["eskom"]["stage"], str)
    datetime.strptime(result["status"]["eskom"]["stage_updated"], V2_STATUS_TIME_FORMAT)


def test_normalize_v3_status_adds_microseconds():
    result = esp_normalizers.normalize_v3_status(
        _v3_status(stage_updated="2026-05-15T22:00:00+02:00")
    )
    datetime.strptime(result["status"]["eskom"]["stage_updated"], V2_STATUS_TIME_FORMAT)


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {"error": "quota exceeded"},
        {},
        {"status": {}},
        {"status": {"eskom": "not-a-dict"}},
        _v3_status(stage_updated=None),
        _v3_status(stage_updated="garbage"),
    ],
)
def test_normalize_v3_status_raises_on_surprise(payload):
    with pytest.raises(EskomAPIError):
        esp_normalizers.normalize_v3_status(payload)


# --- normalize_v3_events ---------------------------------------------------


def test_normalize_v3_events_happy_path():
    events = [
        {
            "note": "Stage 2",
            "start": "2026-08-08T20:00:00+02:00",
            "end": "2026-08-08T22:30:00+02:00",
        }
    ]
    result = esp_normalizers.normalize_v3_events(events)
    assert result == events
    datetime.strptime(result[0]["start"], V2_EVENT_TIME_FORMAT)


def test_normalize_v3_events_strips_fractional():
    events = [
        {
            "note": "Stage 2",
            "start": "2026-08-08T20:00:00.123+02:00",
            "end": "2026-08-08T22:30:00.456+02:00",
        }
    ]
    result = esp_normalizers.normalize_v3_events(events)
    assert result[0]["start"] == "2026-08-08T20:00:00+02:00"


def test_normalize_v3_events_tolerates_null_and_malformed():
    events = [
        {
            "note": None,
            "start": "2026-08-08T20:00:00+02:00",
            "end": "2026-08-08T22:30:00+02:00",
        },
        {"note": "missing end", "start": "2026-08-08T20:00:00+02:00"},
        {"note": "null times", "start": None, "end": None},
        {"note": "non-ISO", "start": "tomorrow", "end": "later"},
        "not-a-dict",
    ]
    result = esp_normalizers.normalize_v3_events(events)
    assert len(result) == 1
    assert result[0]["note"] == ""


def test_normalize_v3_events_empty_and_none():
    assert esp_normalizers.normalize_v3_events([]) == []
    assert esp_normalizers.normalize_v3_events(None) == []
    with pytest.raises(EskomAPIError):
        esp_normalizers.normalize_v3_events("not-a-list")


# --- v3_days_to_v2 ----------------------------------------------------------


def _v3_day(schedule):
    return {"date": "2026-11-18", "name": "Tuesday", "schedule": schedule}


def _slots(*ranges):
    return [
        {"start": f"2026-11-18T{start}:00+02:00", "end": f"2026-11-18T{end}:00+02:00"}
        for start, end in ranges
    ]


def test_v3_days_to_v2_shape():
    days = [
        _v3_day(
            [
                {"name": "Stage 1", "slots": _slots(("06:00", "08:30"))},
                {
                    "name": "Stage 2",
                    "slots": _slots(("06:00", "08:30"), ("14:00", "16:30")),
                },
            ]
        )
    ]
    result = esp_normalizers.v3_days_to_v2(days)
    assert len(result) == 1
    day = result[0]
    assert day["date"] == "2026-11-18"
    assert day["name"] == "Tuesday"
    assert len(day["stages"]) == 8
    assert day["stages"][0] == ["06:00-08:30"]
    assert day["stages"][1] == ["06:00-08:30", "14:00-16:30"]
    assert day["stages"][7] == []


def test_v3_days_to_v2_midnight_crossing():
    slots = [{"start": "2026-11-18T22:30:00+02:00", "end": "2026-11-19T00:30:00+02:00"}]
    days = [_v3_day([{"name": "Stage 1", "slots": slots}])]
    result = esp_normalizers.v3_days_to_v2(days)
    assert result[0]["stages"][0] == ["22:30-00:30"]


def test_v3_days_to_v2_converts_utc_slots_to_sast():
    # ESP examples use +02:00 today, but UTC slots must not silently shift
    # the schedule by two hours (calendar re-attaches +02:00 to these)
    slots = [{"start": "2026-11-18T04:00:00Z", "end": "2026-11-18T06:30:00Z"}]
    days = [_v3_day([{"name": "Stage 1", "slots": slots}])]
    result = esp_normalizers.v3_days_to_v2(days)
    assert result[0]["stages"][0] == ["06:00-08:30"]


def test_v3_days_to_v2_clips_and_skips():
    days = [
        _v3_day(
            [
                {"name": "Stage 0", "slots": _slots(("06:00", "08:30"))},
                {"name": "Stage 9", "slots": _slots(("06:00", "08:30"))},
                {"name": "Load Reduction", "slots": _slots(("06:00", "08:30"))},
                {"name": None, "slots": _slots(("06:00", "08:30"))},
                {"name": " Stage 3 ", "slots": _slots(("10:00", "12:30"))},
                "not-a-dict",
            ]
        )
    ]
    result = esp_normalizers.v3_days_to_v2(days)
    stages = result[0]["stages"]
    assert stages[2] == ["10:00-12:30"]  # whitespace-tolerant Stage 3
    assert all(not s for i, s in enumerate(stages) if i != 2)


def test_v3_days_to_v2_null_tolerance_and_empty():
    # Days without a valid YYYY-MM-DD date are skipped entirely: the calendar
    # builds datetimes from the date string and would abort its event listing
    days = [{"date": None, "name": None, "schedule": None}, "not-a-dict"]
    result = esp_normalizers.v3_days_to_v2(days)
    assert result == []
    assert esp_normalizers.v3_days_to_v2(None) == []
    assert esp_normalizers.v3_days_to_v2([]) == []
    with pytest.raises(EskomAPIError):
        esp_normalizers.v3_days_to_v2({"not": "a list"})


def test_v3_days_to_v2_hhmm_slots_passthrough():
    # Defensive: if ESP ever serves bare HH:MM strings, pass them through
    days = [
        _v3_day([{"name": "Stage 1", "slots": [{"start": "06:00", "end": "08:30"}]}])
    ]
    result = esp_normalizers.v3_days_to_v2(days)
    assert result[0]["stages"][0] == ["06:00-08:30"]


# --- v3_schedule_to_area_information ----------------------------------------


def _v3_schedule_payload():
    return {
        "name": "Stellenbosch",
        "events": [
            {
                "note": "Stage 2",
                "start": "2026-08-08T20:00:00+02:00",
                "end": "2026-08-08T22:30:00+02:00",
            }
        ],
        "schedule": {
            "days": [
                _v3_day([{"name": "Stage 1", "slots": _slots(("20:00", "22:30"))}])
            ]
        },
    }


def test_v3_schedule_to_area_information_shape():
    area_info = {"name": "Stellenbosch", "region": "Stellenbosch, Western Cape"}
    result = esp_normalizers.v3_schedule_to_area_information(
        _v3_schedule_payload(), area_info
    )
    assert set(result) == {"events", "info", "schedule"}
    assert result["info"] == area_info
    assert result["events"][0]["note"] == "Stage 2"
    assert result["schedule"]["days"][0]["stages"][0] == ["20:00-22:30"]


def test_v3_schedule_to_area_information_missing_bits():
    result = esp_normalizers.v3_schedule_to_area_information({"events": []}, None)
    assert result["events"] == []
    assert result["info"] == {"name": "", "region": ""}
    assert result["schedule"]["days"] == []
    with pytest.raises(EskomAPIError):
        esp_normalizers.v3_schedule_to_area_information({"error": "nope"}, None)
    with pytest.raises(EskomAPIError):
        esp_normalizers.v3_schedule_to_area_information(None, None)


# --- allowance_from_headers ---------------------------------------------------


def test_allowance_from_headers_happy_path():
    headers = {
        "x-ratelimit-limit": "200",
        "x-ratelimit-remaining": "173",
        "x-ratelimit-used": "27",
        "x-ratelimit-reset": "2026-07-17T00:00:00+00:00",
    }
    result = esp_normalizers.allowance_from_headers(headers)
    assert result == {
        "allowance": {"count": 27, "limit": 200, "type": "daily"},
        "source": "headers",
    }


def test_allowance_from_headers_mixed_case_keys():
    headers = {"X-RateLimit-Limit": "200", "X-RateLimit-Used": "27"}
    result = esp_normalizers.allowance_from_headers(headers)
    assert result["allowance"]["count"] == 27


@pytest.mark.parametrize(
    "headers",
    [
        None,
        {},
        {"x-ratelimit-limit": "200"},
        {"x-ratelimit-limit": "200", "x-ratelimit-used": None},
        {"x-ratelimit-limit": "many", "x-ratelimit-used": "27"},
    ],
)
def test_allowance_from_headers_unusable(headers):
    assert esp_normalizers.allowance_from_headers(headers) is None


# --- ensure_error_free ---------------------------------------------------------


def test_ensure_error_free():
    assert esp_normalizers.ensure_error_free({"ok": 1}, "/x") == {"ok": 1}
    for bad in (None, [], "str", {"error": "boom"}):
        with pytest.raises(EskomAPIError):
            esp_normalizers.ensure_error_free(bad, "/x")
