import json
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from cachetools import TTLCache, cached

from helenservice.api_exceptions import InvalidApiResponseException, InvalidDeliverySiteException

from .api_response import (
    MeasurementResponse,
    MeasurementsWithSpotPriceResponse,
    SpotPriceChartResponse,
    SpotPricesResponse,
)
from .const import HTTP_READ_TIMEOUT, RESOLUTION_HOUR
from .helen_session import HelenSession


# TODO: consider moving all calculation functions somewhere else - they are not related to HelenApiClient
class HelenApiClient:
    HELEN_API_URL_V25 = "https://api.omahelen.fi/v25"
    MEASUREMENTS_ENDPOINT = "/measurements/electricity"
    TRANSFER_ENDPOINT = "/measurements/electricity-transfer"
    SPOT_PRICES_ENDPOINT = MEASUREMENTS_ENDPOINT + "/spot-prices"
    SPOT_PRICES_CHART_ENDPOINT = "/chart-data/electricity/spot-prices/daily"
    CONTRACT_ENDPOINT = "/contract/list"

    _latest_login_time: datetime = None
    _session: HelenSession = None
    _margin: float = None
    _selected_delivery_site_id: str = None
    _selected_contract = None
    _all_active_contracts = None

    def __init__(self, tax: float = None, margin: float = None):
        self._tax = 0.255 if tax is None else tax
        self._margin = 0.38 if margin is None else margin

    def login_and_init(self, username, password):
        """Login to Oma Helen. Creates a new session when called."""
        self._session = HelenSession().login(username, password)
        self._latest_login_time = datetime.now()
        self._refresh_api_client_state()
        return self

    def is_session_valid(self):
        """If the latest login has happened within the last hour, then the session should be valid and ready to go"""
        if self._latest_login_time is None:
            return False
        now = datetime.now()
        is_latest_login_within_hour = now - timedelta(hours=1) <= self._latest_login_time <= now
        return is_latest_login_within_hour

    def close(self):
        if self._session is not None:
            self._session.close()

    def _get_hourly_consumption_costs(self, start_date: date, end_date: date) -> list:
        hourly_prices_response = self.get_spot_prices_between_dates(start_date, end_date, RESOLUTION_HOUR)
        if not hourly_prices_response.interval:
            return []
        # retain the hourly-price/hourly-measurement pairs (list ordering matters!) by assigning invalid items None
        hourly_prices = list(
            map(
                lambda price: price if price.status == 'valid' else None,
                hourly_prices_response.interval.measurements,
            )
        )
        hourly_measurements_data = self.get_measurements_between_dates(
            start_date, end_date, RESOLUTION_HOUR
        ).intervals.electricity
        if not hourly_measurements_data:
            return []
        hourly_measurements = list(
            map(
                lambda measurement: measurement if measurement.status == 'valid' else None,
                hourly_measurements_data[0].measurements,
            )
        )
        length = min(hourly_prices.__len__(), hourly_measurements.__len__())
        if length == 0:
            return []
        hourly_consumption_costs = []
        for i in range(length):
            hourly_price = hourly_prices[i]
            hourly_measurement = hourly_measurements[i]
            if hourly_price is None or hourly_measurement is None:
                continue
            hourly_price_with_tax_and_margin = hourly_price.value + self._margin
            hourly_consumption_costs.append(abs(hourly_price_with_tax_and_margin * hourly_measurement.value))
        return hourly_consumption_costs

    def calculate_transfer_fees_between_dates(self, start_date: date, end_date: date):
        """Calculate your total transfer fee costs including the monthly base price

        Returns the price in euros
        """
        total_consumption = self.get_total_consumption_between_dates(start_date, end_date)
        transfer_fee = self.get_transfer_fee()
        total_price = total_consumption * transfer_fee
        total_price_in_euros = total_price / 100 + self.get_transfer_base_price()
        return total_price_in_euros

    def get_total_consumption_between_dates(self, start_date: date, end_date: date) -> float:
        daily_measurements_response = self.get_daily_measurements_between_dates(start_date, end_date)
        daily_measurements = list(
            filter(
                lambda measurement: measurement.status == 'valid',
                daily_measurements_response.intervals.electricity[0].measurements,
            )
        )
        total_consumption = sum(map(lambda measurement: abs(measurement.value), daily_measurements))
        return total_consumption

    def calculate_total_costs_by_spot_prices_between_dates(self, start_date: date, end_date: date):
        """Calculate your total electricity cost with according spot prices by hourly precision.
        Note: Spot prices already include tax from get_spot_prices_between_dates.

        Returns the price in euros
        """
        hourly_consumption_costs = self._get_hourly_consumption_costs(start_date, end_date)
        total_price = sum(hourly_consumption_costs)
        # Prices already include tax from get_spot_prices_between_dates
        total_price_in_euros = total_price / 100
        return total_price_in_euros

    def calculate_impact_of_usage_between_dates(self, start_date: date, end_date: date) -> float:
        """Calculate the price impact of your usage based on hourly consumption and hourly spot prices

        The price impact increases or decreases your contract's unit price in certain contracts
        such as the Helen Smart Electricity Guarantee contract
        https://www.helen.fi/en/electricity/electricity-products-and-prices/smart-electricity-guarantee
        A negative number decreases and a positive number increases the base price.

        According to Helen, the impact is calculated with formula (A-B) / E = c/kWh, where
        A = the sum of hourly consumption multiplied with the hourly price (i.e. your weighted average price of each hour)
        B = total consumption multiplied with the whole month's average market price (i.e. your average price of the whole month)
        E = total consumption
        """
        hourly_prices_response = self.get_spot_prices_between_dates(start_date, end_date, RESOLUTION_HOUR)
        if not hourly_prices_response.interval:
            return 0.0
        # retain the hourly-price/hourly-measurement pairs (list ordering matters!) by assigning invalid items None
        hourly_prices = list(
            map(
                lambda price: price if price.status == 'valid' else None,
                hourly_prices_response.interval.measurements,
            )
        )
        hourly_measurements_response = self.get_measurements_between_dates(start_date, end_date, RESOLUTION_HOUR)
        if not hourly_measurements_response.intervals or not hourly_measurements_response.intervals.electricity:
            return 0.0
        hourly_measurements = list(
            map(
                lambda measurement: measurement if measurement.status == 'valid' else None,
                hourly_measurements_response.intervals.electricity[0].measurements,
            )
        )
        length = min(hourly_prices.__len__(), hourly_measurements.__len__())
        if length == 0:
            return 0.0
        hourly_prices_without_nones = list(filter(lambda price: price is not None, hourly_prices))
        hourly_measurements_without_nones = list(
            filter(lambda measurement: measurement is not None, hourly_measurements)
        )
        hourly_weighted_consumption_prices = []
        for i in range(length):
            hourly_price = hourly_prices[i]
            hourly_measurement = hourly_measurements[i]
            if hourly_price is None or hourly_measurement is None:
                continue
            hourly_weighted_consumption_prices.append(abs(hourly_price.value * hourly_measurement.value))
        if not hourly_weighted_consumption_prices:
            return 0.0
        monthly_average_price = (
            sum(map(lambda price: abs(price.value), hourly_prices_without_nones))
            / hourly_prices_without_nones.__len__()
        )
        total_consumption = sum(map(lambda measurement: abs(measurement.value), hourly_measurements_without_nones))
        total_hourly_weighted_consumption_prices = sum(hourly_weighted_consumption_prices)
        total_consumption_average_price = monthly_average_price * total_consumption

        impact = (total_hourly_weighted_consumption_prices - total_consumption_average_price) / total_consumption

        return impact

    @cached(cache=TTLCache(maxsize=4, ttl=3600))
    def get_daily_measurements_between_dates(self, start: date, end: date) -> MeasurementResponse:
        """Get electricity measurements for each day of the wanted month of the on-going year."""

        start_time, end_time = self._get_utc_time_range(start, end)
        delivery_site_id = self._get_selected_delivery_site_id_for_api()
        measurements_params = {
            "begin": start_time,
            "end": end_time,
            "resolution": "day",
            "delivery_site_id": delivery_site_id,
            "allow_transfer": "true",
        }

        measurements_url = self._get_measurements_endpoint()

        response_json_text = requests.get(
            measurements_url,
            params=measurements_params,
            headers=self._api_request_headers(),
            timeout=HTTP_READ_TIMEOUT,
        ).text
        daily_measurement: MeasurementResponse = MeasurementResponse(**json.loads(response_json_text))

        return daily_measurement

    @cached(cache=TTLCache(maxsize=2, ttl=3600))
    def get_monthly_measurements_by_year(self, year: int) -> MeasurementResponse:
        """Get electricity measurements for each month of the selected year."""

        last_year = year - 1
        start_time = f"{last_year}-12-31T22:00:00+00:00"
        end_time = f"{year}-12-31T21:59:59+00:00"
        delivery_site_id = self._get_selected_delivery_site_id_for_api()
        measurements_params = {
            "begin": start_time,
            "end": end_time,
            "resolution": "month",
            "delivery_site_id": delivery_site_id,
            "allow_transfer": "true",
        }

        measurements_url = self._get_measurements_endpoint()
        response_json_text = requests.get(
            measurements_url,
            params=measurements_params,
            headers=self._api_request_headers(),
            timeout=HTTP_READ_TIMEOUT,
        ).text
        monthly_measurement: MeasurementResponse = MeasurementResponse(**json.loads(response_json_text))

        return monthly_measurement

    @cached(cache=TTLCache(maxsize=4, ttl=3600))
    def get_measurements_between_dates(
        self, start: date, end: date, resolution: str = RESOLUTION_HOUR
    ) -> MeasurementResponse:
        """Get electricity measurements for each hour or quarter between given dates."""

        start_time, end_time = self._get_utc_time_range(start, end)
        delivery_site_id = self._get_selected_delivery_site_id_for_api()
        measurements_params = {
            "begin": start_time,
            "end": end_time,
            "resolution": resolution,
            "delivery_site_id": delivery_site_id,
            "allow_transfer": "true",
        }

        measurements_url = self._get_measurements_endpoint()
        response_json_text = requests.get(
            measurements_url,
            params=measurements_params,
            headers=self._api_request_headers(),
            timeout=HTTP_READ_TIMEOUT,
        ).text
        hourly_measurement: MeasurementResponse = MeasurementResponse(**json.loads(response_json_text))

        return hourly_measurement

    @cached(cache=TTLCache(maxsize=4, ttl=3600))
    def get_measurements_with_spot_prices(
        self, start: date, end: date, resolution: str = RESOLUTION_HOUR
    ) -> MeasurementsWithSpotPriceResponse:
        """Get electricity measurements with spot prices for a specific GSRN between given dates.

        Args:
            start: The start date
            end: The end date
            resolution: The resolution (default: "hour")

        Returns:
            MeasurementsWithSpotPriceResponse object containing measurements and spot prices.
        """
        start_time, end_time = self._get_utc_time_range(start, end, round_to_full_hour=True)

        gsrn_id = self._selected_contract["gsrn"]

        chart_params = {"start": start_time, "stop": end_time, "resolution": resolution, "channel": "oh"}

        chart_url = f"{self.HELEN_API_URL_V25}/chart-data/{gsrn_id}/electricity"
        response = requests.get(
            chart_url,
            params=chart_params,
            headers=self._api_request_headers(),
            timeout=HTTP_READ_TIMEOUT,
        )

        return MeasurementsWithSpotPriceResponse(**response.json())

    @cached(cache=TTLCache(maxsize=4, ttl=3600))
    def get_spot_prices_from_chart_data(self, target_date: date) -> SpotPriceChartResponse:
        """Get electricity spot prices from chart data API for a single day. Returns data in 15-minute intervals.

        Args:
            target_date: The target date to get spot prices for

        Returns:
            SpotPriceChartResponse object containing the full data structure.
        """
        start_time, end_time = self._get_utc_time_range(target_date, target_date, round_to_full_hour=True)

        chart_params = {"start": start_time, "stop": end_time}

        chart_url = self.HELEN_API_URL_V25 + self.SPOT_PRICES_CHART_ENDPOINT
        response = requests.get(
            chart_url,
            params=chart_params,
            headers=self._api_request_headers(),
            timeout=HTTP_READ_TIMEOUT,
        )

        return SpotPriceChartResponse(**response.json())

    @cached(cache=TTLCache(maxsize=4, ttl=3600))
    def get_spot_prices_between_dates(
        self, start: date, end: date, resolution: str = RESOLUTION_HOUR
    ) -> SpotPricesResponse:
        """Get electricity spot prices for each hour between given dates. Values include tax."""

        start_time, end_time = self._get_utc_time_range(start, end)
        delivery_site_id = self._get_selected_delivery_site_id_for_api()
        spot_prices_params = {
            "begin": start_time,
            "end": end_time,
            "resolution": resolution,
            "delivery_site_id": delivery_site_id,
            "allow_transfer": "true",
        }

        spot_prices_url = self.HELEN_API_URL_V25 + self.SPOT_PRICES_ENDPOINT
        response_json_text = requests.get(
            spot_prices_url,
            params=spot_prices_params,
            headers=self._api_request_headers(),
            timeout=HTTP_READ_TIMEOUT,
        ).text
        spot_prices_measurement: SpotPricesResponse = SpotPricesResponse(**json.loads(response_json_text))

        # Add tax to each price value
        if spot_prices_measurement.interval and spot_prices_measurement.interval.measurements:
            for measurement in spot_prices_measurement.interval.measurements:
                if measurement.status == 'valid' and measurement.value is not None:
                    measurement.value = measurement.value * (1 + self._tax)

        return spot_prices_measurement

    @cached(cache=TTLCache(maxsize=2, ttl=3600))
    def get_contract_data_json(self):
        """Get your contract data."""

        contract_url = self.HELEN_API_URL_V25 + self.CONTRACT_ENDPOINT
        contract_params = {"include_transfer": "true", "update": "true", "include_products": "true"}
        contract_response_dict = requests.get(
            contract_url,
            headers=self._api_request_headers(),
            timeout=HTTP_READ_TIMEOUT,
            params=contract_params,
        ).json()
        contracts_dict = contract_response_dict["contracts"]

        return contracts_dict

    def _get_selected_delivery_site_id_for_api(self):
        return str(self._selected_contract["delivery_site"]["id"])

    def get_all_delivery_site_ids(self) -> list[int]:
        """Get all delivery site ids from your contracts."""

        self._refresh_api_client_state()
        delivery_sites = list(map(lambda contract: str(contract["delivery_site"]["id"]), self._all_active_contracts))
        return delivery_sites

    def get_all_gsrn_ids(self) -> list[int]:
        """Get all GSRN ids from your contracts."""

        self._refresh_api_client_state()
        gsrn_ids = list(map(lambda contract: str(contract["gsrn"]), self._all_active_contracts))
        return gsrn_ids

    def select_delivery_site_if_valid_id(self, delivery_site_id: str = None):
        """Select a delivery site to be used when querying data."""
        delivery_sites = self.get_all_delivery_site_ids()
        gsrn_ids = self.get_all_gsrn_ids()
        found_delivery_site_id = next(filter(lambda id: str(id) == delivery_site_id, delivery_sites), None)
        if not found_delivery_site_id:
            found_delivery_site_id = next(filter(lambda id: str(id) == delivery_site_id, gsrn_ids), None)
        if not found_delivery_site_id:
            raise InvalidDeliverySiteException(
                f"Cannot select {delivery_site_id} because it does not exist in the active delivery sites list {delivery_sites} or GSRN id list {gsrn_ids}"
            )
        self._selected_delivery_site_id = str(found_delivery_site_id)
        self._refresh_api_client_state()
        self._invalidate_caches()
        logging.warning("Delivery site set to '%s'", delivery_site_id)

    def get_contract_base_price(self) -> float:
        """Get the contract base price from your contract data."""

        self._refresh_api_client_state()
        contract = self._selected_contract
        if not contract:
            raise InvalidApiResponseException("Contract data is empty or None")
        products = contract["products"] if contract else []
        product = next(filter(lambda p: p["product_type"] == "energy", products), None)
        if not product:
            logging.warning("Could not resolve contract base price from Helen API response. Returning 0.0")
            return 0.0
        components = product["components"] if product else []
        base_price_component = next(filter(lambda component: component["is_base_price"], components), None)
        if not base_price_component:
            logging.warning("Could not resolve contract base price from Helen API response. Returning 0.0")
            return 0.0
        return base_price_component["price"]

    def get_contract_type(self) -> str:
        """Get the contract type as a string from your contract data."""

        self._refresh_api_client_state()
        contract = self._selected_contract
        if not contract:
            raise InvalidApiResponseException("Contract data is empty or None")
        products = contract["products"] if contract else []
        product = next(filter(lambda p: p["product_type"] == "energy", products), None)
        if not product:
            logging.warning("Could not resolve contract type from Helen API response. Returning None")
            return None
        return product["id"]

    def get_contract_energy_unit_price(self) -> float:
        """
        Get the fixed unit price for electricity from your contract data. Returns '0.0' for spot electricity contracts
        because the price is not fixed in your contract when using spot.
        """

        self._refresh_api_client_state()
        contract = self._selected_contract
        if not contract:
            raise InvalidApiResponseException("Contract data is empty or None")
        products = contract["products"] if contract else []
        product = next(filter(lambda p: p["product_type"] == "energy", products), None)
        if not product:
            logging.warning("Could not resolve energy price from Helen API response. Returning 0.0")
            return 0.0
        if not product:
            raise InvalidApiResponseException("Product data is empty or None")
        components = product["components"] if product else []
        energy_unit_price_component = next(filter(lambda component: component["name"] == "Energia", components), None)
        if not energy_unit_price_component:
            logging.warning("Could not resolve energy price from Helen API response. Returning 0.0")
            return 0.0
        return energy_unit_price_component["price"]

    def get_transfer_fee(self) -> float:
        """Get the transfer fee price (c/kWh) from your contract data. Returns '0.0' if Helen is not your transfer company"""

        self._refresh_api_client_state()
        contract = self._selected_contract
        if not contract:
            raise InvalidApiResponseException("Contract data is empty or None")
        products = contract["products"] if contract else []
        product = next(filter(lambda p: p["product_type"] == "transfer", products), None)
        if not product:
            logging.warning("Could not resolve transfer fees from Helen API response. Returning 0.0")
            return 0.0
        components = product["components"] if product else []
        transfer_fee_component = next(filter(lambda component: component["name"] == "Siirtomaksu", components), None)
        if transfer_fee_component is None:
            logging.warning("Could not resolve transfer fees from Helen API response. Returning 0.0")
            return 0.0
        return transfer_fee_component["price"]

    def get_transfer_base_price(self) -> float:
        """Get the transfer base price (eur) from your contract data. Returns '0.0' if Helen is not your transfer company"""

        self._refresh_api_client_state()
        contract = self._selected_contract
        if not contract:
            raise InvalidApiResponseException("Contract data is empty or None")
        products = contract["products"] if contract else []
        product = next(filter(lambda p: p["product_type"] == "transfer", products), None)
        if not product:
            logging.warning("Could not resolve transfer base price from Helen API response. Returning 0.0")
            return 0.0
        components = product["components"] if product else []
        transfer_base_price_component = next(filter(lambda component: component["is_base_price"], components), None)
        if transfer_base_price_component is None:
            logging.warning("Could not resolve transfer base price from Helen API response. Returning 0.0")
            return 0.0
        return transfer_base_price_component["price"]

    def get_api_access_token(self):
        return self._session.get_access_token()

    def _refresh_api_client_state(self):
        contracts = self.get_contract_data_json()
        self._all_active_contracts = self._get_all_active_contracts(contracts)

        if self._selected_delivery_site_id is None:
            latest_active_contract = self._get_latest_contract(self._all_active_contracts)
            self._selected_contract = latest_active_contract
            self._selected_delivery_site_id = latest_active_contract["gsrn"]
        else:
            selected_active_contract = self._get_contract_by_delivery_site_id(self._all_active_contracts)
            self._selected_contract = selected_active_contract

    def _invalidate_caches(self):
        self.get_daily_measurements_between_dates.cache_clear()
        self.get_monthly_measurements_by_year.cache_clear()
        self.get_measurements_between_dates.cache_clear()
        self.get_spot_prices_between_dates.cache_clear()
        self.get_contract_data_json.cache_clear()
        self.get_spot_prices_from_chart_data.cache_clear()

    def _api_request_headers(self):
        return {
            "Authorization": f"Bearer {self.get_api_access_token()}",
            "Accept": "application/json",
        }

    def set_margin(self, margin: float):
        self._margin = margin

    def _get_all_active_contracts(self, contracts):
        """
        Find all active contracts from a list of contracts.
        A contract is considered active if:
        - It has no end_date or end_date is in the future
        - Its start_date is not in the future
        - Its domain is not 'electricity-production'
        """
        now = datetime.now()

        def is_active_contract(contract):
            # Check if contract has started (start_date is not in future)
            start_date = datetime.strptime(contract["start_date"], '%Y-%m-%dT%H:%M:%S')
            if start_date > now:
                return False

            # Check if contract hasn't ended (end_date is None or in future)
            end_date_str = contract.get("end_date")
            if end_date_str is not None:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M:%S')
                if end_date < now:
                    return False

            # Check domain
            return contract.get("domain") != "electricity-production"

        return list(filter(is_active_contract, contracts))

    def _get_contract_by_delivery_site_id(self, contracts):
        """
        Finds a contract from a list of contracts by delivery_site_id.
        """
        active_contracts = self._get_all_active_contracts(contracts)
        if self._selected_delivery_site_id:
            if len(str(self._selected_delivery_site_id)) == 18:
                active_contracts = list(
                    filter(
                        lambda contract: contract["gsrn"] == str(self._selected_delivery_site_id),
                        active_contracts,
                    )
                )
            else:
                active_contracts = list(
                    filter(
                        lambda contract: str(contract["delivery_site"]["id"]) == str(self._selected_delivery_site_id),
                        active_contracts,
                    )
                )
        if active_contracts.__len__() > 1:
            logging.debug("Found multiple active Helen contracts. Using the newest one.")
            active_contracts.sort(
                key=lambda contract: datetime.strptime(contract["start_date"], '%Y-%m-%dT%H:%M:%S'),
                reverse=True,
            )
        if active_contracts.__len__() == 0:
            logging.error("No active contracts found")
            return None
        return active_contracts[0]

    def _get_latest_contract(self, contracts):
        """
        Resolves the latest contract from a list of contracts.
        """
        if contracts.__len__() == 0:
            logging.error("No contracts found")
            return None
        contracts.sort(
            key=lambda contract: datetime.strptime(contract["start_date"], '%Y-%m-%dT%H:%M:%S'),
            reverse=True,
        )
        return contracts[0]

    def _date_is_now_or_later(self, end_date_str):
        end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M:%S')
        now = datetime.now()
        return end_date >= now

    def _get_measurements_endpoint(self):
        if 'domain' in self._selected_contract and self._selected_contract['domain'] == 'electricity-transfer':
            return self.HELEN_API_URL_V25 + self.TRANSFER_ENDPOINT
        return self.HELEN_API_URL_V25 + self.MEASUREMENTS_ENDPOINT

    def _get_utc_time_range(
        self, start_date: date, end_date: date, round_to_full_hour: bool = False
    ) -> tuple[str, str]:
        """
        Convert local midnight times to UTC considering DST.

        Args:
            start_date: The start date
            end_date: The end date
            round_to_full_hour: If True, rounds the end time up to the next full hour (HH:00:00),
                            used for chart data API. If False, uses millisecond precision (default).

        Returns:
            tuple of (start_time, end_time) in ISO format with UTC offset.
        """
        # Create datetime objects in Finland timezone
        fi_tz = ZoneInfo("Europe/Helsinki")
        # Start time is previous day 00:00 local time
        local_start = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=fi_tz)
        # End time is end date 23:59:59.999 local time
        local_end = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=fi_tz)

        # Convert to UTC
        utc_start = local_start.astimezone(ZoneInfo("UTC"))
        utc_end = local_end.astimezone(ZoneInfo("UTC"))

        if round_to_full_hour:
            # Round up to the next full hour for the end time if needed
            if utc_end.minute > 0 or utc_end.second > 0 or utc_end.microsecond > 0:
                utc_end = (utc_end + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            return (utc_start.isoformat(), utc_end.isoformat())
        else:
            # Format with millisecond precision for other APIs
            return (
                utc_start.isoformat(timespec='milliseconds'),
                utc_end.replace(microsecond=999000).isoformat(timespec='milliseconds'),
            )
