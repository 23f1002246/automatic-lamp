import os
import json
import openai


# Initialize the OpenAI client (make sure your key is set)
openai.api_key = os.environ.get("OPENAI_API_KEY")


def generate_app_code(brief: str, attachments: list = None):
    """
    Use the LLM to generate minimal HTML/JS/CSS and a README.md
    for the given task brief and attachments.
    """

    attachments_note = ""
    if attachments:
        attachments_list = [a["name"] for a in attachments]
        attachments_note = f"\nAttached files: {', '.join(attachments_list)}"

    prompt = f"""
You are a professional web developer.
Generate a **fully working minimal app** as per this brief:

{brief}
{attachments_note}

The output must include:

1. A single HTML file (index.html) that:
   - Works standalone
   - Uses Bootstrap 5 if asked
   - Loads external JS libraries (like marked, highlight.js, etc.) via CDN if mentioned
   - Uses only plain JS (no build tools)
   - Is responsive and loads fast

2. A README.md with:
   - Project summary (based on the brief)
   - Setup instructions (how to open or test)
   - Explanation of major code parts
   - License reference (MIT)

Return a JSON object with these keys exactly:
{
  "index.html": "<full HTML code>",
  "README.md": "<full Markdown readme>"
}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    content = response["choices"][0]["message"]["content"].strip()

    # Try to extract JSON content safely
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        json_str = content[start:end]
        app_data = json.loads(json_str)
    except Exception:
        raise ValueError(f"LLM output could not be parsed as JSON:\n{content}")

    return app_data


def update_app_code(existing_readme: str, brief: str, round_num: int):
    """
    For round 2 and beyond, request the LLM to modify the app based on new instructions.
    """

    prompt = f"""
You are now updating an existing student web app for round {round_num}.
Follow this new brief:

{brief}

You are given the previous README.md:
---
{existing_readme}
---

Make necessary changes to HTML and update README.md accordingly.

Return a JSON object with these keys:
{
  "index.html": "<updated HTML>",
  "README.md": "<updated README>"
}
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    content = response["choices"][0]["message"]["content"].strip()

    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        json_str = content[start:end]
        updated_data = json.loads(json_str)
    except Exception:
        raise ValueError(f"LLM output could not be parsed as JSON:\n{content}")

    return updated_data
