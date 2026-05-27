import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
from unittest.mock import patch, MagicMock
from app.data.ai import summarize_checkins
from app.config import DEPARTMENTS, COMPLAINTS
import random
from datetime import datetime


def _make_sample_df(n=5):
    rows = []
    for _ in range(n):
        dept = random.choice(DEPARTMENTS)
        rows.append({
            "patient_id": random.randint(1000, 9999),
            "check_in_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "department": dept,
            "complaint": random.choice(COMPLAINTS[dept]),
            "sex": random.choice(["Male", "Female"]),
            "age": random.randint(1, 99),
        })
    return pd.DataFrame(rows)


def test_summarize_checkins_returns_string():
    """summarize_checkins should always return a string."""
    df = _make_sample_df()
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices[0].message.content = "Summary text."

    with patch("app.data.ai._get_client", return_value=mock_client):
        result = summarize_checkins(df)

    assert isinstance(result, str)
    assert len(result) > 0


def test_summarize_checkins_handles_api_error():
    """On OpenAI failure, returns an error message string instead of raising."""
    df = _make_sample_df()
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API down")

    with patch("app.data.ai._get_client", return_value=mock_client):
        result = summarize_checkins(df)

    assert "Error" in result


def test_summarize_checkins_uses_recent_100_rows():
    """Passes at most 100 rows to the API regardless of DataFrame size."""
    df = _make_sample_df(n=200)
    captured = {}

    def fake_create(**kwargs):
        captured["messages"] = kwargs.get("messages", [])
        mock = MagicMock()
        mock.choices[0].message.content = "ok"
        return mock

    mock_client = MagicMock()
    mock_client.chat.completions.create = fake_create

    with patch("app.data.ai._get_client", return_value=mock_client):
        summarize_checkins(df)

    user_msg = captured["messages"][-1]["content"]
    # The prompt contains at most 100 serialized records
    assert user_msg.count("patient_id") <= 100
