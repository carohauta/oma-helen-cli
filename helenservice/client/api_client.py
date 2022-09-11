from datetime import date
import json
from helenservice.client.api_response import MonthlyMeasurementResponse
from helenservice.client.helen_session import HelenSession
from requests import get


class HelenApiClient:
    HELEN_API_URL = "https://api.omahelen.fi/v7"
    MEASUREMENTS_ENDPOINT = "/measurements/electricity"
    CONTRACT_ENDPOINT = "/contract/list"

    def __init__(self):
        self.session = HelenSession()

    def login(self, username, password):
        self.session.login(username, password)

    def get_monthly_measurements(self) -> MonthlyMeasurementResponse:
        """Get electricity measurements for each month of the on-going year."""

        year = date.today().year
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
        headers = {
            "Authorization": f"Bearer {self.session.get_access_token()}",
            "Accept": "application/json"
        }
        response_json_text = get(
            measurements_url, measurements_params, headers=headers).text
        monthly_measurement: MonthlyMeasurementResponse = MonthlyMeasurementResponse(
            **json.loads(response_json_text))

        return monthly_measurement

    def get_contract_data_json(self):
        """Get your contract data."""

        contract_url = self.HELEN_API_URL + self.CONTRACT_ENDPOINT
        headers = {
            "Authorization": f"Bearer {self.session.get_access_token()}",
            "Accept": "application/json"
        }
        return get(contract_url, headers=headers).json()

    def get_delivery_site_id(self) -> int:
        """Get the delivery site id from your contract data."""

        contract_data_json = self.get_contract_data_json()
        return contract_data_json[0]["delivery_site"]["id"]
