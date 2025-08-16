# Function to auto-populate the data table with live data

# ============================= IMPORTS ============================= #

# ------ System Imports ------ #
import os
import sys
from dotenv import load_dotenv
load_dotenv()

# #
import json
import time
import random
import pandas as pd
from datetime import datetime

# ------ OpenAI ------ #
from openai import OpenAI

# ------ Dash Imports ------ #
import dash
from dash import dcc, html, Output, Input, State
import plotly.graph_objects as go

# --- Confluent Kafka --- #
from confluent_kafka import Producer, Consumer, KafkaError
import threading
from collections import deque

# =========================== FILE ========================== #

current_dir = os.getcwd()
current_file = os.path.basename(__file__)
script_dir = os.path.dirname(os.path.abspath(__file__))
# file = os.path.join(script_dir, 'data', 'patient_checkin_dataset.xlsx')
# df = pd.read_excel(file)

# print(response.choices[0].message.content)

# =========================== CONFIGURATION ========================== #

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_API_KEY = os.getenv("KAFKA_API_KEY", "")
KAFKA_API_SECRET = os.getenv("KAFKA_API_SECRET", "")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "patient_checkins")

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

# Thread-safe queue for consumed messages
consumed_data = deque(maxlen=100)
data_lock = threading.Lock() 

# ============================ Globals =============================== #

# Thread-safe data store
consumed_data = []
consumer_started = False
consumer_running = False 
producer_started = False
paused = False 
last_pause_state = None 
# Keep track of historical counts per department
counts_history = {dept: [] for dept in DEPARTMENTS}
# Keep track of how many messages we’ve already processed
last_index = 0  

# Clear local data when the app starts / reloads
with data_lock:
    consumed_data.clear()
for dept in counts_history:
    counts_history[dept].clear()

# ============================ PRODUCER =============================== #

# Kafka producer configuration dictionary with connection and authentication details
producer_conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,  # Kafka cluster address
    'security.protocol': 'SASL_SSL',                # Use SASL over SSL for security
    'sasl.mechanisms': 'PLAIN',                      # SASL mechanism is PLAIN (username/password)
    'sasl.username': KAFKA_API_KEY,                  # Your Kafka API key
    'sasl.password': KAFKA_API_SECRET,               # Your Kafka API secret
}

# Kafka Producer instance with the above configuration
producer = Producer(producer_conf)

# callback function to be called after message delivery attempt
# def delivery_report(err, msg):
#     if err is not None:
#         # If there's an error delivering the message, print an error message
#         print(f"❌ Delivery failed: {err}")
#     else:
#         # Otherwise, print success with topic, partition, and offset info
#         print(f"✅ Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

# # single test message to verify connection
# try:
#     test_message = '{"test": "connectivity"}'                  # JSON string to test connectivity
#     producer.produce(KAFKA_TOPIC, value=test_message, callback=delivery_report)  # Send test message
#     producer.flush()                                           # Wait for all messages to be delivered
# except Exception as e:
#     print(f"🔥 Connection error: {e}")                         # Print connection error if it fails

# function to produce random patient check-in messages continuously
def kafka_producer():
    global paused, last_pause_state

    try:
        while True:  # Infinite loop
            if paused:
                if last_pause_state != paused:
                    last_pause_state = paused
                time.sleep(0.5)
                continue
            else:
                if last_pause_state != paused:
                    last_pause_state = paused

            dept = random.choice(DEPARTMENTS)
            message = {
                "patient_id": random.randint(1000, 9999),
                "check_in_time": time.strftime('%Y-%m-%d %H:%M:%S'),
                "department": dept,
                "complaint": random.choice(COMPLAINTS[dept]),
                "sex": random.choice(["Male", "Female"]),
                "age": random.randint(1, 99),  
            }

            try:
                producer.produce(topic=KAFKA_TOPIC, value=json.dumps(message))
                producer.poll(0)
                producer.flush()
                print(f"Produced: {message}")
            except Exception as e:
                print(f"[Producer Error] {e}")

            time.sleep(2)

    finally:
        producer.flush()
        print("Producer finished, all messages delivered.")

# ============================ CONSUMER =============================== #

