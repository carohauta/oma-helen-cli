import json
from datetime import date
from unittest.mock import Mock, patch

import pytest

from helenservice.api_client import HelenApiClient
from helenservice.api_response import MeasurementResponse, SpotPriceChartResponse
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
        client._selected_contract = {"delivery_site": {"id": "123456789"}, "domain": None}
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

    def test_get_spot_prices_between_dates_hourly(self, api_client, mock_measurements_response):
        """Test get_spot_prices_between_dates method with hourly resolution."""
        start_date = date(2025, 9, 7)
        end_date = date(2025, 9, 8)

        # Mock the HTTP request with spot prices response structure
        mock_spot_prices_response = {"interval": mock_measurements_response["intervals"]["electricity"][0]}
        mock_response = Mock()
        mock_response.text = json.dumps(mock_spot_prices_response)

        with patch("requests.get", return_value=mock_response) as mock_get:
            result = api_client.get_spot_prices_between_dates(start_date, end_date, RESOLUTION_HOUR)

            # Verify the request was made correctly
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[1]["params"]["resolution"] == "hour"
            assert call_args[1]["params"]["delivery_site_id"] == "123456789"

            # Verify the response parsing
            assert result.interval is not None
            assert result.interval.measurements is not None
            assert len(result.interval.measurements) > 0

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

            # Verify default resolution is used
            call_args = mock_get.call_args
            assert call_args[1]["params"]["resolution"] == "hour"

            # Verify response
            assert result.interval is not None
