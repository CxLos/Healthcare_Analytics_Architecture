# ============================= IMPORTS ============================= #

import os
import sys
import json
import time
import random
import threading
from datetime import datetime
from collections import deque

from dotenv import load_dotenv
load_dotenv()

import dash
from dash import dcc, html, Output, Input, State
import plotly.graph_objects as go

from confluent_kafka import Producer, Consumer, KafkaError

# =========================== FILE ========================== #

current_dir = os.getcwd()
current_file = os.path.basename(__file__)
script_dir = os.path.dirname(os.path.abspath(__file__))

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

# Thread-safe queue for consumed messages
consumed_data = deque(maxlen=100)
data_lock = threading.Lock() 

# ============================ Globals =============================== #

# Thread-safe data store
consumed_data = []
consumer_started = False
consumer_running = False 
paused = False 
last_pause_state = None 

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
    
    while True:  # Infinite loop
        
        # 0. Check if producer should be paused
        if paused:
            if last_pause_state != paused:
                # print("⏸️ Kafka Producer paused")
                last_pause_state = paused
            time.sleep(0.5)
            continue
        else:
            if last_pause_state != paused:
                # print("▶️ Kafka Producer playing")
                last_pause_state = paused

        # 1. Create a random patient check-in message
        message = {
            "patient_id": random.randint(1000, 9999),
            "check_in_time": time.strftime('%Y-%m-%d %H:%M:%S'),
            "department": random.choice(DEPARTMENTS)
        }

        try:
            # 2. Serialize message to JSON and produce it to Kafka
            producer.produce(
                topic=KAFKA_TOPIC,
                value=json.dumps(message)
            )
            producer.poll(0)  # Serve delivery callbacks (non-blocking)
            # print(f"Produced: {message}")  # Optional logging

        except Exception as e:
            print(f"[Producer Error] {e}")

        # 3. Sleep a short time before next message
        time.sleep(0.5)                                       # Wait .5 seconds before producing next message


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
with data_lock:
    for _ in range(30):  # add 5 dummy check-ins
        consumed_data.append({
            "patient_id": random.randint(1000, 9999),
            "check_in_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "department": random.choice(DEPARTMENTS)
        })

# Consumer Function
def kafka_consumer():
    global consumer_running, paused, last_pause_state

    # print(f"🟢 Kafka consumer started at {datetime.now()}")
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
            msg = consumer.poll(0.3)
            if msg is None:
                time.sleep(0.1)
                continue

            if msg.error():
                continue

            try:
                parsed = json.loads(msg.value().decode('utf-8'))
                with data_lock:
                    consumed_data.append(parsed)
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
        ])
    ]),

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
            ]),
            html.Div(
                id="stream-status", 
                className="stream-status-text"), 
            dcc.Store(id="department-store", data=DEPARTMENTS),
            dcc.Store(id="consumer-trigger"),  # ⬅️ Added here
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
    ),
]),

#------------- README ----------- # 

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
    )
])

# ------------------- DASH CALLBACK: Trigger Consumer ------------------- #

@app.callback(
    Output("consumer-trigger", "data"),
    Input("interval-component", "n_intervals")
)

def trigger_consumer(n):
    # 1. Start the consumer thread (if not already running)
    start_consumer()
    
    # 2. Return status so Dash knows consumer is active
    return {"status": "started"}

# ------------------- DASH CALLBACK: Update Chart ------------------ #

# Keep track of historical counts per department
counts_history = {dept: [] for dept in DEPARTMENTS}

@app.callback(
    Output('live-line-chart', 'figure'),
    Input('interval-component', 'n_intervals'),
    State('department-store', 'data'),
    State('pause-store', 'data')  # <-- track paused state
)
def update_graph_live(n, departments, pause_data):
    # 1. Check if chart is paused
    if pause_data.get("paused"):
        return dash.no_update  # Do not update chart while paused

    # # 2. Print the current interval and the number of consumed records
    # print(f"Updating chart at interval {n}")
    # print(f"Consumed Data Length: {len(consumed_data)}")

    # 3. Safely copy the current consumed data using a lock
    with data_lock:
        data_snapshot = list(consumed_data)

    # 4. Initialize dictionary to count check-ins for each department
    current_counts = {dept: 0 for dept in departments}

    # 5. Count check-ins per department
    for record in data_snapshot:
        dept = record.get('department')
        if dept in current_counts:
            current_counts[dept] += 1

    # 6. Append counts to history for plotting
    for dept in departments:
        counts_history[dept].append(current_counts.get(dept, 0))

    # 7. Create Scatter objects for each department
    data = [
        go.Scatter(
            x=list(range(len(counts_history[dept]))),
            y=counts_history[dept],
            mode='lines+markers',
            name=dept,
            hovertemplate=f"<b>Department: </b>{dept}</br><b>Count: </b>%{{y}}<br><b>Time Interval: </b>%{{x}}<extra></extra>"
        )
        for dept in departments
    ]

    # 8. Create the figure and update layout
    fig = go.Figure(data=data)
    fig.update_layout(
        height=680,
        title=dict(
            text="Patient Check-ins by Department", 
            y=0.94, 
            x=0.5),
        xaxis=dict(
            title="Time Interval", 
            title_standoff=30),
        yaxis=dict(
            title="Number of Check-ins",
            title_standoff=30,
            range=[0, max(max(counts) for counts in counts_history.values()) + 1]
        )
    )

    # 9. Return updated figure
    return fig


# ------------------- DASH CALLBACK: Reset Chart ------------------ #

@app.callback(
    Output("interval-component", "n_intervals"),
    Input("reset-button", "n_clicks"),
    prevent_initial_call=True
)

def reset_chart(n_clicks):
    # 1. Clear consumed data safely
    with data_lock:
        consumed_data.clear()

    # 2. Clear historical counts
    for dept in counts_history:
        counts_history[dept].clear()

    # 3. Reset interval counter
    # print("🔁Dashboard cleared")
    return 0


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
        "color": "white",
        "margin": "10px 0px 0px 0px",
        "padding": "10px 10px 10px 10px",
        "border": "2px solid black",
        "border-radius": "100px",
        "text-align": "center",
        "font-family": 'Calibri',
        "font-size": '20px',
        "font-weight": "bold"
    }
    
    if pause_data.get("paused", False):
        return "Paused", {**base_style, "background-color": "red"}
    else:
        return "Live", {**base_style, "background-color": "mediumseagreen"}
    

# =========================== RUN APP & THREADS ======================= #

print(f"Serving Flask app '{current_file}'! 🚀")

if __name__ == "__main__":
    
    # Start Kafka producer thread (daemon so it ends when main thread ends)
    producer_thread = threading.Thread(target=kafka_producer, daemon=True)
    producer_thread.start()

    # Start Kafka consumer thread
    consumer_thread = threading.Thread(target=kafka_consumer, daemon=True)
    consumer_thread.start()

    # Run Dash app on all interfaces and appropriate port (for Heroku)
    port = int(os.environ.get('PORT', 8050))
    app.run_server(host='0.0.0.0', port=port, debug=True)
    # app.run_server(host='0.0.0.0', port=port, debug=False)

# -------------------------------------------- KILL PORT ---------------------------------------------------

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