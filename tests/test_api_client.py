import json
from datetime import date
from unittest.mock import Mock, patch

import pytest

from helenservice.api_client import HelenApiClient
from helenservice.api_exceptions import InvalidApiResponseException
from helenservice.api_response import MeasurementsWithSpotPriceResponse, SpotPriceChartResponse
from helenservice.const import HTTP_READ_TIMEOUT, RESOLUTION_HOUR


class TestHelenApiClient:
    """Test cases for HelenApiClient methods."""

    @pytest.fixture
    def api_client(self):
        """Create a test API client instance."""
        client = HelenApiClient()
        # Mock the session to avoid authentication requirements
        client._session = Mock()
        client._session.get_access_token.return_value = "mock_token"
        client._selected_delivery_site_id = "123456789"
        client._selected_contract = {"delivery_site": {"id": "123456789"}, "domain": None, "gsrn": "643007572123456789"}
        client._all_active_contracts = [client._selected_contract]
        return client

    @pytest.fixture
    def api_client_transfer(self, api_client):
        """API client whose selected contract is electricity-transfer only."""
        api_client._selected_contract["domain"] = "electricity-transfer"
        return api_client

    def test_get_daily_measurements_between_dates(self, api_client):
        with patch("requests.get", return_value=self._mock_response(self._load("measurement_spot_day_response.json"))) as mock_get:
            result = api_client.get_daily_measurements_between_dates(date(2025, 9, 7), date(2025, 10, 8))

        self._assert_v28_chart_data_call(mock_get, resolution="day")
        assert isinstance(result, MeasurementsWithSpotPriceResponse)
        assert result.resolution == "day"
        assert len(result.series) > 0

    def test_get_measurements_between_dates_hourly(self, api_client):
        with patch("requests.get", return_value=self._mock_response(self._load("measurement_spot_hour_response.json"))) as mock_get:
            result = api_client.get_measurements_between_dates(date(2025, 9, 7), date(2025, 9, 8), RESOLUTION_HOUR)

        self._assert_v28_chart_data_call(mock_get, resolution="hour")
        assert isinstance(result, MeasurementsWithSpotPriceResponse)
        assert result.resolution == "hour"
        assert len(result.series) > 0

    def test_get_monthly_measurements_by_year(self, api_client):
        with patch("requests.get", return_value=self._mock_response(self._load("measurement_spot_day_response.json"))) as mock_get:
            result = api_client.get_monthly_measurements_by_year(2025)

        self._assert_v28_chart_data_call(mock_get, resolution="month")
        assert isinstance(result, MeasurementsWithSpotPriceResponse)

    def test_get_spot_prices_from_chart_data(self, api_client):
        with patch("requests.get", return_value=self._mock_response(self._load("chart_data_response.json"))) as mock_get:
            result = api_client.get_spot_prices_from_chart_data(date(2025, 10, 6))

        mock_get.assert_called_once()
        params = mock_get.call_args.kwargs["params"]
        assert "start" in params and "stop" in params
        assert isinstance(result, SpotPriceChartResponse)
        assert result.resolution == "quarter"
        assert len(result.series) > 0

    def test_get_contract_data_json(self, api_client):
        with patch("requests.get", return_value=self._mock_response(self._load("contracts_response.json"))) as mock_get:
            result = api_client.get_contract_data_json()

        params = mock_get.call_args.kwargs["params"]
        assert params == {"include_transfer": "true", "update": "true", "include_products": "true"}
        assert isinstance(result, list) and len(result) > 0
        assert "contract_id" in result[0] and "delivery_site" in result[0]

    def test_get_contract_start_date(self, api_client):
        from datetime import date
        from unittest.mock import patch
        api_client._selected_contract = {
            **api_client._selected_contract,
            "start_date": "2020-11-05T00:00:00",
        }
        with patch.object(api_client, "_refresh_api_client_state"):
            result = api_client.get_contract_start_date()
        assert result == date(2020, 11, 5)

    def test_get_contract_start_date_missing_field(self, api_client):
        from unittest.mock import patch
        api_client._selected_contract = {"other_field": "value"}  # Non-empty dict without start_date
        with patch.object(api_client, "_refresh_api_client_state"):
            result = api_client.get_contract_start_date()
        assert result is None

    def test_get_contract_start_date_none_value(self, api_client):
        from unittest.mock import patch
        api_client._selected_contract = {"start_date": None}
        with patch.object(api_client, "_refresh_api_client_state"):
            result = api_client.get_contract_start_date()
        assert result is None

    def test_get_contract_start_date_invalid_format(self, api_client):
        from unittest.mock import patch
        api_client._selected_contract = {"start_date": "invalid-date"}
        with patch.object(api_client, "_refresh_api_client_state"):
            result = api_client.get_contract_start_date()
        assert result is None

    def test_get_contract_start_date_empty_contract(self, api_client):
        from unittest.mock import patch
        api_client._selected_contract = None
        with patch.object(api_client, "_refresh_api_client_state"):
            with pytest.raises(InvalidApiResponseException, match="Contract data is empty or None"):
                api_client.get_contract_start_date()

    @pytest.mark.parametrize(
        "resolution,resource,expect_ambient",
        [
            ("hour", "measurement_spot_hour_response.json", True),
            ("quarter", "measurement_spot_quarter_response.json", False),
        ],
    )
    def test_get_measurements_with_spot_prices(self, api_client, resolution, resource, expect_ambient):
        with patch("requests.get", return_value=self._mock_response(self._load(resource))) as mock_get:
            result = api_client.get_measurements_with_spot_prices(date(2025, 10, 6), date(2025, 10, 7), resolution)

        self._assert_v28_chart_data_call(mock_get, resolution=resolution)
        assert isinstance(result, MeasurementsWithSpotPriceResponse)
        assert result.resolution == resolution
        assert len(result.series) > 0
        first = result.series[0]
        if expect_ambient:
            assert first.ambient_temperature is not None
            assert first.ambient_humidity is not None
        else:
            assert first.ambient_temperature is None
            assert first.ambient_humidity is None

    @pytest.mark.parametrize(
        "status_code,body,expected_substrings",
        [
            (
                403,
                {
                    "type": "/problems/chart-data/no-relevant-contract",
                    "title": "No relevant contracts for delivery site in requested period",
                    "status": 403,
                },
                ["403", "no-relevant-contract"],
            ),
            (500, {}, ["500"]),
        ],
        ids=["403_no_relevant_contract", "500_internal_error"],
    )
    def test_get_measurements_with_spot_prices_raises_on_http_error(
        self, api_client, status_code, body, expected_substrings
    ):
        """Non-2xx responses must raise InvalidApiResponseException instead of producing
        a confusing TypeError when the error body is fed into MeasurementsWithSpotPriceResponse.

        Regression test for v28 chart-data endpoint returning errors such as
        ``no-relevant-contract`` (403) for transfer-only delivery sites.
        """
        response = self._mock_response(json_body=body, ok=False, status_code=status_code)
        with patch("requests.get", return_value=response):
            with pytest.raises(InvalidApiResponseException) as exc_info:
                api_client.get_measurements_with_spot_prices(date(2025, 10, 1), date(2025, 10, 8), "day")

        message = str(exc_info.value)
        for substring in expected_substrings:
            assert substring in message

    def test_get_daily_measurements_between_dates_propagates_http_error(self, api_client):
        """The wrapper must surface the same exception raised by the underlying call,
        not a TypeError from response parsing."""
        response = self._mock_response(json_body={}, ok=False, status_code=500, text="Internal Server Error")
        with patch("requests.get", return_value=response):
            with pytest.raises(InvalidApiResponseException):
                api_client.get_daily_measurements_between_dates(date(2025, 10, 1), date(2025, 10, 8))

    def test_transfer_contract_uses_osv_channel(self, api_client_transfer):
        """A delivery site with an electricity-transfer contract must request
        ``channel=osv`` (the transfer channel) instead of the default ``oh``,
        and the ``electricity_transfer`` field is exposed as the unified
        ``electricity`` value."""
        body = self._load("measurement_transfer_day_response.json")
        with patch("requests.get", return_value=self._mock_response(body)) as mock_get:
            result = api_client_transfer.get_daily_measurements_between_dates(date(2025, 10, 1), date(2025, 10, 4))

        self._assert_v28_chart_data_call(mock_get, resolution="day", channel="osv")
        assert isinstance(result, MeasurementsWithSpotPriceResponse)
        first = result.series[0]
        assert first.electricity == 10.0

    def test_total_consumption_for_transfer_contract(self, api_client_transfer):
        """get_total_consumption_between_dates must sum the transfer kWh,
        ignoring null entries, when only an electricity-transfer contract exists."""
        body = self._load("measurement_transfer_day_response.json")
        with patch("requests.get", return_value=self._mock_response(body)):
            total = api_client_transfer.get_total_consumption_between_dates(date(2025, 10, 1), date(2025, 10, 4))

        # Sum of non-null electricity_transfer values from the fixture (10 + 20 + 30)
        assert total == pytest.approx(60.0)

    def test_get_transfer_fee_sums_non_base_components(self, api_client_transfer):
        """Total per-kWh transfer price = transfer fee + electricity tax,
        excluding the monthly base fee. Works regardless of the inconsistent
        component name casing the API returns ("siirtomaksu" vs "Siirtomaksu")."""
        api_client_transfer._selected_contract["products"] = [
            {
                "product_type": "transfer",
                "components": [
                    {"name": "siirtomaksu", "price": 4.44, "is_base_price": False},
                    {"name": "Sähkövero", "price": 2.91788, "is_base_price": False},
                    {"name": "perusmaksu", "price": 6.01, "is_base_price": True},
                ],
            }
        ]
        with patch.object(api_client_transfer, "_refresh_api_client_state"):
            assert api_client_transfer.get_transfer_fee() == pytest.approx(7.35788)

    def test_get_transfer_fee_without_transfer_product(self, api_client):
        api_client._selected_contract["products"] = [{"product_type": "energy", "components": []}]
        with patch.object(api_client, "_refresh_api_client_state"):
            assert api_client.get_transfer_fee() == 0.0

    def test_close_saves_cookies_and_nulls_session(self, api_client):
        api_client._session.get_all_cookies.return_value = [("access-token", "tok", ".oma.helen.fi", "/")]
        api_client.close()
        assert api_client._saved_cookies == [("access-token", "tok", ".oma.helen.fi", "/")]
        assert api_client._session is None

    def test_double_close_preserves_saved_cookies(self, api_client):
        """Second close() must not overwrite _saved_cookies with None."""
        api_client._session.get_all_cookies.return_value = [("access-token", "tok", ".oma.helen.fi", "/")]
        api_client.close()   # saves cookies, nulls session
        api_client.close()   # session is None — must be a no-op
        assert api_client._saved_cookies == [("access-token", "tok", ".oma.helen.fi", "/")]

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load(name):
        with open(f"tests/resources/{name}") as f:
            return json.load(f)

    @staticmethod
    def _mock_response(json_body=None, ok=True, status_code=200, text=""):
        response = Mock()
        response.ok = ok
        response.status_code = status_code
        response.text = text or (json.dumps(json_body) if json_body is not None else "")
        response.json.return_value = json_body if json_body is not None else {}
        return response

    @staticmethod
    def _assert_v28_chart_data_call(mock_get, *, resolution, channel="oh"):
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        url = args[0]
        params = kwargs["params"]
        assert "v28" in url
        assert "chart-data" in url
        assert params["resolution"] == resolution
        assert params["channel"] == channel
        assert "start" in params and "stop" in params
        assert kwargs["timeout"] == HTTP_READ_TIMEOUT