# Kafka consumer configuration dictionary with connection, authentication, and consumer-specific settings
consumer_conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'security.protocol': 'SASL_SSL',
    'sasl.mechanisms': 'PLAIN',
    'sasl.username': KAFKA_API_KEY,
    'sasl.password': KAFKA_API_SECRET,
    'group.id': 'dashboard-consumer',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': True
}

# Seed initial data
# with data_lock:
#     for _ in range(30):  # add 5 dummy check-ins
#         consumed_data.append({
#             "patient_id": random.randint(1000, 9999),
#             "check_in_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
#             "department": dept,
#             "complaint": random.choice(COMPLAINTS[dept]),
#             "sex": random.choice(["Male", "Female"]),     
#             "age": random.randint(1, 99), 
#         })

# Consumer Function
def kafka_consumer():
    global consumer_running, paused, last_pause_state, consumed_data

    print(f"🟢 Kafka consumer started at {datetime.now()}")
    consumer = Consumer(consumer_conf)
    consumer.subscribe([KAFKA_TOPIC])
    time.sleep(2)  # allow partition assignment

    consumer_running = True
    try:
        while consumer_running:  # main loop controlled by flag
            
            # 1. Print state if it changed
            # if paused != last_pause_state:
            #     if paused:
            #         print("⏸️ Consumer paused")
            #     else:
            #         print("▶️ Consumer playing")
            #     last_pause_state = paused
            
            if paused:
                # If paused, skip polling, just wait
                time.sleep(0.5)
                continue

            # Poll Kafka for new messages
            print("Polling Kafka for messages...")
            msg = consumer.poll(2)
            if msg is None:
                time.sleep(0.5)
                continue

            if msg.error():
                continue

            try:
                parsed = json.loads(msg.value().decode('utf-8'))
                with data_lock:
                    consumed_data.append(parsed)
                    print("✅ Recieved: ", parsed)
            except Exception as e:
                print(f"⚠️ Error parsing message: {e}")

    except Exception as e:
        print(f"🔥 Consumer connection error: {e}")
    finally:
        consumer.close()
        # print("🛑 Kafka consumer stopped")

# Thread starter for consumer
def start_consumer():
    global consumer_started
    if not consumer_started:
        consumer_thread = threading.Thread(target=kafka_consumer)
        consumer_thread.daemon = True
        consumer_thread.start()
        consumer_started = True
        # print("🟢 Kafka consumer thread launched")

