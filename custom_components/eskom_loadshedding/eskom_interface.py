import logging
import socket

import aiohttp

from .const import BASE_API_URL, REQUEST_TIMEOUT_S  # pylint: disable=unused-import

_LOGGER: logging.Logger = logging.getLogger(__package__)


class EskomInterface:
    """Interface class to obtain loadshedding information using the EskomSePush API"""

    def __init__(
        self, session: aiohttp.ClientSession, api_key: str, area_id: str = None
    ):
        """Initializes class parameters"""
        self.session = session
        self.api_key = api_key
        self.area_id = area_id
        self.base_url = BASE_API_URL
        self.headers = {
            "Token": api_key,
        }

    async def async_query_api(self, endpoint: str, payload: dict = None):
        """
        Queries a given endpoint on the EskomSePush API with the specified payload

        Args:
            endpoint (string): The endpoint of the EskomSePush API
            payload (dict, optional): The parameters to apply to the query. Defaults to None.

        Returns:
            The response object from the request

        """
        query_url = self.base_url + endpoint
        try:
            async with self.session.get(
                url=query_url,
                headers=self.headers,
                params=payload,
                timeout=REQUEST_TIMEOUT_S,
            ) as resp:
                return await resp.json()
        except aiohttp.ClientResponseError as exception:
            _LOGGER.error(
                "Error fetching information from %s. Response code: %s",
                query_url,
                exception.status,
            )
            # Re-raise the ClientResponseError to allow checking for valid headers during config
            # These will be caught by the DataUpdateCoordinator
            raise
        except TimeoutError as exception:
            _LOGGER.error(
                "Timeout fetching information from %s: %s",
                query_url,
                exception,
            )
        except (KeyError, TypeError) as exception:
            _LOGGER.error(
                "Error parsing information from %s: %s",
                query_url,
                exception,
            )
        except (aiohttp.ClientError, socket.gaierror) as exception:
            _LOGGER.error(
                "Error fetching information from %s: %s",
                query_url,
                exception,
            )

    async def async_get_status(self) -> dict:
        """Fetches the current loadshedding status"""
        # Query the API
        return await self.async_query_api("/status")

    async def async_get_allowance(self):
        """Fetches the current API allowance"""
        # Query the API
        return await self.async_query_api("/api_allowance")

    async def async_get_area_information(self):
        """Fetches local loadshedding event information"""
        # Query the API
        payload = {"id": self.area_id}
        return await self.async_query_api("/area", payload=payload)

    async def async_search_areas(self, area_search: str):
        """Searches for areas matching a search string"""
        # Query the API
        payload = {"text": area_search}
        return await self.async_query_api("/areas_search", payload=payload)

    async def async_get_data(self):
        """Fetches all relevant data from the loadshedding API"""
        allowance = await self.async_get_allowance()
        status = await self.async_get_status()
        area_information = await self.async_get_area_information()

        data = {
            "allowance": allowance,
            "status": status,
            "area_information": area_information,
        }
        return data
