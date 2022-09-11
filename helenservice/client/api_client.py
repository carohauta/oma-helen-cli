from datetime import date
import json
from helenservice.client.api_response import MonthlyMeasurementResponse
from helenservice.client.helen_session import HelenSession
from requests import get


class HelenApiClient:
    HELEN_API_URL = "https://api.omahelen.fi/v7"
    MEASUREMENTS_ENDPOINT = "/measurements/electricity"
    CONTRACT_ENDPOINT = "/contract/list"

    contract_data_dict = None

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
        constract_response_dict = get(contract_url, headers=headers).json()
        self.contract_data_dict = constract_response_dict
        return constract_response_dict

    def get_delivery_site_id(self) -> int:
        """Get the delivery site id from your contract data."""

        if self.contract_data_dict is not None:
            return self.contract_data_dict[0]["delivery_site"]["id"]
        else: 
            return self.get_contract_data_json()[0]["delivery_site"]["id"]

    def get_contract_base_price(self) -> int:
        """Get the contract base price from your contract data."""
        
        contract_data = None
        if self.contract_data_dict is not None:
            contract_data = self.contract_data_dict
        else: 
            contract_data = self.get_contract_data_json()
        contract_components = contract_data[0]["products"][0]["components"]
        base_price_component = next(filter(lambda component: component["is_base_price"], contract_components))
        return base_price_component["price"]
        
