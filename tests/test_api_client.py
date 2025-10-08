import json
from datetime import date
from unittest.mock import Mock, patch

import pytest

from helenservice.api_client import HelenApiClient
from helenservice.api_response import MeasurementResponse, MeasurementsWithSpotPriceResponse, SpotPriceChartResponse
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
    def mock_measurements_response(self):
        """Load the test measurements response data."""
        with open("tests/resources/measurements_response.json") as f:
            return json.load(f)

    @pytest.fixture
    def mock_chart_data_response(self):
        """Load the test chart data response."""
        with open("tests/resources/chart_data_response.json") as f:
            return json.load(f)

    @pytest.fixture
    def mock_contracts_response(self):
        """Load the test contracts response."""
        with open("tests/resources/contracts_response.json") as f:
            return json.load(f)

    @pytest.fixture
    def mock_measurement_spot_hour_response(self):
        """Load the test measurement with spot prices response (hourly)."""
        with open("tests/resources/measurement_spot_hour_response.json") as f:
            return json.load(f)

    @pytest.fixture
    def mock_measurement_spot_quarter_response(self):
        """Load the test measurement with spot prices response (quarterly)."""
        with open("tests/resources/measurement_spot_quarter_response.json") as f:
            return json.load(f)

    def test_get_daily_measurements_between_dates(self, api_client, mock_measurements_response):
        """Test get_daily_measurements_between_dates method."""
        start_date = date(2025, 9, 7)
        end_date = date(2025, 10, 8)

        # Mock the HTTP request
        mock_response = Mock()
        mock_response.text = json.dumps(mock_measurements_response)

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = api_client.get_daily_measurements_between_dates(start_date, end_date)

            # Verify the request was made correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["params"]["resolution"] == "day"
            assert call_args[1]["params"]["delivery_site_id"] == "123456789"
            assert call_args[1]["timeout"] == HTTP_READ_TIMEOUT

            # Verify the response parsing
            assert isinstance(result, MeasurementResponse)
            assert result.intervals is not None
            assert result.intervals.electricity is not None
            assert len(result.intervals.electricity[0].measurements) > 0

    def test_get_measurements_between_dates_hourly(self, api_client, mock_measurements_response):
        """Test get_measurements_between_dates method with hourly resolution."""
        start_date = date(2025, 9, 7)
        end_date = date(2025, 9, 8)

        # Mock the HTTP request
        mock_response = Mock()
        mock_response.text = json.dumps(mock_measurements_response)

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = api_client.get_measurements_between_dates(start_date, end_date, RESOLUTION_HOUR)

            # Verify the request was made correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["params"]["resolution"] == "hour"
            assert call_args[1]["params"]["delivery_site_id"] == "123456789"

            # Verify the response parsing
            assert isinstance(result, MeasurementResponse)
            assert result.intervals is not None
            assert result.intervals.electricity is not None

    def test_get_monthly_measurements_by_year(self, api_client, mock_measurements_response):
        """Test get_monthly_measurements_by_year method."""
        year = 2025

        # Mock the HTTP request
        mock_response = Mock()
        mock_response.text = json.dumps(mock_measurements_response)

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = api_client.get_monthly_measurements_by_year(year)

            # Verify the request was made correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["params"]["resolution"] == "month"
            assert "begin" in call_args[1]["params"]
            assert "end" in call_args[1]["params"]

            # Verify the response parsing
            assert isinstance(result, MeasurementResponse)
            assert result.intervals is not None
            assert result.intervals.electricity is not None

    def test_get_spot_prices_from_chart_data(self, api_client, mock_chart_data_response):
        """Test get_spot_prices_from_chart_data method."""
        target_date = date(2025, 10, 6)

        # Mock the HTTP request
        mock_response = Mock()
        mock_response.json.return_value = mock_chart_data_response

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = api_client.get_spot_prices_from_chart_data(target_date)

            # Verify the request was made correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "start" in call_args[1]["params"]
            assert "stop" in call_args[1]["params"]

            # Verify the response parsing
            assert isinstance(result, SpotPriceChartResponse)
            assert result.resolution == "quarter"
            assert result.series is not None
            assert len(result.series) > 0

    def test_get_contract_data_json(self, api_client, mock_contracts_response):
        """Test get_contract_data_json method."""
        # Mock the HTTP request
        mock_response = Mock()
        mock_response.json.return_value = mock_contracts_response

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = api_client.get_contract_data_json()

            # Verify the request was made correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["params"]["include_transfer"] == "true"
            assert call_args[1]["params"]["update"] == "true"
            assert call_args[1]["params"]["include_products"] == "true"

            # Verify the response
            assert isinstance(result, list)
            assert len(result) > 0
            assert "contract_id" in result[0]
            assert "delivery_site" in result[0]

    def test_get_spot_prices_between_dates_default_resolution(self, api_client, mock_measurements_response):
        """Test get_spot_prices_between_dates method with default resolution."""
        start_date = date(2025, 9, 7)
        end_date = date(2025, 9, 8)

        # Mock the HTTP request
        mock_spot_prices_response = {"interval": mock_measurements_response["intervals"]["electricity"][0]}
        mock_response = Mock()
        mock_response.text = json.dumps(mock_spot_prices_response)

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = api_client.get_spot_prices_between_dates(start_date, end_date)

            # Verify the request was made correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["params"]["resolution"] == "hour"
            assert call_args[1]["params"]["delivery_site_id"] == "123456789"

            # Verify the response parsing
            assert result.interval is not None
            assert result.interval.measurements is not None
            assert len(result.interval.measurements) > 0

    def test_get_measurements_with_spot_prices_hourly(
        self, api_client, mock_measurement_spot_hour_response, mock_contracts_response
    ):
        """Test get_measurements_with_spot_prices method with hourly resolution."""
        start_date = date(2025, 10, 6)
        end_date = date(2025, 10, 7)

        # Mock the HTTP requests
        mock_chart_response = Mock()
        mock_chart_response.json.return_value = mock_measurement_spot_hour_response

        mock_contracts_response_mock = Mock()
        mock_contracts_response_mock.json.return_value = mock_contracts_response

        # Mock the _refresh_api_client_state method to avoid contract lookup
        with patch.object(api_client, '_refresh_api_client_state'):
            with patch("requests.get", return_value=mock_chart_response) as mock_get:
                result = api_client.get_measurements_with_spot_prices(start_date, end_date, "hour")

            # Verify the request was made correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "start" in call_args[1]["params"]
            assert "stop" in call_args[1]["params"]
            assert call_args[1]["params"]["resolution"] == "hour"
            assert call_args[1]["params"]["channel"] == "oh"
            assert "chart-data" in call_args[0][0]  # URL contains chart-data

            # Verify the response parsing
            assert isinstance(result, MeasurementsWithSpotPriceResponse)
            assert result.resolution == "hour"
            assert result.series is not None
            assert len(result.series) > 0
            # Check that series contains electricity, spot price, and ambient data
            first_series = result.series[0]
            assert hasattr(first_series, 'electricity')
            assert hasattr(first_series, 'electricity_spot_prices_vat')
            assert hasattr(first_series, 'electricity_spot_prices')
            assert hasattr(first_series, 'ambient_temperature')
            assert hasattr(first_series, 'ambient_humidity')
            # Verify ambient data is present in hourly response
            assert first_series.ambient_temperature is not None
            assert first_series.ambient_humidity is not None

    def test_get_measurements_with_spot_prices_quarterly(
        self, api_client, mock_measurement_spot_quarter_response, mock_contracts_response
    ):
        """Test get_measurements_with_spot_prices method with quarterly resolution."""
        start_date = date(2025, 10, 6)
        end_date = date(2025, 10, 7)

        # Mock the HTTP requests
        mock_chart_response = Mock()
        mock_chart_response.json.return_value = mock_measurement_spot_quarter_response

        mock_contracts_response_mock = Mock()
        mock_contracts_response_mock.json.return_value = mock_contracts_response

        # Mock the _refresh_api_client_state method to avoid contract lookup
        with patch.object(api_client, '_refresh_api_client_state'):
            with patch("requests.get", return_value=mock_chart_response) as mock_get:
                result = api_client.get_measurements_with_spot_prices(start_date, end_date, "quarter")

            # Verify the request was made correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "start" in call_args[1]["params"]
            assert "stop" in call_args[1]["params"]
            assert call_args[1]["params"]["resolution"] == "quarter"
            assert call_args[1]["params"]["channel"] == "oh"
            assert "chart-data" in call_args[0][0]  # URL contains chart-data

            # Verify the response parsing
            assert isinstance(result, MeasurementsWithSpotPriceResponse)
            assert result.resolution == "quarter"
            assert result.series is not None
            assert len(result.series) > 0
            # Check that series contains electricity and spot price data
            first_series = result.series[0]
            assert hasattr(first_series, 'electricity')
            assert hasattr(first_series, 'electricity_spot_prices_vat')
            assert hasattr(first_series, 'electricity_spot_prices')
            # Verify ambient data is not present in quarterly response (should be None)
            assert hasattr(first_series, 'ambient_temperature')
            assert hasattr(first_series, 'ambient_humidity')
            assert first_series.ambient_temperature is None
            assert first_series.ambient_humidity is None
