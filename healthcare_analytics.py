# =================================== IMPORTS ================================= #

# ------ System Imports ------ #
import os
import sys

# ------ Python Imports ------ #
import numpy as np 
import pandas as pd 
import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
import plotly.express as px

# ------- Kafka -------- #
from kafka import KafkaProducer, KafkaConsumer
import json, time
import random
import threading
from collections import deque

# ------- Spark -------- #
# from pyspark.sql import SparkSession
# from pyspark.sql.functions import from_json, col
# from pyspark.sql.types import StructType, StringType, IntegerType

# ------ Dash Imports ------ #
import dash
from dash import dcc, html, Output, Input

# Global queue to store consumed messages (maxlen limits memory)
consumed_data = deque(maxlen=100)

# Kafka configs
KAFKA_TOPIC = 'patient_checkins'
KAFKA_BOOTSTRAP_SERVERS = ['localhost:9092']

# -------------------------------------- DATA ------------------------------------------- #

# current_dir = os.getcwd()
# current_file = os.path.basename(__file__)
# script_dir = os.path.dirname(os.path.abspath(__file__))
# print(f"Current Directory: {current_dir}")
# print(f"Current File: {current_file}")
# print(f"Script Directory: {script_dir}")

# file = os.path.join(script_dir, 'data', 'education_inequality_data.csv')
# df = pd.read_csv(file)

# print(df.head(10))
# print(f'DF Shape: \n {df.shape}')
# print(f'Number of rows: {df.shape[0]}')
# print(f'Column names: \n {df.columns}')
# print(df.info())
# print(df.describe())
# print(df.dtypes)

# ---------------- Producer ---------------- #

def kafka_producer():
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    departments = ["Cardiology", "Oncology", "Pediatrics"]
    
    while True:
        message = {
            "patient_id": random.randint(1000, 9999),
            "check_in_time": time.strftime('%Y-%m-%d %H:%M:%S'),
            "department": random.choice(departments)
        }
        producer.send(KAFKA_TOPIC, message)
        print(f"Produced: {message}")
        time.sleep(2)  # produce every 2 seconds

# ---------------- Consumer ---------------- #

def kafka_consumer():
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        auto_offset_reset='latest',
        group_id='dash_consumer_group',
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    for message in consumer:
        data = message.value
        print(f"Consumed: {data}")
        consumed_data.append(data)

# ------------------ Data Table for Dash ------------------ #

# df_table = go.Figure(data=[go.Table(
#     header=dict(
#         values=list(df.columns),
#         fill_color='paleturquoise',
#         align='center',
#         font=dict(size=12)
#     ),
#     cells=dict(
#         values=[df[col] for col in df.columns],
#         fill_color='lavender',
#         align='left',
#         font=dict(size=12)
#     )
# )])

