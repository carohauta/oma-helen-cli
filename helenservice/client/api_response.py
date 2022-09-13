from typing import List


class MonthlyMeasurement(object):
    def __init__(self, value: int, status: str):
        self.value = value
        self.status = status


class MonthlyMeasurementElectricity(object):
    def __init__(self, start: str, stop: str, resolution_s: str, resolution: str, unit: str, measurements: List):
        self.start = start
        self.stop = stop
        self.resolution_s = resolution_s
        self.resolution = resolution
        self.unit = unit
        self.measurements = list(map(lambda m: MonthlyMeasurement(**m), measurements))


class MonthlyMeasurementIntervals(object):
    def __init__(self, electricity: List):
        self.electricity = list(map(lambda e: MonthlyMeasurementElectricity(**e), electricity))


class MonthlyMeasurementResponse(object):
    def __init__(self, intervals: dict):
        self.intervals = MonthlyMeasurementIntervals(**intervals)
