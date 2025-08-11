# ------ System Imports ------ #
import os
import sys
import time
import json
import random
import threading
from collections import deque

# ------ Python Imports ------ #
import numpy as np 
import pandas as pd 
import plotly.graph_objects as go

# ------- Kafka -------- #
from kafka import KafkaProducer, KafkaConsumer

# ------ Dash Imports ------ #
import dash
from dash import dcc, html, Output, Input

# ---------------------------- Globals ---------------------------- #

# Thread-safe deque for consumed Kafka messages
consumed_data = deque(maxlen=100)
data_lock = threading.Lock()

# Kafka config
KAFKA_TOPIC = 'patient_checkins'
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']

# Departments for message generation and display
DEPARTMENTS = ["Cardiology", "Oncology", "Pediatrics"]

# ---------------- Producer ---------------- #
def kafka_producer():
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        while True:
            message = {
                "patient_id": random.randint(1000, 9999),
                "check_in_time": time.strftime('%Y-%m-%d %H:%M:%S'),
                "department": random.choice(DEPARTMENTS)
            }
            producer.send(KAFKA_TOPIC, message)
            print(f"Produced: {message}")
            time.sleep(2)
    except Exception as e:
        print(f"[Producer Error] {e}")

# ---------------- Consumer ---------------- #
def kafka_consumer():
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset='earliest',
            group_id='dash_consumer_group',
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        for message in consumer:
            data = message.value
            print(f"Consumed: {data}")
            with data_lock:
                consumed_data.append(data)
    except Exception as e:
        print(f"[Consumer Error] {e}")

# ----------------------------- Dash App ----------------------------- #
app = dash.Dash(__name__)
server = app.server

app.layout = html.Div(children=[
    html.Div(className='divv', children=[
        html.H1('Healthcare Analytics Architecture Demo', className='title'),
        html.Div(className='btn-box', children=[
            html.A('Repo', href='https://github.com/CxLos/Healthcare_Analytics_Architecture', className='btn')
        ])
    ]),

    html.Div([
        html.H1("Live Patient Check-ins by Department"),
        dcc.Graph(id='live-bar-chart'),
        dcc.Interval(
            id='interval-component',
            interval=3*1000,
            n_intervals=0
        )
    ]),

    html.Div(className='readme-section', children=[
        html.H2("📘 README"),
        html.H4("📝 Description"),
        html.P("This dashboard provides real-time insights into patient check-ins across hospital departments."),

        html.H4("📦 Installation"),
        html.P("To run this project locally, follow these steps:"),
        html.Pre(html.Code(
            "git clone https://github.com/CxLos/Healthcare_Analytics_Architecture\n"
            "cd Healthcare_Analytics_Architecture\n"
            "pip install -r requirements.txt"
        )),

        html.H4("▶️ Usage"),
        html.P("Run this dashboard with:"),
        html.Pre(html.Code("python healthcare_dashboard.py")),

        html.H4("🧪 Methodology"),
        html.P("Kafka streams simulate patient check-ins, which are consumed and visualized in real time."),

        html.H4("🔍 Insights"),
        html.Ul([
            html.Li("Track department load in real time."),
            html.Li("Identify peak check-in periods."),
            html.Li("Monitor operational flow across hospital units.")
        ]),

        html.H4("✅ Conclusion"),
        html.P("Real-time analytics can improve resource allocation and patient flow management."),

        html.H4("📄 License"),
        html.P("MIT License © 2025 CxLos"),
        html.Code(
            "Permission is hereby granted, free of charge, to any person obtaining a copy of this software..."
        )
    ])
])

@app.callback(
    Output('live-bar-chart', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_graph_live(n):
    print(f"Updating chart at interval {n}")
    with data_lock:
        print(f"Consumed Data Length: {len(consumed_data)}")

        # Aggregate counts by department
        counts = {}
        for record in consumed_data:
            dept = record.get('department')
            if dept:
                counts[dept] = counts.get(dept, 0) + 1

    # Use dummy data if no records yet
    if not counts:
        departments = DEPARTMENTS
        values = [0, 0, 0]
    else:
        departments = list(counts.keys())
        values = list(counts.values())

    fig = go.Figure(data=[go.Bar(x=departments, y=values)])
    fig.update_layout(
        height=700,
        xaxis_title="Department",
        yaxis_title="Number of Check-ins",
        yaxis=dict(range=[0, max(values + [1])])
    )
    return fig

# ---------------------- End ------------------------- #
if __name__ == "__main__":
    # Start producer thread
    producer_thread = threading.Thread(target=kafka_producer, daemon=True)
    producer_thread.start()

    # Start consumer thread
    consumer_thread = threading.Thread(target=kafka_consumer, daemon=True)
    consumer_thread.start()

    # Let threads warm up
    time.sleep(5)

    # Run Dash app
    app.run_server(debug=True)