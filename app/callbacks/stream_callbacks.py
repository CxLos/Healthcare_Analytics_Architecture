# ============================= CALLBACKS ============================== #

import random
import pandas as pd
from datetime import datetime

import dash
from dash import Output, Input, State
import plotly.graph_objects as go

from app import config as cfg
from app.data.ai import summarize_checkins
from app.data.generator import start_threads_once


def register_callbacks(app):

    # ------------------- Trigger Stream Thread ------------------- #

    @app.callback(
        Output("consumer-trigger", "data", allow_duplicate=True),
        Input("interval-component", "n_intervals"),
        prevent_initial_call=True
    )
    def trigger_stream(n):
        start_threads_once()
        return {"status": "started"}

    # ------------------- Update Line Chart ------------------ #

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

        with cfg.data_lock:
            data_snapshot = list(cfg.consumed_data)

        current_counts = {dept: 0 for dept in departments}
        for record in data_snapshot:
            dept = record.get("department")
            if dept in current_counts:
                current_counts[dept] += 1

        for dept in departments:
            last_value = cfg.counts_history[dept][-1] if cfg.counts_history[dept] else 0
            change = random.choices(
                population=[-2, -1, 0, 1, 2],
                weights=[0.1, 0.3, 0.5, 0.4, 0.2],
                k=1
            )[0]
            new_value = max(0, last_value + change)
            cfg.counts_history[dept].append(new_value)

        if view_mode == 'latest':
            max_points = 30
        else:
            max_points = len(cfg.counts_history[departments[0]])

        data = [
            go.Scatter(
                x=list(range(len(cfg.counts_history[dept])))[-max_points:],
                y=cfg.counts_history[dept][-max_points:],
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
            title=dict(text="Patient Check-ins by Department", y=0.94, x=0.5),
            xaxis_title="Time Interval",
            yaxis_title="Number of Check-ins",
            xaxis=dict(gridcolor="#b0b0b0"),
            yaxis=dict(range=[0, 50], gridcolor="#b0b0b0"),
            paper_bgcolor="#E2E2E2",
            plot_bgcolor="#FFFFFF",
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
        print(f"Updating table at interval {n}")
        print(f"Consumed Data Length: {len(cfg.consumed_data)}")

        if pause_data.get("paused", False):
            return dash.no_update

        with cfg.data_lock:
            snapshot = list(cfg.consumed_data)

        df_live = pd.DataFrame(snapshot)

        if 'check_in_time' in df_live.columns:
            df_live = df_live.sort_values('check_in_time', ascending=False)

        all_columns = ['patient_id', 'check_in_time', "age", "sex", 'department', "complaint"]
        for col in all_columns:
            if col not in df_live.columns:
                df_live[col] = ''

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
            paper_bgcolor="rgb(193, 193, 193)",
            shapes=[
                dict(
                    type="rect",
                    xref="paper", yref="paper",
                    x0=0, y0=0, x1=1, y1=1,
                    line=dict(color="black", width=2),
                    fillcolor="rgba(0,0,0,0)"
                )
            ],
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

        with cfg.data_lock:
            if not cfg.consumed_data:
                snapshot = []
                for dept in cfg.DEPARTMENTS:
                    snapshot.append({
                        "patient_id": random.randint(1000, 9999),
                        "check_in_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "department": dept,
                        "complaint": random.choice(cfg.COMPLAINTS[dept]),
                        "sex": random.choice(["Male", "Female"]),
                        "age": random.randint(7, 90),
                    })
                df_live = pd.DataFrame(snapshot)
            else:
                df_live = pd.DataFrame(cfg.consumed_data)

        return summarize_checkins(df_live)

    # ------------------- Reset Chart ------------------ #

    @app.callback(
        Output("interval-component", "n_intervals"),
        Output("table-interval-component", "n_intervals"),
        Output("consumer-trigger", "data", allow_duplicate=True),
        Input("reset-button", "n_clicks"),
        prevent_initial_call=True
    )
    def reset_chart(n_clicks):
        for dept in cfg.counts_history:
            cfg.counts_history[dept].clear()
        with cfg.data_lock:
            cfg.consumed_data.clear()
        return 0, 0, {"status": "reset"}

    # ------------------- Pause / Resume ------------------ #

    @app.callback(
        Output("pause-store", "data"),
        Input("pause-button", "n_clicks"),
        State("pause-store", "data"),
        prevent_initial_call=True
    )
    def toggle_pause(n_clicks, pause_data):
        cfg.paused = not pause_data.get("paused", False)
        return {"paused": cfg.paused}

    # ------------------- Stream Status Text ------------------ #

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
            "padding-bottom": "0px",
            "border-right": "2px solid black",
            "border-left": "2px solid black",
            "border-top": "2px solid black",
            "border-color": "black",
            "border-radius": "0px",
            "text-align": "center",
            "font-family": 'Calibri',
            "font-size": '20px',
            "font-weight": "bold",
            "width": "10vw",
        }
        if pause_data.get("paused", False):
            return "Paused", {**base_style, "background-color": "red"}
        return "Live", {**base_style, "background-color": "mediumseagreen"}
