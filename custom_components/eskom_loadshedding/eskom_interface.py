import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class eskom_interface:
    """Interface class to obtain loadshedding information using the Eskom API"""

    def __init__(self):
        """Initializes class parameters"""

        self.base_url = "http://loadshedding.eskom.co.za/LoadShedding"
        self.headers = {
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64; rv:69.0) Gecko/20100101 Firefox/69.0"
        }
        self.session = requests.Session()
        self.retries = Retry(
            total=5, backoff_factor=1, status_forcelist=[502, 503, 504]
        )
        self.session.mount("http://", HTTPAdapter(max_retries=self.retries))

    def query_api(self, endpoint, payload=None):
        """Queries a given endpoint on the Eskom loadshedding API with the specified payload

        Args:
            endpoint (string): The endpoint of the Eskom API
            payload (dict, optional): The parameters to apply to the query. Defaults to None.

        Returns:
            The response object from the request
        """

        res = self.session.get(
            self.base_url + endpoint, headers=self.headers, params=payload
        )
        return res

    def get_stage(self, attempts=5):
        """Fetches the current loadshedding stage from the Eskom API

        Args:
            attempts (int, optional): The number of attempts to query a sane value from the Eskom API. Defaults to 5.

        Returns:
            The loadshedding stage if the query succeeded, else `None`
        """

        # Query the API until a sensible (> 0) value is received, or the number of attempts is exceeded
        for attempt in range(attempts):
            res = self.query_api("/GetStatus")

            # Return the current loadshedding stage by subtracting 1 from the query result
            # Occasionally the Eskom API will return a negative stage, so simply retry if this occurs
            if res and int(res.text) > 0:
                return int(res.text) - 1

        # If the query does not succeed after the number of attempts has been exceeded, raise an exception
        raise Exception(
            f"Error, invalid loadshedding stage received from API after {attempts} attempts"
        )

    def get_data(self):
        """Fetches data from the loadshedding API"""
        stage = self.get_stage()
        data = {
            "data": {"stage": stage},
        }
        return data
