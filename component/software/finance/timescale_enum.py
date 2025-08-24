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
    MAX = "max"