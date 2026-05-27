# ============================= LAYOUT ============================== #

from dash import dcc, html
from app.config import DEPARTMENTS


def create_layout():
    return html.Div([

        # ------------- Header ----------- #
        html.Div(
            className='divv',
            children=[
                html.Div(
                    className='header-content',
                    children=[
                        html.H1('Real-Time Healthcare Data Pipeline', className='title'),
                        html.H1('With Apache Kafka', className='title2'),
                        html.Div(
                            className='btn-box',
                            children=[
                                html.A(
                                    'Repo',
                                    href='https://github.com/CxLos/Healthcare_Analytics_Architecture',
                                    className='repo-btn'
                                )
                            ]
                        )
                    ]
                )
            ]
        ),

        # ------------- Stream Controls ----------- #
        html.Div(
            className="kafka-row",
            children=[
                html.Div(
                    className='stream-border',
                    children=[
                        html.H1("🖥️ Live-Stream Dashboard", className="kafka-title"),
                    ]
                ),
                html.Div(
                    className='stream-buttons',
                    children=[
                        html.Button("⏯️", id="pause-button", n_clicks=0, title="Resume / Pause Stream"),
                        html.Button("🔄", id="reset-button", n_clicks=0, title="Reset Stream"),
                        dcc.Store(id="pause-store", data={"paused": False}),
                        dcc.Store(id="page-load-reset", data={"reset": True}),
                        dcc.Store(id="tab-closed-trigger", data=False, storage_type="session"),
                    ]
                ),
                dcc.RadioItems(
                    id='view-mode-toggle',
                    options=[
                        {'label': 'Full History', 'value': 'full'},
                        {'label': 'Latest 30', 'value': 'latest'},
                    ],
                    value='full',
                    labelStyle={'display': 'inline-block', 'margin-right': '10px'}
                ),
            ]
        ),

        # ----------- Live Stream Graph ------------- #
        html.Div(
            className="stream-row",
            children=[
                html.Div(id="stream-status", className="stream-status-text"),
                html.Div(
                    className="interval",
                    children=[
                        dcc.Store(id="department-store", data=DEPARTMENTS),
                        dcc.Store(id="consumer-trigger"),
                        dcc.Graph(className="line-graph", id='live-line-chart'),
                        dcc.Interval(
                            id='interval-component',
                            interval=2 * 1000,
                            n_intervals=0
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
                        html.H1("Quick Synopsis:", className="ai-title"),
                        html.Div(id='checkin-summary', className='gpt-response'),
                        dcc.Interval(
                            id='chatgpt-interval',
                            interval=20 * 1000,
                            n_intervals=0
                        )
                    ]
                ),

                # ---- Data Section ---- #
                html.Div(
                    className="data-box",
                    children=[
                        html.H1("Patient Check-in Table", className="data-title"),
                        dcc.Graph(className="check-in-table", id='check-in-table'),
                        dcc.Interval(
                            id='table-interval-component',
                            interval=2 * 1000,
                            n_intervals=0
                        )
                    ]
                ),
            ]
        ),

        # ------------- README ----------- #
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
                html.Pre(html.Code("python app/healthcare_analytics.py")),

                html.H4("🧪 Methodology"),
                html.P("Synthetic patient check-ins are created with:"),
                html.Ul([
                    html.Li("patient_id: (random 4-digit number)"),
                    html.Li("check_in_time: (current timestamp)"),
                    html.Li("department: (randomly selected from Cardiology, Oncology, Pediatrics etc...)"),
                ]),
                html.P(
                    "A background thread generates synthetic check-in events every 2 seconds "
                    "and appends them to a thread-safe queue consumed by the Dash dashboard."
                ),

                html.H4("🔍 Insights"),
                html.Ul([
                    html.Li("Demonstrates real-time streaming capabilities."),
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
