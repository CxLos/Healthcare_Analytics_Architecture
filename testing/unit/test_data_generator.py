import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.config import DEPARTMENTS, COMPLAINTS
from app.data.generator import data_generator
from app import config as cfg
import threading
import time


def test_departments_not_empty():
    assert len(DEPARTMENTS) > 0


def test_all_departments_have_complaints():
    for dept in DEPARTMENTS:
        assert dept in COMPLAINTS
        assert len(COMPLAINTS[dept]) > 0


def test_data_generator_appends_record():
    """Run generator thread briefly and confirm a record is appended."""
    with cfg.data_lock:
        cfg.consumed_data.clear()

    t = threading.Thread(target=data_generator, daemon=True)
    t.start()
    time.sleep(3)  # allow at least one 2-second cycle

    with cfg.data_lock:
        count = len(cfg.consumed_data)

    assert count >= 1


def test_generated_record_has_required_fields():
    """Each generated record must contain all expected keys."""
    with cfg.data_lock:
        cfg.consumed_data.clear()

    t = threading.Thread(target=data_generator, daemon=True)
    t.start()
    time.sleep(3)

    with cfg.data_lock:
        record = cfg.consumed_data[0] if cfg.consumed_data else {}

    required_keys = {"patient_id", "check_in_time", "department", "complaint", "sex", "age"}
    assert required_keys.issubset(record.keys())


def test_generated_record_department_is_valid():
    with cfg.data_lock:
        cfg.consumed_data.clear()

    t = threading.Thread(target=data_generator, daemon=True)
    t.start()
    time.sleep(3)

    with cfg.data_lock:
        record = cfg.consumed_data[0] if cfg.consumed_data else {}

    assert record.get("department") in DEPARTMENTS


def test_data_generator_pauses_when_flagged():
    """While paused, generator should not append records."""
    with cfg.data_lock:
        cfg.consumed_data.clear()
    cfg.paused = True

    t = threading.Thread(target=data_generator, daemon=True)
    t.start()
    time.sleep(0.7)  # enough for at least one 0.5s sleep cycle

    with cfg.data_lock:
        count = len(cfg.consumed_data)

    cfg.paused = False  # restore
    assert count == 0


def test_start_threads_once_launches_thread():
    """start_threads_once should spawn a thread when producer_started is False."""
    from app.data.generator import start_threads_once
    from unittest.mock import patch, MagicMock

    cfg.producer_started = False
    mock_thread = MagicMock()
    with patch("app.data.generator.threading.Thread", return_value=mock_thread) as mock_cls:
        start_threads_once()

    assert cfg.producer_started is True
    mock_thread.start.assert_called_once()
    cfg.producer_started = False  # restore


def test_start_threads_once_idempotent():
    """start_threads_once should not start a second thread when already started."""
    from app.data.generator import start_threads_once
    from unittest.mock import patch

    cfg.producer_started = True
    with patch("app.data.generator.threading.Thread") as mock_cls:
        start_threads_once()
        mock_cls.assert_not_called()
    cfg.producer_started = False  # restore
