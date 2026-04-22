"""Unit tests for timestamp helper utilities."""

from datetime import datetime, timedelta
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from textgraphx.time_utils import utc_iso_now, utc_timestamp_now


@pytest.mark.unit
class TestTimeUtils:
    def test_utc_iso_now_is_timezone_aware_utc(self):
        value = utc_iso_now()
        dt = datetime.fromisoformat(value)

        assert dt.tzinfo is not None
        assert dt.utcoffset() == timedelta(0)

    def test_utc_timestamp_now_returns_float(self):
        ts = utc_timestamp_now()
        assert isinstance(ts, float)
