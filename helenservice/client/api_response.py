from typing import List


class MonthlyMeasurement(object):
    def __init__(self, value: int, status: str):
        self.value = value
        self.status = status


class MonthlyMeasurementElectricity(object):
    def __init__(self, start: str, stop: str, resolution_s: str, resolution: str, unit: str, measurements: List[MonthlyMeasurement]):
        self.start = start
        self.stop = stop
        self.resolution_s = resolution_s
        self.resolution = resolution
        self.unit = unit
        self.measurements = measurements


class MonthlyMeasurementIntervals(object):
    def __init__(self, electricity: List[MonthlyMeasurementElectricity]):
        self.electricity = electricity


class MonthlyMeasurementResponse(object):
    def __init__(self, intervals: MonthlyMeasurementIntervals):
        self.intervals = intervals
