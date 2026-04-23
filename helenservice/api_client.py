import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from cachetools import TTLCache, cachedmethod

from helenservice.api_exceptions import InvalidApiResponseException, InvalidDeliverySiteException

from .api_response import (
    MeasurementsWithSpotPriceResponse,
    SpotPriceChartResponse,
)
from .const import HTTP_READ_TIMEOUT, RESOLUTION_HOUR
from .helen_session import HelenSession


# TODO: consider moving all calculation functions somewhere else - they are not related to HelenApiClient
class HelenApiClient:
    HELEN_API_URL_V25 = "https://api.omahelen.fi/v25"
    HELEN_API_URL_V26 = "https://api.omahelen.fi/v26"
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
        self._cache = TTLCache(maxsize=128, ttl=3600)

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
        series = self.get_measurements_with_spot_prices(start_date, end_date, RESOLUTION_HOUR).series
        if not series:
            return []
        hourly_consumption_costs = []
        for entry in series:
            if entry.electricity is None or entry.electricity_spot_prices is None:
                continue
            hourly_price_with_tax_and_margin = entry.electricity_spot_prices * (1 + self._tax) + self._margin
            hourly_consumption_costs.append(abs(hourly_price_with_tax_and_margin * entry.electricity))
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
        series = self.get_daily_measurements_between_dates(start_date, end_date).series
        total_consumption = sum(abs(entry.electricity) for entry in series if entry.electricity is not None)
        return total_consumption

    def calculate_total_costs_by_spot_prices_between_dates(self, start_date: date, end_date: date):
        """Calculate your total electricity cost with according spot prices by hourly precision.
        Note: Spot prices include the user-configured tax and margin.

        Returns the price in euros
        """
        hourly_consumption_costs = self._get_hourly_consumption_costs(start_date, end_date)
        total_price = sum(hourly_consumption_costs)
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
        series = self.get_measurements_with_spot_prices(start_date, end_date, RESOLUTION_HOUR).series
        if not series:
            return 0.0
        valid_entries = [
            entry for entry in series if entry.electricity is not None and entry.electricity_spot_prices is not None
        ]
        if not valid_entries:
            return 0.0
        hourly_weighted_consumption_prices = [
            abs(entry.electricity_spot_prices * (1 + self._tax) * entry.electricity) for entry in valid_entries
        ]
        monthly_average_price = sum(
            abs(entry.electricity_spot_prices * (1 + self._tax)) for entry in valid_entries
        ) / len(valid_entries)
        total_consumption = sum(abs(entry.electricity) for entry in valid_entries)
        total_hourly_weighted_consumption_prices = sum(hourly_weighted_consumption_prices)
        total_consumption_average_price = monthly_average_price * total_consumption

        impact = (total_hourly_weighted_consumption_prices - total_consumption_average_price) / total_consumption

        return impact

    @cachedmethod(lambda self: self._cache)
    def get_daily_measurements_between_dates(self, start: date, end: date) -> MeasurementsWithSpotPriceResponse:
        """Get electricity measurements for each day between the given dates."""

        return self.get_measurements_with_spot_prices(start, end, resolution="day")

    @cachedmethod(lambda self: self._cache)
    def get_monthly_measurements_by_year(self, year: int) -> MeasurementsWithSpotPriceResponse:
        """Get electricity measurements for each month of the selected year."""

        start = date(year - 1, 12, 31)
        end = date(year, 12, 31)
        return self.get_measurements_with_spot_prices(start, end, resolution="month")

    @cachedmethod(lambda self: self._cache)
    def get_measurements_between_dates(
        self, start: date, end: date, resolution: str = RESOLUTION_HOUR
    ) -> MeasurementsWithSpotPriceResponse:
        """Get electricity measurements for each hour or quarter between given dates."""

        return self.get_measurements_with_spot_prices(start, end, resolution)

    @cachedmethod(lambda self: self._cache)
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
        start_time, end_time = self._get_utc_time_range(start, end)

        gsrn_id = self._selected_contract["gsrn"]

        chart_params = {"start": start_time, "stop": end_time, "resolution": resolution, "channel": "oh"}

        chart_url = f"{self.HELEN_API_URL_V26}/chart-data/{gsrn_id}/electricity"
        response = requests.get(
            chart_url,
            params=chart_params,
            headers=self._api_request_headers(),
            timeout=HTTP_READ_TIMEOUT,
        )

        return MeasurementsWithSpotPriceResponse(**response.json())

    @cachedmethod(lambda self: self._cache)
    def get_spot_prices_from_chart_data(self, target_date: date) -> SpotPriceChartResponse:
        """Get electricity spot prices from chart data API for a single day. Returns data in 15-minute intervals.

        Args:
            target_date: The target date to get spot prices for

        Returns:
            SpotPriceChartResponse object containing the full data structure.
        """
        start_time, end_time = self._get_utc_time_range(target_date, target_date)

        chart_params = {"start": start_time, "stop": end_time}

        chart_url = self.HELEN_API_URL_V25 + self.SPOT_PRICES_CHART_ENDPOINT
        response = requests.get(
            chart_url,
            params=chart_params,
            headers=self._api_request_headers(),
            timeout=HTTP_READ_TIMEOUT,
        )

        return SpotPriceChartResponse(**response.json())

    @cachedmethod(lambda self: self._cache)
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
        self._cache.clear()

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

    def _get_utc_time_range(self, start_date: date, end_date: date) -> tuple[str, str]:
        """
        Convert a local date range to UTC midnight boundaries, matching the Oma Helen API.

        The API uses midnight Helsinki time as interval boundaries. Because Helsinki is
        UTC+2 (winter) or UTC+3 (summer), midnight of a given date in Helsinki maps to
        21:00Z or 22:00Z of the *previous* UTC calendar day. Both start and stop use
        this convention, producing a half-open interval [start_date, end_date+1).

        Args:
            start_date: First day of the range (inclusive)
            end_date: Last day of the range (inclusive)

        Returns:
            tuple of (start_time, stop_time) as ISO 8601 strings with UTC offset.
        """
        fi_tz = ZoneInfo("Europe/Helsinki")
        # Midnight of start_date in Helsinki (= 21:00Z or 22:00Z of the previous UTC day)
        local_start = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=fi_tz)
        # Midnight of the day after end_date in Helsinki (exclusive upper bound)
        local_end = datetime.combine(end_date + timedelta(days=1), datetime.min.time()).replace(tzinfo=fi_tz)

        utc_start = local_start.astimezone(ZoneInfo("UTC"))
        utc_end = local_end.astimezone(ZoneInfo("UTC"))

        return (utc_start.isoformat(), utc_end.isoformat())
