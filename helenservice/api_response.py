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


class SpotPricesResponse(object):
    def __init__(self, interval: dict, **_):
        self.interval = MeasurementData(**interval) if interval is not None else None