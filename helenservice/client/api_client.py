import calendar
from cachetools import cached, TTLCache
import json
from datetime import datetime, timedelta
from helenservice.client.api_response import MeasurementResponse
from helenservice.client.const import HTTP_READ_TIMEOUT
from helenservice.client.helen_session import HelenSession
from requests import get
from dateutil.relativedelta import relativedelta


class HelenApiClient:
    HELEN_API_URL = "https://api.omahelen.fi/v7"
    MEASUREMENTS_ENDPOINT = "/measurements/electricity"
    CONTRACT_ENDPOINT = "/contract/list"

    _latest_login_time: datetime = None
    _session: HelenSession = None        

    def login(self, username, password):
        """Login to Oma Helen. Creates a new session when called."""
        self._session = HelenSession()
        self._session.login(username, password)
        self._latest_login_time = datetime.now()

    def is_session_valid(self):
        """If the latest login has happened within the last hour, then the session should be valid and ready to go"""
        if self._latest_login_time is None:
            return False
        now = datetime.now()
        is_latest_login_within_hour = now-timedelta(hours=1) <= self._latest_login_time <= now
        return is_latest_login_within_hour
            
    @cached(cache=TTLCache(maxsize=4, ttl=3600))
    def get_daily_measurements_by_month(self, month: int) -> MeasurementResponse:
        """Get electricity measurements for each day of the wanted month of the on-going year."""

        # The start_time is always the last day of the previous month
        wanted_month_first_day = datetime.today().replace(day=1, month=month)
        wanted_month_last_day = datetime.today().replace(day=calendar.monthrange(wanted_month_first_day.year, month)[-1], month=month)
        
        previous_month = wanted_month_last_day + relativedelta(months=-1)
        previous_month_last_day = previous_month.replace(day=calendar.monthrange(previous_month.year, previous_month.month)[-1])

        start_time = f"{previous_month_last_day.year}-{previous_month_last_day.month}-{previous_month_last_day.day}T21:00:00.000Z"
        end_time = f"{wanted_month_last_day.year}-{wanted_month_last_day.month}-{wanted_month_last_day.day}T20:59:59.999Z"
        delivery_site_id = self.get_delivery_site_id()
        measurements_params = {
            "begin": start_time,
            "end": end_time,
            "resolution": "day",
            "delivery_site_id": delivery_site_id,
            "allow_transfer": "true"
        }

        measurements_url = self.HELEN_API_URL + self.MEASUREMENTS_ENDPOINT
        response_json_text = get(
            measurements_url, measurements_params, headers=self._api_request_headers(), timeout=HTTP_READ_TIMEOUT).text
        daily_measurement: MeasurementResponse = MeasurementResponse(
            **json.loads(response_json_text))

        return daily_measurement

    @cached(cache=TTLCache(maxsize=2, ttl=3600))
    def get_monthly_measurements_by_year(self, year: int) -> MeasurementResponse:
        """Get electricity measurements for each month of the on-going year."""
        
        last_year = year-1
        start_time = f"{last_year}-12-31T22:00:00+00:00"
        end_time = f"{year}-12-31T21:59:59+00:00"
        delivery_site_id = self.get_delivery_site_id()
        measurements_params = {
            "begin": start_time,
            "end": end_time,
            "resolution": "month",
            "delivery_site_id": delivery_site_id,
            "allow_transfer": "true"
        }

        measurements_url = self.HELEN_API_URL + self.MEASUREMENTS_ENDPOINT
        response_json_text = get(
            measurements_url, measurements_params, headers=self._api_request_headers(), timeout=HTTP_READ_TIMEOUT).text
        monthly_measurement: MeasurementResponse = MeasurementResponse(
            **json.loads(response_json_text))

        return monthly_measurement
    
    @cached(cache=TTLCache(maxsize=2, ttl=3600))
    def get_contract_data_json(self):
        """Get your contract data."""

        contract_url = self.HELEN_API_URL + self.CONTRACT_ENDPOINT
        contract_response_dict = get(contract_url, headers=self._api_request_headers(), timeout=HTTP_READ_TIMEOUT).json()
        self._contract_data_dict = contract_response_dict
        return contract_response_dict

    def get_delivery_site_id(self) -> int:
        """Get the delivery site id from your contract data."""

        return self.get_contract_data_json()[0]["delivery_site"]["id"]

    def get_contract_base_price(self) -> int:
        """Get the contract base price from your contract data."""
        
        contract_data = self.get_contract_data_json()
        contract_components = contract_data[0]["products"][0]["components"]
        base_price_component = next(filter(lambda component: component["is_base_price"], contract_components))
        return base_price_component["price"]

    def get_api_access_token(self):
        return self._session.get_access_token()

    def _api_request_headers(self):
        return {
            "Authorization": f"Bearer {self.get_api_access_token()}",
            "Accept": "application/json"
        }
