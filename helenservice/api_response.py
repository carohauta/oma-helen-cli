from typing import List


class Measurement(object):
    def __init__(self, value: float, status: str, **_):
        self.value = value
        self.status = status


class MeasurementData(object):
    def __init__(self, start: str, stop: str, resolution_s: str, resolution: str, unit: str, measurements: List, **_):
        self.start = start
        self.stop = stop
        self.resolution_s = resolution_s
        self.resolution = resolution
        self.unit = unit
        self.measurements = list(map(lambda m: Measurement(**m), measurements))


class MeasurementIntervals(object):
    def __init__(self, electricity: List = None, electricity_transfer: List = None, **_):
        if electricity is not None:
            self.electricity = list(map(lambda e: MeasurementData(**e), electricity))
        elif electricity_transfer is not None:
            self.electricity = list(map(lambda e: MeasurementData(**e), electricity_transfer))


class MeasurementResponse(object):
    def __init__(self, intervals: dict, **_):
        self.intervals = MeasurementIntervals(**intervals) if intervals is not None else None


class SpotPriceChartSeries(object):
    def __init__(self, start: str, stop: str, electricity_spot_prices_vat: float = None, electricity_spot_prices: float = None,
                 electricity_spot_prices_hour_average_vat: float = None, electricity_spot_prices_hour_average: float = None, **_):
        self.start = start
        self.stop = stop
        self.electricity_spot_prices_vat = electricity_spot_prices_vat
        self.electricity_spot_prices = electricity_spot_prices
        self.electricity_spot_prices_hour_average_vat = electricity_spot_prices_hour_average_vat
        self.electricity_spot_prices_hour_average = electricity_spot_prices_hour_average


class SpotPriceChartResponse(object):
    def __init__(self, start: str, stop: str, resolution: str, units: dict, ids: dict,
                 data_start_times: dict, data_stop_times: dict, series: List, missing_series: List = None, **_):
        self.start = start
        self.stop = stop
        self.resolution = resolution
        self.units = units
        self.ids = ids
        self.data_start_times = data_start_times
        self.data_stop_times = data_stop_times
        self.series = list(map(lambda s: SpotPriceChartSeries(**s), series))
        self.missing_series = missing_series if missing_series is not None else []


class SpotPricesResponse(object):
    def __init__(self, interval: dict, **_):
        self.interval = MeasurementData(**interval) if interval is not None else None