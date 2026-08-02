"""Fixture-driven tests: real ESP v3 payloads through the normalizers.

Fixtures captured from the live v3.0 API in July 2026 (schedule fixtures via
the free `test=current` parameter). They lock the real-world shapes — if ESP
changes a shape, these fail before production does. Observations baked into
the fixtures: /status timestamps carry fractional seconds and colon offsets;
schedule events DO carry fractional seconds (strip_fractional is load-bearing);
days[].schedule[].name is exactly "Stage 1".."Stage 8"; empty slot lists occur;
auth failures serve HTTP 403 with a JSON body (the spec documents 401 - the
client handles both).
"""

import json
import re
from datetime import datetime
from pathlib import Path

from test_esp_normalizers import esp_normalizers

FIXTURES = Path(__file__).parent / "fixtures"

V2_STATUS_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f%z"
V2_EVENT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def _load(name):
    with open(FIXTURES / name) as f:
        return json.load(f)


def test_real_v3_status_normalizes():
    result = esp_normalizers.normalize_v3_status(_load("v3_status.json"))
    for area in ("eskom", "capetown"):
        assert isinstance(result["status"][area]["stage"], str)
        datetime.strptime(
            result["status"][area]["stage_updated"], V2_STATUS_TIME_FORMAT
        )


def test_real_v3_schedules_normalize_to_v2_consumable_shape():
    for name in ("v3_schedule_test_eskme2.json", "v3_schedule_test_capetown7.json"):
        payload = _load(name)
        area_info = {"name": "Test Area", "region": "Test Region"}
        result = esp_normalizers.v3_schedule_to_area_information(payload, area_info)

        # events must parse with the v2 consumers' strptime (real fixtures
        # carry fractional seconds, which strip_fractional must remove)
        assert result["events"], f"{name}: expected test events"
        for event in result["events"]:
            datetime.strptime(event["start"], V2_EVENT_TIME_FORMAT)
            datetime.strptime(event["end"], V2_EVENT_TIME_FORMAT)
            assert isinstance(event["note"], str)

        # days must match the exact v2 calendar contract:
        # 8 stage lists of "HH:MM-HH:MM" strings, date YYYY-MM-DD
        days = result["schedule"]["days"]
        assert days, f"{name}: expected schedule days"
        for day in days:
            assert re.match(r"^\d{4}-\d{2}-\d{2}$", day["date"])
            assert len(day["stages"]) == 8
            for slots in day["stages"]:
                for slot in slots:
                    assert re.match(r"^\d{2}:\d{2}-\d{2}:\d{2}$", slot)
        # the calendar builds f"{date}T{HH:MM}+02:00" and parses %Y-%m-%dT%H:%M%z
        sample_day = days[0]
        for slots in sample_day["stages"]:
            if slots:
                start = slots[0].split("-")[0]
                datetime.strptime(
                    f"{sample_day['date']}T{start}+02:00", "%Y-%m-%dT%H:%M%z"
                )
                break


def test_real_v3_area_payloads_have_expected_fields():
    for name, schedule_id in (
        ("v3_area_stellenbosch.json", "eskme-2"),
        ("v3_area_vawaterfront.json", "capetown-7"),
    ):
        payload = _load(name)
        assert payload["name"]
        assert payload["municipality"]
        assert payload["province"]
        auto = [s["id"] for s in payload["schedules"] if s.get("auto_enabled")]
        assert auto == [schedule_id]


def test_real_ratelimit_headers_synthesize_allowance():
    discovery = _load("v3_ratelimit_headers.json")
    for key, headers in discovery["ratelimit_headers_observed"].items():
        result = esp_normalizers.allowance_from_headers(headers)
        assert result is not None, key
        allowance = result["allowance"]
        assert allowance["limit"] - allowance["count"] == int(
            headers["x-ratelimit-remaining"]
        )
