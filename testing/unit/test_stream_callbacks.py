import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import dash
import plotly.graph_objects as go
from unittest.mock import patch, MagicMock

from app.healthcare_analytics import app
from app import config as cfg

# ---------------------------------------------------------------------------
# Extract all registered callback functions by name.
# Dash wraps callbacks with add_context; use __wrapped__ to get the original
# inner function which can be called without Dash context kwargs.
# ---------------------------------------------------------------------------
_cb = {
    val["callback"].__name__: getattr(val["callback"], "__wrapped__", val["callback"])
    for val in app.callback_map.values()
    if "callback" in val
}


# ───────────────────────── trigger_stream ──────────────────────────────────

def test_trigger_stream_returns_started():
    with patch("app.callbacks.stream_callbacks.start_threads_once"):
        result = _cb["trigger_stream"](1)
    assert result == {"status": "started"}


# ──────────────────────── update_graph_live ───────────────────────────────

def test_update_graph_live_paused():
    result = _cb["update_graph_live"](1, "full", cfg.DEPARTMENTS, {"paused": True})
    assert result is dash.no_update


def test_update_graph_live_full_mode():
    for dept in cfg.counts_history:
        cfg.counts_history[dept].clear()
    result = _cb["update_graph_live"](1, "full", cfg.DEPARTMENTS, {"paused": False})
    assert isinstance(result, go.Figure)


def test_update_graph_live_latest_mode():
    for dept in cfg.counts_history:
        cfg.counts_history[dept].clear()
    result = _cb["update_graph_live"](1, "latest", cfg.DEPARTMENTS, {"paused": False})
    assert isinstance(result, go.Figure)


def test_update_graph_live_with_existing_data():
    for dept in cfg.counts_history:
        cfg.counts_history[dept].clear()
    with cfg.data_lock:
        cfg.consumed_data.append({
            "patient_id": 1234, "department": "Cardiology",
            "check_in_time": "2025-01-01 00:00:00",
            "complaint": "Chest pain", "sex": "Male", "age": 45,
        })
    result = _cb["update_graph_live"](1, "full", cfg.DEPARTMENTS, {"paused": False})
    assert isinstance(result, go.Figure)
    with cfg.data_lock:
        cfg.consumed_data.clear()


# ─────────────────────── get_live_table_figure ────────────────────────────

def test_get_live_table_figure_paused():
    result = _cb["get_live_table_figure"](1, {}, cfg.DEPARTMENTS, {"paused": True})
    assert result is dash.no_update


def test_get_live_table_figure_empty_data():
    with cfg.data_lock:
        cfg.consumed_data.clear()
    result = _cb["get_live_table_figure"](1, {}, cfg.DEPARTMENTS, {"paused": False})
    assert isinstance(result, go.Figure)


def test_get_live_table_figure_with_data():
    with cfg.data_lock:
        cfg.consumed_data.clear()
        cfg.consumed_data.append({
            "patient_id": 1234, "department": "Cardiology",
            "check_in_time": "2025-01-01 00:00:00",
            "complaint": "Chest pain", "sex": "Male", "age": 45,
        })
    result = _cb["get_live_table_figure"](1, {}, cfg.DEPARTMENTS, {"paused": False})
    assert isinstance(result, go.Figure)
    with cfg.data_lock:
        cfg.consumed_data.clear()


# ────────────────────────── update_summary ────────────────────────────────

def test_update_summary_paused():
    result = _cb["update_summary"](1, {"paused": True})
    assert result is dash.no_update


def test_update_summary_no_data_generates_dummy():
    with cfg.data_lock:
        cfg.consumed_data.clear()
    with patch("app.callbacks.stream_callbacks.summarize_checkins", return_value="dummy summary"):
        result = _cb["update_summary"](1, {"paused": False})
    assert result == "dummy summary"


def test_update_summary_with_data():
    with cfg.data_lock:
        cfg.consumed_data.clear()
        cfg.consumed_data.append({
            "patient_id": 1234, "department": "Cardiology",
            "check_in_time": "2025-01-01 00:00:00",
            "complaint": "Chest pain", "sex": "Male", "age": 45,
        })
    with patch("app.callbacks.stream_callbacks.summarize_checkins", return_value="real summary"):
        result = _cb["update_summary"](1, {"paused": False})
    assert result == "real summary"
    with cfg.data_lock:
        cfg.consumed_data.clear()


# ─────────────────────────── reset_chart ─────────────────────────────────

def test_reset_chart_clears_state_and_resets_intervals():
    with cfg.data_lock:
        cfg.consumed_data.append({"patient_id": 9999})
    cfg.counts_history["Cardiology"].append(10)

    result = _cb["reset_chart"](1)

    assert result == (0, 0, {"status": "reset"})
    assert len(cfg.consumed_data) == 0
    assert cfg.counts_history["Cardiology"] == []


# ────────────────────────── toggle_pause ─────────────────────────────────

def test_toggle_pause_enables_pause():
    result = _cb["toggle_pause"](1, {"paused": False})
    assert result == {"paused": True}
    cfg.paused = False  # restore


def test_toggle_pause_disables_pause():
    result = _cb["toggle_pause"](1, {"paused": True})
    assert result == {"paused": False}


# ──────────────────────── update_stream_status ────────────────────────────

def test_update_stream_status_live():
    text, style = _cb["update_stream_status"]({"paused": False})
    assert text == "Live"
    assert style["background-color"] == "mediumseagreen"


def test_update_stream_status_paused():
    text, style = _cb["update_stream_status"]({"paused": True})
    assert text == "Paused"
    assert style["background-color"] == "red"
