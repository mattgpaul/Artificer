from enum import Enum

class Timescale(Enum):
    MINUTE = "1m"
    MINUTE5 = "5m"
    MINUTE15 = "15m"
    MINUTE30 = "30m"
    HOUR = "1h"
    HOUR2 = "2h"
    HOUR4 = "4h"
    HOUR8 = "8h"
    DAY = "1d"
    WEEK = "1w"
    MONTH = "1mo"
    MONTH3 = "3mo"
    MONTH6 = "6mo"
    YEAR = "1y"
    YEAR5 = "5y"
    YEAR10 = "10y"
    YEAR20 = "20y"
    YEAR30 = "30y"

    @property
    def order(self) -> int:
        """Returns the hierarchy order (lower = finer granularity)"""
        hierarchy = [
            "1m", "5m", "15m", "30m",
            "1h", "2h", "4h", "8h", 
            "1d", "1w", "1mo", "3mo", "6mo",
            "1y", "5y", "10y", "20y", "30y"
        ]
        return hierarchy.index(self.value)

    def __lt__(self, other: "Timescale") -> bool:
        return self.order < other.order

    def __gt__(self, other: "Timescale") -> bool:
        return self.order > other.order

    def __eq__(self, other: "Timescale") -> bool:
        return self.order == other.order

    def __ne__(self, other: "Timescale") -> bool:
        return self.order != other.order