# df_table.update_layout(
#     margin=dict(l=50, r=50, t=30, b=40),
#     paper_bgcolor='rgba(0,0,0,0)',
#     plot_bgcolor='rgba(0,0,0,0)'
# )

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
    
    html.Div(className='data-section', children=[
        html.Div(className='data-row', children=[
            html.Div(className='data-title', children=[
                html.H1('Healthcare Analytics Data Table', className='table-title')
            ]),
            html.Div(className='data-table', children=[
                dcc.Graph(
                    # figure=df_table
                    )
            ])
        ]),
    ]),
    
    html.Div([
        html.H1("Live Patient Check-ins by Department"),
            dcc.Graph(id='live-bar-chart'),
            dcc.Interval(
                id='interval-component',
                interval=3*1000,  # 3000 milliseconds = 3 seconds
                n_intervals=0
            )
    ]),
    
    html.Div(className='readme-section', children=[
        html.H2("📘 README"),
        html.H4("📝 Description"),
        html.P("This dashboard provides insights into educational inequality data."),

        html.H4("📦 Installation"),
        html.P("To run this project locally, follow these steps:"),
        html.Pre(html.Code(
            "git clone https://github.com/CxLos/Education_Inequality\n"
            "cd Education_Inequality\n"
            "pip install -r requirements.txt"
        )),

        html.H4("▶️ Usage"),
        html.P("Run this dashboard with:"),
        html.Pre(html.Code("python edu_inequality.py")),

        html.H4("🧪 Methodology"),
        html.P("Dataset sourced from Kaggle with features including funding, test scores, and dropout rates."),

        html.H4("🔍 Insights"),
        html.Ul([
            html.Li("Schools with higher funding tend to have lower dropout rates."),
            html.Li("Dropout rates are higher in schools with more low-income or minority students."),
            html.Li("Better internet access correlates with improved outcomes.")
        ]),

        html.H4("🌟 Feature Importance"),
        html.Ul([
            html.Li("Percent Low-Income"),
            html.Li("Funding Per Student"),
            html.Li("Student-Teacher Ratio"),
            html.Li("Internet Access Percent")
        ]),

        html.H4("✅ Conclusion"),
        html.P("Equitable resource allocation improves student retention and performance."),

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
    # Aggregate counts by department
    counts = {}
    for record in consumed_data:
        dept = record['department']
        counts[dept] = counts.get(dept, 0) + 1

    departments = list(counts.keys())
    values = list(counts.values())

    fig = go.Figure(data=[go.Bar(x=departments, y=values)])
    fig.update_layout(
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

    # Run Dash app
    app.run_server(debug=True)
    
# =================================== Updated Database ================================= #

# updated_path = f'data/kidney_disease_outcome_cleaned.xlsx'.xlsx'
# data_path = os.path.join(script_dir, updated_path)

# with pd.ExcelWriter(data_path, engine='xlsxwriter') as writer:
#     df.to_excel(
#             writer, 
#             sheet_name=f'Engagement {current_month} {report_year}', 
#             startrow=1, 
#             index=False
#         )

#     # Access the workbook and each worksheet
#     workbook = writer.book
#     sheet1 = writer.sheets['Kidney Disease Outcome']
    
#     # Define the header format
#     header_format = workbook.add_format({
#         'bold': True, 
#         'font_size': 13, 
#         'align': 'center', 
#         'valign': 'vcenter',
#         'border': 1, 
#         'font_color': 'black', 
#         'bg_color': '#B7B7B7',
#     })
    
#     # Set column A (Name) to be left-aligned, and B-E to be right-aligned
#     left_align_format = workbook.add_format({
#         'align': 'left',  # Left-align for column A
#         'valign': 'vcenter',  # Vertically center
#         'border': 0  # No border for individual cells
#     })

#     right_align_format = workbook.add_format({
#         'align': 'right',  # Right-align for columns B-E
#         'valign': 'vcenter',  # Vertically center
#         'border': 0  # No border for individual cells
#     })
    
#     # Create border around the entire table
#     border_format = workbook.add_format({
#         'border': 1,  # Add border to all sides
#         'border_color': 'black',  # Set border color to black
#         'align': 'center',  # Center-align text
#         'valign': 'vcenter',  # Vertically center text
#         'font_size': 12,  # Set font size
#         'font_color': 'black',  # Set font color to black
#         'bg_color': '#FFFFFF'  # Set background color to white
#     })

#     # Merge and format the first row (A1:E1) for each sheet
#     sheet1.merge_range('A1:N1', f'Engagement Report {current_month} {report_year}', header_format)

#     # Set column alignment and width
#     # sheet1.set_column('A:A', 20, left_align_format)   

#     print(f"Kidney Disease Excel file saved to {data_path}")

# -------------------------------------------- KILL PORT ---------------------------------------------------

# netstat -ano | findstr :8050
# taskkill /PID 24772 /F
# npx kill-port 8050

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
# heroku create education-inequality-llm
# heroku git:remote -a education-inequality-llm
# git push heroku main

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
# bin/zookeeper-server-start.sh config/zookeeper.properties
# cmd.exe /c "bin\windows\zookeeper-server-start.bat config\zookeeper.properties"
# java -cp "libs/*" -Dlog4j.configuration=file:config/log4j.properties org.apache.zookeeper.server.quorum.QuorumPeerMain config/zookeeper.properties

# Start Kafka server/ broker
# bin\windows\zookeeper-server-start.bat config\zookeeper.properties
# cmd.exe /c "bin\windows\kafka-server-start.bat config\server.properties"
# java -cp "libs/*" -Dlog4j.configuration=file:config/log4j.properties org.apache.zookeeper.server.quorum.QuorumPeerMain config/zookeeper.properties



# Verify Kafka is listening to port 9092
# netstat -an | findstr 9092

# --------- Set environment variables ------------ #


