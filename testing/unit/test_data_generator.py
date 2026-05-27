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
