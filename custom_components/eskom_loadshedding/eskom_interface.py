"""HTTP interface to the EskomSePush API v3.0."""

import logging
import socket

import aiohttp

from . import esp_normalizers
from .const import BASE_API_URL, REQUEST_TIMEOUT_S
from .esp_normalizers import EskomAPIError, EskomAuthError

_LOGGER: logging.Logger = logging.getLogger(__package__)

_RATELIMIT_HEADERS = (
    "x-ratelimit-limit",
    "x-ratelimit-remaining",
    "x-ratelimit-used",
    "x-ratelimit-reset",
)


class EskomInterface:
    """Interface class to obtain loadshedding information using the EskomSePush API"""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        schedule_id: str = None,
        area_id: str = None,
        area_info: dict = None,
    ):
        """Initializes class parameters"""
        self.session = session
        self.api_key = api_key
        self.schedule_id = schedule_id
        self.area_id = area_id
        self.area_info = area_info
        self.base_url = BASE_API_URL
        self.latest_ratelimit = None
        self.headers = {
            "Token": api_key,
        }

    async def async_query_api(self, endpoint: str, payload: dict = None):
        """Queries a given endpoint on the EskomSePush API.

        Raises EskomAuthError on HTTP 401/403 and EskomAPIError on any other
        non-200 response, timeout, network failure, or undecodable body —
        so the coordinator marks entities unavailable instead of freezing
        them on garbage data. Successful calls also capture the
        x-ratelimit-* quota headers, which replace the retired v2
        /api_allowance endpoint.
        """
        query_url = self.base_url + endpoint
        try:
            async with self.session.get(
                url=query_url,
                headers=self.headers,
                params=payload,
                timeout=REQUEST_TIMEOUT_S,
            ) as resp:
                if "x-ratelimit-limit" in resp.headers:
                    self.latest_ratelimit = {
                        key: resp.headers.get(key) for key in _RATELIMIT_HEADERS
                    }
                # Classify auth failures on status alone — the body may not
                # be JSON (spec documents 401, live API serves 403 today)
                if resp.status in (401, 403):
                    raise EskomAuthError(
                        f"{endpoint}: authentication rejected (HTTP {resp.status})",
                        status=resp.status,
                    )
                try:
                    data = await resp.json()
                except (aiohttp.ContentTypeError, ValueError) as exception:
                    raise EskomAPIError(
                        f"{endpoint}: undecodable response (HTTP {resp.status})",
                        status=resp.status,
                    ) from exception
                if resp.status != 200:
                    message = data.get("error") if isinstance(data, dict) else data
                    raise EskomAPIError(
                        f"{endpoint}: HTTP {resp.status}: {message}",
                        status=resp.status,
                    )
                return data
        except (TimeoutError, aiohttp.ClientError, socket.gaierror) as exception:
            _LOGGER.error(
                "Error fetching information from %s: %s", query_url, exception
            )
            raise EskomAPIError(
                f"{endpoint}: request failed: {exception}"
            ) from exception

    async def async_get_status(self) -> dict:
        """Fetches the current loadshedding status"""
        # Query the API
        data = await self.async_query_api("/status")
        return esp_normalizers.normalize_v3_status(data)

    async def async_get_area(self, area_id: str) -> dict:
        """Fetches area metadata (name, municipality, available schedules)"""
        # Query the API
        data = await self.async_query_api("/area", payload={"id": area_id})
        return esp_normalizers.ensure_error_free(data, "/area")

    async def async_get_area_info(self) -> dict:
        """Returns the static area info block ({'name': …, 'region': …}).

        Prefers configured values; falls back to a single /area fetch
        (1 credit), cached on the instance for its lifetime. Entries migrated
        from v2 have no v3 area id, so they render empty info until the area
        is re-selected (a repair issue prompts for this).
        """
        if self.area_info and self.area_info.get("name"):
            return self.area_info
        if not self.area_id:
            return {"name": "", "region": ""}
        data = await self.async_get_area(self.area_id)
        region = ", ".join(
            part
            for part in (data.get("municipality", ""), data.get("province", ""))
            if part
        )
        self.area_info = {"name": data.get("name", ""), "region": region}
        return self.area_info

    async def async_get_area_information(self):
        """Fetches local loadshedding events and the stage schedule"""
        area_info = await self.async_get_area_info()
        if not self.schedule_id:
            # Entries whose schedule id could not be derived must still load,
            # so the options flow stays reachable (a repair issue prompts the
            # user to re-select their area)
            return esp_normalizers.v3_schedule_to_area_information(
                {"events": [], "schedule": {"days": []}}, area_info
            )
        # Query the API
        data = await self.async_query_api("/schedule", payload={"id": self.schedule_id})
        return esp_normalizers.v3_schedule_to_area_information(data, area_info)

    async def async_search_areas(self, area_search: str):
        """Searches for areas matching a search string"""
        # Query the API
        payload = {"text": area_search}
        return await self.async_query_api("/areas_search", payload=payload)

    async def async_get_data(self):
        """Fetches all relevant data from the loadshedding API"""
        # Quota headers are only as fresh as this cycle's responses
        self.latest_ratelimit = None

        status = await self.async_get_status()
        area_information = await self.async_get_area_information()

        # The v2 /api_allowance endpoint is deprecated (removed in v3.1);
        # quota now comes from the x-ratelimit-* headers on every response
        allowance = esp_normalizers.allowance_from_headers(self.latest_ratelimit)

        data = {
            "allowance": allowance,
            "status": status,
            "area_information": area_information,
        }
        return data
