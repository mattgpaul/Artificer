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
