import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
from app.healthcare_analytics import app
from app.config import consumed_data, data_lock, counts_history, DEPARTMENTS


def test_app_layout_has_live_chart():
    """Dash layout should contain the live line chart component."""
    layout_str = str(app.layout)
    assert "live-line-chart" in layout_str


def test_app_layout_has_check_in_table():
    assert "check-in-table" in str(app.layout)


def test_app_layout_has_pause_button():
    assert "pause-button" in str(app.layout)


def test_app_layout_has_reset_button():
    assert "reset-button" in str(app.layout)


def test_reset_clears_consumed_data():
    """Simulates the reset logic used by the reset_chart callback."""
    with data_lock:
        consumed_data.append({"patient_id": 1111, "department": "Cardiology"})

    # Replicate reset callback logic
    for dept in counts_history:
        counts_history[dept].clear()
    with data_lock:
        consumed_data.clear()

    assert len(consumed_data) == 0
    for dept in DEPARTMENTS:
        assert counts_history[dept] == []
