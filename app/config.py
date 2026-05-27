# =========================== CONFIGURATION ========================== #

import threading

# Departments list
DEPARTMENTS = [
    "Cardiology",
    "Hematology",
    "Pediatrics",
    "Neurology",
    "Endocrinology",
    "Radiology",
    "Nephrology",
    "Oncology",
    "Urology",
]

COMPLAINTS = {
    "Cardiology": [
        "Chest pain",
        "Shortness of breath",
        "Palpitations",
        "High blood pressure follow-up",
        "Heart palpitations"
    ],
    "Hematology": [
        "Easy bruising",
        "Fatigue",
        "Anemia follow-up",
        "Blood clot concern",
        "Bleeding gums"
    ],
    "Pediatrics": [
        "Fever",
        "Cough",
        "Ear pain",
        "Vomiting",
        "Routine check-up"
    ],
    "Neurology": [
        "Headache",
        "Dizziness",
        "Seizure",
        "Numbness or tingling",
        "Memory issues"
    ],
    "Endocrinology": [
        "Diabetes check-up",
        "Thyroid problem",
        "Weight changes",
        "Fatigue",
        "Hormone imbalance"
    ],
    "Radiology": [
        "X-ray request",
        "MRI follow-up",
        "CT scan appointment",
        "Ultrasound request",
        "Screening exam"
    ],
    "Nephrology": [
        "Kidney function check",
        "Swelling/edema",
        "High blood pressure",
        "Urinary issues",
        "Chronic kidney disease follow-up"
    ],
    "Oncology": [
        "Cancer follow-up",
        "Treatment side effects",
        "New symptom check",
        "Pain management",
        "Screening exam"
    ],
    "Urology": [
        "Urinary tract infection",
        "Kidney stones",
        "Prostate check-up",
        "Blood in urine",
        "Frequent urination"
    ]
}

# ============================ Globals =============================== #

data_lock = threading.Lock()
consumed_data = []
producer_started = False
paused = False
last_pause_state = None
counts_history = {dept: [] for dept in DEPARTMENTS}
last_index = 0

# Clear local data when the app starts / reloads
with data_lock:
    consumed_data.clear()
for dept in counts_history:
    counts_history[dept].clear()