# ============================= OpenAI ============================== #

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def summarize_checkins(df_live):
    # Convert recent rows into a simple string
    recent_data = df_live.head(100).to_dict(orient='records')
    recent_data_str = "\n".join([str(record) for record in recent_data])
    prompt = (
        "You are a healthcare analytics assistant. "
        "Provide a descriptive summary in about 2 paragraphs explaining commonly reported symptoms, any possible trends, and just any other general information you think might be useful in human-readable text:\n\n"
        f"{recent_data_str}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You provide a detailed summary of healtcare data."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error summarizing data: {e}"

# ============================= DASH APP ============================== #

app = dash.Dash(__name__)
server = app.server

app.layout = html.Div(
    
    className='',
    children=[
    
    #------------- Header ----------- # 
    
    html.Div(
        className='div',
        children=[
            html.Div(
                className='divv',
                children=[
                    html.H1(
                        'Real-Time Healthcare Data Pipeline', 
                        className='title'),
                    html.H1(
                        'With Apache Kafka',
                        className='title2'),
                    html.Div(
                        className='btn-box', 
                        children=[
                        html.A(
                            'Repo', 
                            href='https://github.com/CxLos/Healthcare_Analytics_Architecture', 
                            className='repo-btn')
                        ]
                    )
                ]
            ),

    #------------- Kafka ----------- # 
    
    html.Div(
        className="kafka-row",
        children=[
            html.H1(
                "Dashboard Live-Stream",
                className="kafka-title"
            ),
            html.Div(
                className='stream-buttons',
                children=[
                    html.Button("⏯️", id="pause-button", n_clicks=0, title="Resume / Pause Stream"),
                    html.Button("🔄", id="reset-button", n_clicks=0, title="Reset Stream"),
                    dcc.Store(id="pause-store", data={"paused": False}),
                    dcc.Store(id="page-load-reset", data={"reset": True}),  
                    dcc.Store(id="tab-closed-trigger", data=False, storage_type="session")
                ]
            ),
        ]
    ),
    
    # ----------- Live Stream Graph ------------- #
    
    html.Div(
        className="stream-row",
        children=[
            html.Div(
                className='',
                children=[
                    html.Div(
                        id="stream-status", 
                        className="stream-status-text"
                    ), 
                ]
            ),

            html.Div(
                className="interval",
                children=[
                    dcc.RadioItems(
                        id='view-mode-toggle',
                        options=[
                            {'label': 'Full History', 'value': 'full'},
                            {'label': 'Latest 30', 'value': 'latest'},
                        ],
                        value='full',
                        labelStyle={
                            'display': 'inline-block',
                            'margin-right': '10px',
                            }
                    ),
                    dcc.Store(id="department-store", data=DEPARTMENTS),
                    dcc.Store(id="consumer-trigger"),  
                    dcc.Graph(
                        className="line-graph",
                        id='live-line-chart',
                        style={"marginTop": "0px"}
                    ),
                    html.Div(
                        className="interval",
                        children=[
                            dcc.Interval(
                                id='interval-component',
                                interval=2 * 1000,  # every 3 seconds
                                n_intervals=0
                            )
                        ]
                    )
                ]
            )
        ]
    ),
    
    # ----------- Bottom Row ------------- #
    
    html.Div(
        className="data-row",
        children=[
            
            # ---- AI Section ---- #
            
            html.Div(
                className="ai-box",
                children=[
                    html.H1(
                        "Quick Synopsis:",
                        className="ai-title"
                    ),
                    html.Div(
                        className='gpt-response', 
                        id='checkin-summary', 
                        # style={'whiteSpace': 'pre-line', 'marginTop': '20px'}
                    ),
                    dcc.Interval(
                        id='chatgpt-interval',
                        interval=20 * 1000,  # every 30 seconds
                        n_intervals=0
                    )
                ]
            ),
            
            # ---- Data Section ---- #
            html.Div(
                className="data-box",
                children=[
                    html.H1(
                        "Patient Check-in Table",
                        className="data-title"
                    ),
                    dcc.Store(id="department-store", data=DEPARTMENTS),
                    dcc.Store(id="consumer-trigger"), 
                    dcc.Graph(
                        className="check-in-table",
                        id='check-in-table',
                    ),
                    
                    html.Div(
                        className="interval",
                        children=[
                            dcc.Interval(
                                id='table-interval-component',
                                interval=2 * 1000, 
                                n_intervals=0
                            )
                        ]
                    )
                ]
            ),
        ]
    ),
]),

#------------- README ----------- # 

    html.Div(
        className='bottom-page',
        children=[
                 
        ]
    ),

    html.Div(
        className='readme-section', 
        children=[
            html.H2("📘 README"),
            html.H4("📝 Description"),
            html.P(
                "This project demonstrates a real-time healthcare data pipeline using "
                "Apache Kafka for event streaming, Python for data generation & consumption, "
                "and Plotly Dash for interactive visualization. Synthetic patient check-in "
                "events are generated with fields like 'patient_id', 'check_in_time', & "
                "'department', streamed into Kafka, and visualized live."
            ),

            html.H4("📦 Installation"),
            html.P("To run this project locally, follow these steps:"),
            html.Pre(html.Code(
                "git clone https://github.com/CxLos/Healthcare_Analytics_Architecture\n"
                "cd Healthcare_Analytics_Architecture\n"
                "pip install -r requirements.txt"
            )),

            html.H4("▶️ Usage"),
            html.P("Run this dashboard with:"),
            html.Pre(html.Code("python healthcare_analytics.py")),

            html.H4("🧪 Methodology"),
            html.P("Synthetic patient check-ins are created with:"),
            html.Ul([
                html.Li("patient_id: (random 4-digit number)"),
                html.Li("check_in_time: (current timestamp)"),
                html.Li("department: (randomly selected from Cardiology, Oncology, Pediatrics etc...)"),
            ]),
            html.P(
                "The producer sends JSON-encoded events to the Kafka topic patient_checkins, "
                "the consumer reads these events in real time, and the data is displayed "
                "on a Plotly Dash dashboard."
            ),

            html.H4("🔍 Insights"),
            html.Ul([
                html.Li("Demonstrates real-time streaming capabilities with Apache Kafka."),
                html.Li("Simulates department-level patient flow monitoring."),
                html.Li("Provides a framework for scaling to predictive healthcare analytics.")
            ]),

            html.H4("✅ Conclusion"),
            html.P(
                "This pipeline shows how real-time event streaming can be applied in healthcare "
                "to monitor patient flow instantly. The same architecture can be extended to "
                "include machine learning for anomaly detection, predictive analytics, and automated alerts."
            ),

            html.H4("📄 License"),
            html.P("MIT License © 2025 CxLos"),
            html.Code(
                "Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the \"Software\"), "
                "to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, "
                "and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: \n\n"
                "The above copyright notice and this permission notice shall be included in "
                "all copies or substantial portions of the Software.\n\n"
                "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR "
                "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS "
                "FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR "
                "COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN "
                "AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH "
                "THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."
            )
        ]
    ),
])

# ------------------- DASH CALLBACK: Trigger Consumer ------------------- #

@app.callback(
    Output("consumer-trigger", "data"),
    Input("interval-component", "n_intervals")
)

def trigger_consumer(n):
    # 1. Start the consumer thread (if not already running)
    # start_consumer()
    
    # 2. Return status so Dash knows consumer is active
    return {"status": "started"}

# ------------------- DASH CALLBACK: Update Chart ------------------ #

@app.callback(
    Output('live-line-chart', 'figure'),
    Input('interval-component', 'n_intervals'),
    Input('view-mode-toggle', 'value'),
    State('department-store', 'data'),
    State('pause-store', 'data')
)
def update_graph_live(n, view_mode, departments, pause_data):
    if pause_data.get("paused"):
        return dash.no_update

    with data_lock:
        data_snapshot = list(consumed_data)

    current_counts = {dept: 0 for dept in departments}
    for record in data_snapshot:
        dept = record.get("department")
        if dept in current_counts:
            current_counts[dept] += 1

    for dept in departments:
        last_value = counts_history[dept][-1] if counts_history[dept] else 0
        change = random.choices(
            population=[-2, -1, 0, 1, 2],
            weights=[0.1, 0.3, 0.5, 0.4, 0.2],
            k=1
        )[0]
        new_value = max(0, last_value + change)
        counts_history[dept].append(new_value)

    # Slice history based on view mode
    if view_mode == 'latest':
        max_points = 30
    else:
        max_points = len(counts_history[departments[0]])

    data = [
        go.Scatter(
            x=list(range(len(counts_history[dept])))[-max_points:],
            y=counts_history[dept][-max_points:],
            mode='lines+markers',
            name=dept,
            hovertemplate=f"<b>Department:</b> {dept}<br>"
                          f"<b>Check-ins:</b> %{{y}}<br>"
                          f"<b>Time Interval:</b> %{{x}}<extra></extra>"
        )
        for dept in departments
    ]

    fig = go.Figure(data=data)
    fig.update_layout(
        height=700,
        title=dict(text="Patient Check-ins by Department", y=0.94, x=0.5),
        xaxis_title="Time Interval",
        yaxis_title="Number of Check-ins",
        yaxis=dict(range=[0, 50]),
    )
    fig.update_yaxes(autorange=True)

    return fig


# ----------------------- Data Table ----------------------- #

@app.callback(
    Output('check-in-table', 'figure'),
    Input('table-interval-component', 'n_intervals'),
    Input('consumer-trigger', 'data'),
    State('department-store', 'data'),
    State('pause-store', 'data')
)
def get_live_table_figure(n, trigger_data, departments, pause_data):
    
    # global consumed_data

    print(f"Updating chart at interval {n}")
    print(f"Consumed Data Length: {len(consumed_data)}")

    if pause_data.get("paused", False):
        return dash.no_update

    # Safely copy the current consumed data
    with data_lock:
        snapshot = list(consumed_data)

    # Build DataFrame from real consumed data only
    df_live = pd.DataFrame(snapshot)

    # Sort by check-in time descending
    if 'check_in_time' in df_live.columns:
        df_live = df_live.sort_values('check_in_time', ascending=False)

    # Ensure all expected columns exist
    all_columns = ['patient_id', 'check_in_time', "age", "sex", 'department', "complaint"]
    for col in all_columns:
        if col not in df_live.columns:
            df_live[col] = ''

    # Build table figure
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=all_columns,
            fill_color='paleturquoise',
            align='center',
            height=30,
            font=dict(size=12)
        ),
        cells=dict(
            values=[df_live[col] for col in all_columns],
            fill_color='lavender',
            align='left',
            height=25,
            font=dict(size=12)
        )
    )])

    fig.update_layout(
        margin=dict(l=50, r=50, t=30, b=40),
        height=500,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig

# ------------------- AI Summary ------------------ #

@app.callback(
    Output('checkin-summary', 'children'),
    Input('chatgpt-interval', 'n_intervals'),
    State('pause-store', 'data')
)
def update_summary(n, pause_data):
    if pause_data.get("paused", False):
        return dash.no_update

    with data_lock:
        if not consumed_data:
            # Generate dummy data like the table
            snapshot = []
            for dept in DEPARTMENTS:
                snapshot.append({
                    "patient_id": random.randint(1000, 9999),
                    "check_in_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "department": dept,
                    "complaint": random.choice(COMPLAINTS[dept]),
                    "sex": random.choice(["Male", "Female"]),
                    "age": random.randint(7, 90),
                })
            df_live = pd.DataFrame(snapshot)
        else:
            df_live = pd.DataFrame(consumed_data)

    # Pass the DataFrame (real or dummy) to OpenAI
    return summarize_checkins(df_live)

# ------------------- DASH CALLBACK: Reset Chart ------------------ #

@app.callback(
    Output("interval-component", "n_intervals"),
    Output("table-interval-component", "n_intervals"),
    Output("consumer-trigger", "data", allow_duplicate=True),
    Input("reset-button", "n_clicks"),
    prevent_initial_call=True
)

def reset_chart(n_clicks):
    global consumed_data

    # 1. Clear historical counts safely
    for dept in counts_history:
        counts_history[dept].clear()

    # 2. Clear consumed data safely (thread-safe)
    with data_lock:
        consumed_data.clear()

    # 3. Ensure the consumer is running so new messages populate immediately
    # start_consumer()  # Only starts if not already running

    # 4. Reset interval counter so chart/table callbacks update from 0
    return 0, 0, {"status": "reset"}

# ------------------- DASH CALLBACK: Pause/Resume Chart ------------------ #
@app.callback(
    Output("pause-store", "data"),  # track pause state
    Input("pause-button", "n_clicks"),
    State("pause-store", "data"),
    prevent_initial_call=True # 
)
def toggle_pause(n_clicks, pause_data):
    
    global paused
    
    # 1. Flip paused state each time button is clicked
    paused = not pause_data.get("paused", False)

    # 2. Return updated state
    return {"paused": paused}


# =========================== Status Text ======================= #

@app.callback(
    Output("stream-status", "children"),
    Output("stream-status", "style"),
    Input("pause-store", "data")
)
def update_stream_status(pause_data):
    base_style = {
        "display": "flex",
        "justify-content": "center",
        "align-items": "center",
        "color": "white",
        "margin": "0px 0px 0px 0px",
        "padding-top": "1px",
        "padding-bottom": "1px",
        "border-right": "2px solid black",
        "border-left": "2px solid black",
        "border-bottom": "2px solid black",
        "border-color": "rgb(186, 186, 186)",
        "border-radius": "0px",
        "text-align": "center",
        "font-family": 'Calibri',
        "font-size": '20px',
        "font-weight": "bold",
        "width":"10vw",
    }
    
    if pause_data.get("paused", False):
        return "Paused", {**base_style, "background-color": "red"}
    else:
        return "Live", {**base_style, "background-color": "mediumseagreen"}

# ================= Initiate Kafka Threads ================== #

# def start_threads():
#     producer_thread = threading.Thread(target=kafka_producer, daemon=True)
#     producer_thread.start()

#     consumer_thread = threading.Thread(target=kafka_consumer, daemon=True)
#     consumer_thread.start()

# if os.environ.get("DYNO"):  # Running on Heroku
#     start_threads()

def start_threads_once():
    global producer_started, consumer_started

    if not producer_started:
        threading.Thread(target=kafka_producer, daemon=True).start()
        producer_started = True
        print("🟢 Kafka producer thread launched")

    if not consumer_started:
        threading.Thread(target=kafka_consumer, daemon=True).start()
        consumer_started = True
        print("🟢 Kafka consumer thread launched")
        
@app.callback(
    Output("consumer-trigger", "data", allow_duplicate=True),
    Input("interval-component", "n_intervals"),
    prevent_initial_call=True
)
def trigger_consumer(n):
    start_threads_once()  # lazy-start producer + consumer
    return {"status": "started"}

    
# =========================== RUN APP & THREADS ======================= #

# print(f"Serving Flask app '{current_file}'! 🚀")

if __name__ == "__main__":
    
    print(f"Serving Flask app '{current_file}'! 🚀")
    # start_threads() 
    port = int(os.environ.get('PORT', 8050))
    app.run_server(host='0.0.0.0', port=port, debug=True)
    # app.run_server(host='0.0.0.0', port=port, debug=False)

# ----------------------- KILL PORT -------------------------- #

# netstat -ano | findstr :8050
# taskkill /PID 24772 /F
# npx kill-port 8050

# Check network access:
# nc -vz pkc-xxxxx.us-central1.gcp.confluent.cloud 9092

# -------------------- Host Application ------------------------ #

# 1. pip freeze > requirements.txt
# 2. add this to procfile: 'web: gunicorn app_name:server'

# python -m venv .venv # create venv

# cd "C:/Users/CxLos/OneDrive/Documents/Portfolio Projects/Machine Learning/Healthcare_Analytics_Architecture"
# python -m venv .venv

# source .venv/Scripts/activate # activate it
# which python # confirm you are using global or venv python

# Update PIP Setup Tools:
# pip freeze > requirements.txt # create requirements file
# pip install -r requirements.txt # install dependencies

# python.exe -m pip install --upgrade pip #upgrade pip
# pip install --upgrade pip setuptools

# Add git to path if accidentally removed:
# export PATH="/c/Program Files/Git/cmd:/c/Program Files/Git/usr/bin:$PATH" 

# Check dependency tree:
# pipdeptree
# pip show package-name

# Remove:
# pypiwin32
# pywin32
# jupytercore
# ipykernel
# ipython

# Add:
# gunicorn==22.0.0

# ------------ Heroku ---------------- #

# Name must start with a letter, end with a letter or digit and can only contain lowercase letters, digits, and dashes.

# Heroku Setup:
# heroku login
# heroku create patient-check-in-stream
# heroku git:remote -a patient-check-in-stream
# git push heroku main

# Set environment variables:
# heroku config:set API_KEY=your_actual_key_here

# Clear Heroku Cache:
# heroku plugins:install heroku-repo
# heroku repo:purge_cache -a mc-impact-11-2024

# Set buildpack for heroku
# heroku buildpacks:set heroku/python

# ----------------- Kafka --------------------- #

# From Kafka installation folder:

# cd into here:
# cd C:\kafka

# Start Zookeeper
# kafka/bin/zookeeper-server-start.sh config/zookeeper.properties
# cmd.exe /c "bin\windows\zookeeper-server-start.bat config\zookeeper.properties"
# java -cp "libs/*" -Dlog4j.configuration=file:config/log4j.properties org.apache.zookeeper.server.quorum.QuorumPeerMain config/zookeeper.properties

# Start Kafka server/ broker
# bin\windows\kafka-server-start.bat config\server.properties
# cmd.exe /c "\bin\windows\kafka-server-start.bat config\server.properties"
# java -cp "libs/*" -Dlog4j.configuration=file:config/log4j.properties org.apache.zookeeper.server.quorum.QuorumPeerMain config/zookeeper.properties



# Verify Kafka is listening to port 9092
# netstat -an | findstr 9092

# --------- Set environment variables ------------ #
