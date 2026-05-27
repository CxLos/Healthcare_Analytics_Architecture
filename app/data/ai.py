# ============================= OpenAI ============================== #

import os
from openai import OpenAI

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def summarize_checkins(df_live):
    recent_data = df_live.head(100).to_dict(orient='records')
    recent_data_str = "\n".join([str(record) for record in recent_data])
    prompt = (
        "You are a healthcare analytics assistant. "
        "Provide a descriptive summary in about 2 paragraphs explaining commonly reported symptoms, any possible trends, and just any other general information you think might be useful in human-readable text:\n\n"
        f"{recent_data_str}"
    )

    try:
        response = _get_client().chat.completions.create(
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
