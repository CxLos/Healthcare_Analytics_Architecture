
# =========================== Imports ========================== #

import os
import sys

# Ensure project root is on sys.path when running this file directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import dash

from app.layouts.layout import create_layout
from app.callbacks.stream_callbacks import register_callbacks

# =========================== DASH APP ========================== #

assets_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
app = dash.Dash(__name__, assets_folder=assets_folder)
server = app.server

app.layout = create_layout()
register_callbacks(app)

# =========================== RUN APP ========================== #

if __name__ == "__main__":
    current_file = os.path.basename(__file__)
    print(f"Serving Flask app '{current_file}'! 🚀")
    port = int(os.environ.get('PORT', 8050))
    app.run(host='0.0.0.0', port=port, debug=True)

# ----------------------- KILL PORT -------------------------- #

# netstat -ano | findstr :8050
# taskkill /PID 24772 /F
# npx kill-port 8050

# -------------------- Host Application ------------------------ #

# 1. pip freeze > requirements.txt
# 2. add this to procfile: 'web: gunicorn app.healthcare_analytics:server'

# python -m venv .venv
# source .venv/Scripts/activate
# pip install -r requirements.txt

# ------------ Heroku ---------------- #

# heroku login
# heroku create patient-check-in-stream
# heroku git:remote -a patient-check-in-stream
# git push heroku main
# heroku config:set API_KEY=your_actual_key_here
# heroku buildpacks:set heroku/python

