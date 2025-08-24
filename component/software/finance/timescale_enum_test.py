from component.software.finance.timescale_enum import Timescale
import pytest

class TestTimescaleEnum:
    def test_timescale_enum(self):
        assert Timescale.MINUTE.value == "1m"
        assert Timescale.MINUTE5.value == "5m"
        assert Timescale.MINUTE15.value == "15m"
        assert Timescale.MINUTE30.value == "30m"
        assert Timescale.HOUR.value == "1h"
        assert Timescale.HOUR2.value == "2h"
        assert Timescale.HOUR4.value == "4h"
        assert Timescale.HOUR8.value == "8h"
        assert Timescale.DAY.value == "1d"

    def test_timescale_enum_invalid_timescale(self):
        with pytest.raises(ValueError):
            Timescale("100y")

    def test_timescale_enum_order(self):
        assert Timescale.MINUTE < Timescale.MINUTE5
        assert Timescale.MINUTE5 < Timescale.MINUTE15
        assert Timescale.MINUTE15 < Timescale.MINUTE30
        assert Timescale.MINUTE30 < Timescale.HOUR
        assert Timescale.HOUR < Timescale.HOUR2
        assert Timescale.HOUR2 < Timescale.HOUR4
        assert Timescale.HOUR4 < Timescale.HOUR8
        assert Timescale.HOUR8 < Timescale.DAY
        assert Timescale.DAY < Timescale.WEEK
        assert Timescale.WEEK < Timescale.MONTH
        assert Timescale.MONTH < Timescale.MONTH3
        assert Timescale.MONTH3 < Timescale.MONTH6
        assert Timescale.MONTH6 < Timescale.YEAR
        assert Timescale.YEAR < Timescale.YEAR5
        assert Timescale.YEAR5 < Timescale.YEAR10
        assert Timescale.YEAR10 < Timescale.YEAR20
        assert Timescale.YEAR20 < Timescale.YEAR30

