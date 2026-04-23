class SpotPriceChartSeries:
    def __init__(
        self,
        start: str,
        stop: str,
        electricity: float = None,
        electricity_spot_prices_vat: float = None,
        electricity_spot_prices: float = None,
        electricity_spot_prices_hour_average_vat: float = None,
        electricity_spot_prices_hour_average: float = None,
        **_,
    ):
        self.start = start
        self.stop = stop
        self.electricity = electricity
        self.electricity_spot_prices_vat = electricity_spot_prices_vat
        self.electricity_spot_prices = electricity_spot_prices
        self.electricity_spot_prices_hour_average_vat = electricity_spot_prices_hour_average_vat
        self.electricity_spot_prices_hour_average = electricity_spot_prices_hour_average


class SpotPriceChartResponse:
    def __init__(
        self,
        start: str,
        stop: str,
        resolution: str,
        units: dict,
        ids: dict,
        data_start_times: dict,
        data_stop_times: dict,
        series: list,
        missing_series: list = None,
        **_,
    ):
        self.start = start
        self.stop = stop
        self.resolution = resolution
        self.units = units
        self.ids = ids
        self.data_start_times = data_start_times
        self.data_stop_times = data_stop_times
        self.series = list(map(lambda s: SpotPriceChartSeries(**s), series))
        self.missing_series = missing_series if missing_series is not None else []


class MeasurementsWithSpotPriceSeries:
    def __init__(
        self,
        start: str,
        stop: str,
        electricity: float = None,
        electricity_spot_prices_vat: float = None,
        electricity_spot_prices: float = None,
        ambient_temperature: float = None,
        ambient_humidity: float = None,
        **_,
    ):
        self.start = start
        self.stop = stop
        self.electricity = electricity
        self.electricity_spot_prices_vat = electricity_spot_prices_vat
        self.electricity_spot_prices = electricity_spot_prices
        self.ambient_temperature = ambient_temperature
        self.ambient_humidity = ambient_humidity


class MeasurementsWithSpotPriceResponse:
    def __init__(
        self,
        start: str,
        stop: str,
        resolution: str,
        units: dict,
        ids: dict,
        data_start_times: dict,
        data_stop_times: dict,
        series: list,
        missing_series: list = None,
        **_,
    ):
        self.start = start
        self.stop = stop
        self.resolution = resolution
        self.units = units
        self.ids = ids
        self.data_start_times = data_start_times
        self.data_stop_times = data_stop_times
        self.series = list(map(lambda s: MeasurementsWithSpotPriceSeries(**s), series))
        self.missing_series = missing_series if missing_series is not None else []
