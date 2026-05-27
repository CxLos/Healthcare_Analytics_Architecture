# ============================ DATA GENERATOR =============================== #

import time
import random
import threading

from app import config as cfg


def data_generator():
    while True:
        if cfg.paused:
            time.sleep(0.5)
            continue

        dept = random.choice(cfg.DEPARTMENTS)
        record = {
            "patient_id": random.randint(1000, 9999),
            "check_in_time": time.strftime('%Y-%m-%d %H:%M:%S'),
            "department": dept,
            "complaint": random.choice(cfg.COMPLAINTS[dept]),
            "sex": random.choice(["Male", "Female"]),
            "age": random.randint(1, 99),
        }

        with cfg.data_lock:
            cfg.consumed_data.append(record)
            print(f"Generated: {record}")

        time.sleep(2)


def start_threads_once():
    if not cfg.producer_started:
        threading.Thread(target=data_generator, daemon=True).start()
        cfg.producer_started = True
        print("🟢 Data generator thread launched")
