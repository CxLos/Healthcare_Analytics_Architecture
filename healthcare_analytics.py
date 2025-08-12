# ============================= IMPORTS ============================= #

import os
import sys
import json
import time
import random
import threading
from collections import deque

from dotenv import load_dotenv
load_dotenv()

import dash
from dash import dcc, html, Output, Input
import plotly.graph_objects as go

from confluent_kafka import Producer, Consumer, KafkaError

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
]

# Thread-safe queue for consumed messages
consumed_data = deque(maxlen=100)
data_lock = threading.Lock()

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
def delivery_report(err, msg):
    if err is not None:
        # If there's an error delivering the message, print an error message
        print(f"❌ Delivery failed: {err}")
    else:
        # Otherwise, print success with topic, partition, and offset info
        print(f"✅ Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")

# single test message to verify connection
try:
    test_message = '{"test": "connectivity"}'                  # JSON string to test connectivity
    producer.produce(KAFKA_TOPIC, value=test_message, callback=delivery_report)  # Send test message
    producer.flush()                                           # Wait for all messages to be delivered
except Exception as e:
    print(f"🔥 Connection error: {e}")                         # Print connection error if it fails

# function to produce random patient check-in messages continuously
def kafka_producer():
    while True:                                                # Infinite loop
        message = {
            "patient_id": random.randint(1000, 9999),         # Random patient ID between 1000 and 9999
            "check_in_time": time.strftime('%Y-%m-%d %H:%M:%S'), # Current date and time string
            "department": random.choice(DEPARTMENTS)          # Randomly pick a department
        }
        try: 
            # Serialize the message to JSON and produce it to Kafka with a delivery callback
            producer.produce(
                topic=KAFKA_TOPIC,
                value=json.dumps(message),
                callback=delivery_report
            )
            producer.poll(0)                                   # Serve delivery callbacks (non-blocking)
            print(f"Produced: {message}")                      # Print the produced message to console
        except Exception as e:
            print(f"[Producer Error] {e}")                     # Print error if produce fails

        time.sleep(2)                                          # Wait 2 seconds before producing next message


# ============================ CONSUMER =============================== #

# Kafka consumer configuration dictionary with connection, authentication, and consumer-specific settings
consumer_conf = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,   # Kafka cluster address
    'security.protocol': 'SASL_SSL',                 # Use SASL over SSL for security
    'sasl.mechanisms': 'PLAIN',                       # SASL mechanism is PLAIN (username/password)
    'sasl.username': KAFKA_API_KEY,                   # Kafka API key
    'sasl.password': KAFKA_API_SECRET,                # Kafka API secret
    'group.id': 'connectivity_test_group',            # Consumer group ID for coordination
    'auto.offset.reset': 'earliest',                   # Start reading from earliest message if no offset stored
    'enable.auto.commit': True                         # Automatically commit offsets after messages are read
}

# Kafka Consumer instance with the above configuration
consumer = Consumer(consumer_conf)

# Subscribe this consumer to the topic you want to consume from
consumer.subscribe([KAFKA_TOPIC])
print("📡 Subscribed to topic:", KAFKA_TOPIC)

# Sleep for 2 seconds to allow Kafka to assign partitions to this consumer
time.sleep(2)

# function to continuously consume messages from Kafka
def kafka_consumer():
    try:
        # Subscribe again inside the function
        consumer.subscribe([KAFKA_TOPIC])
        print("📡 Subscribed to topic:", KAFKA_TOPIC)
        time.sleep(2)  # Allow time for partition assignment

        # Infinite loop to keep polling for new messages
        while True:
            # Poll Kafka broker, waiting up to 1 second for a message
            msg = consumer.poll(1.0)

            if msg is None:
                # No message received in this poll, continue looping
                continue

            if msg.error():
                # If there's an error with the message, print it and skip processing
                print(f"❌ Consumer error: {msg.error()}")
                continue

            # Decode the message value from bytes to a JSON object (dictionary)
            data = json.loads(msg.value().decode('utf-8'))

            # Print received data to console for monitoring
            print(f"✅ Received message: {data}")

            # Safely append the consumed data to a shared thread-safe queue with a lock
            with data_lock:
                consumed_data.append(data)

    except Exception as e:
        # error if the consumer encounters connection or runtime problems
        print(f"🔥 Consumer connection error: {e}")

    finally:
        # Always close the consumer cleanly on exit
        consumer.close()

# ============================= DASH APP ============================== #

app = dash.Dash(__name__)
server = app.server

# Keep track of historical counts per department
counts_history = {dept: [] for dept in DEPARTMENTS}

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
                "Live Patient Check-ins by Department",
                className="kafka-title"
            ),
            dcc.Graph(
                className="line-graph",
                id='live-bar-chart'
            ),
            html.Div(
                className="interval",
                children=[
                    dcc.Interval(
                        id='interval-component',
                        interval=3 * 1000,  # every 3 seconds
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


@app.callback(
    Output('live-bar-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_graph_live(n):
    print(f"Updating chart at interval {n}")
    print(f"Consumed Data Length: {len(consumed_data)}")
    
    # Grab a thread-safe copy of the latest consumed data
    with data_lock:
        data_snapshot = list(consumed_data)

    # Count how many check-ins happened per department right now
    current_counts = {dept: 0 for dept in DEPARTMENTS}
    for record in data_snapshot:
        dept = record.get('department')
        if dept in current_counts:
            current_counts[dept] += 1

    # Add these counts to the running history for each department
    for dept in DEPARTMENTS:
        counts_history[dept].append(current_counts.get(dept, 0))

    # Build a list of line traces for the chart, one per department
    data = []
    for dept in DEPARTMENTS:
        data.append(go.Scatter(
            x=list(range(len(counts_history[dept]))),  # x is just the interval index
            y=counts_history[dept],                    # y is the count history for this dept
            mode='lines+markers',                      # show lines with dots on points
            name=dept,                                 # label the line with the department name
            hovertemplate=f"{dept}: <b>%{{y}}</b><extra></extra>"
        ))

    # Put it all together in a Figure with titles and axis labels
    fig = go.Figure(data=data)
    fig.update_layout(
        height=700,
        xaxis_title="Time Interval",
        yaxis_title="Number of Check-ins",
        yaxis=dict(range=[0, max(max(counts) for counts in counts_history.values()) + 1])  # y-axis from 0 to max count + 1
    )
    return fig


# =========================== RUN APP & THREADS ======================= #

if __name__ == "__main__":
    # Start Kafka producer thread (daemon so it ends when main thread ends)
    producer_thread = threading.Thread(target=kafka_producer, daemon=True)
    producer_thread.start()

    # Start Kafka consumer thread
    consumer_thread = threading.Thread(target=kafka_consumer, daemon=True)
    consumer_thread.start()

    # Run Dash app on all interfaces and appropriate port (for Heroku)
    port = int(os.environ.get('PORT', 8050))
    # app.run_server(host='0.0.0.0', port=port, debug=True)
    app.run_server(host='0.0.0.0', port=port, debug=False)

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
