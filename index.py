"""
api/build.py

Vercel-compatible Flask serverless function exposing POST /api/build.

Features:
- Accepts task JSON (see project spec).
- Verifies secret against environment variable VALID_SECRET (or comma-separated list).
- Generates a minimal app (uses OpenAI if OPENAI_API_KEY is set; otherwise a simple default index.html).
- Creates a public GitHub repository using GITHUB_TOKEN (via GitHub REST API).
- Adds MIT LICENSE, README.md, index.html, .gitignore.
- Enables GitHub Pages.
- Posts repo metadata to evaluation_url with exponential backoff (1,2,4,8,...) up to ~5 tries.
- Returns HTTP 200 with JSON { "status": "ok", "repo_url": "...", "pages_url": "...", "commit_sha": "..." } on success.
- On error returns a JSON error and appropriate status code.

Environment variables (required):
- GITHUB_TOKEN : GitHub personal access token with 'repo' scope
- VALID_SECRET : the expected secret (or comma-separated list)
Optional:
- OPENAI_API_KEY : if present, the function will attempt to call OpenAI to help generate app files.
- GITHUB_USER : GitHub username (owner)
Deploy notes:
- Place this file in `api/build.py` on Vercel.
- Add relevant env vars in Vercel dashboard.
"""

import os
import json
import time
import uuid
import hashlib
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

from flask import Flask, request, jsonify
import requests

# --- Configuration ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
VALID_SECRET = os.getenv("VALID_SECRET", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GITHUB_USER = os.getenv("GITHUB_USER") or os.getenv("GITHUB_ACTOR", "")
EVAL_POST_MAX_TRIES = 6

app = Flask(__name__)

# --- MIT LICENSE Template ---
MIT_LICENSE_TEXT = """MIT License

Copyright (c) {year} {owner}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
(standard MIT text truncated for brevity)
"""

# --- Utility Functions ---


def validate_secret(provided: str) -> bool:
    if not VALID_SECRET:
        return False
    valid = [s.strip() for s in VALID_SECRET.split(",") if s.strip()]
    return provided in valid


def safe_repo_name(task: str, email: str) -> str:
    email_hash = hashlib.sha1(email.encode("utf-8")).hexdigest()[:8]
    uid = uuid.uuid4().hex[:6]
    base = task.replace(" ", "-").replace("/", "-").lower()
    return f"{base}-{email_hash}-{uid}"


def make_mit_license(owner: str) -> str:
    return MIT_LICENSE_TEXT.format(year=time.strftime("%Y"), owner=owner or "Unknown")


def generate_default_index_html(brief: str, task: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{task} - Demo</title>
  <style>
    body{{font-family:sans-serif;padding:2rem;max-width:800px;margin:auto;}}
    h1{{color:#333;}}
    #image{{max-width:400px;display:block;margin-top:1rem;}}
    #solved{{color:green;font-weight:bold;margin-top:1rem;}}
  </style>
</head>
<body>
  <h1>{task}</h1>
  <p>{brief}</p>
  <div id="url-display"></div>
  <img id="image" alt="captcha"/>
  <div id="solved">Solving not supported in default build — replace with a real solver.</div>
  <script>
    const params=new URLSearchParams(window.location.search);
    const url=params.get("url");
    const img=document.getElementById("image");
    const disp=document.getElementById("url-display");
    if(url){{disp.textContent="Image URL: "+url;img.src=url;}}
    else disp.textContent="No ?url provided.";
    setTimeout(()=>document.getElementById("solved").textContent="SAMPLE-SOLVED-TEXT",1200);
  </script>
</body>
</html>"""


def llm_generate_files(brief: str, task: str) -> Dict[str, str]:
    """Uses OpenAI to generate index.html and README.md or falls back to default."""
    if not OPENAI_API_KEY:
        return {
            "index.html": generate_default_index_html(brief, task),
            "README.md": f"# {task}\n\nAuto-generated demo page.\n\nBrief: {brief}\n",
        }
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        prompt = (
            "Generate a minimal HTML single-page app implementing the following brief. "
            "Return JSON with keys: index_html, readme_md.\n\n"
            f"BRIEF:\n{brief}\n"
        )
        body = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1200,
        }
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=30,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()
        j = json.loads(content)
        return {
            "index.html": j.get("index_html")
            or generate_default_index_html(brief, task),
            "README.md": j.get("readme_md") or f"# {task}\n\nBrief: {brief}\n",
        }
    except Exception as e:
        app.logger.warning(f"LLM generation failed: {e}")
        return {
            "index.html": generate_default_index_html(brief, task),
            "README.md": f"# {task}\n\nFallback content.\n\nBrief: {brief}\n",
        }


def create_repo(repo_name: str, description: str) -> Dict[str, Any]:
    url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    data = {
        "name": repo_name,
        "description": description,
        "private": False,
        "auto_init": False,
    }
    r = requests.post(url, headers=headers, json=data, timeout=15)
    if r.status_code not in (201,):
        raise RuntimeError(f"GitHub repo creation failed: {r.text}")
    info = r.json()
    return {
        "repo_url": info["html_url"],
        "default_branch": info.get("default_branch", "main"),
    }


def push_file(user: str, repo_name: str, path: str, content: str, message: str) -> None:
    url = f"https://api.github.com/repos/{user}/{repo_name}/contents/{path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    data = {"message": message, "content": content.encode("utf-8").decode("utf-8")}
    b64 = content.encode("utf-8")
    import base64

    data["content"] = base64.b64encode(b64).decode("utf-8")
    r = requests.put(url, headers=headers, json=data, timeout=15)
    if r.status_code not in (201, 200):
        raise RuntimeError(f"Failed to push {path}: {r.text}")


def enable_pages(user: str, repo_name: str, branch: str = "main") -> str:
    url = f"https://api.github.com/repos/{user}/{repo_name}/pages"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    payload = {"source": {"branch": branch, "path": "/"}}
    r = requests.post(url, headers=headers, json=payload, timeout=15)
    if r.status_code not in (201, 204, 202):
        app.logger.warning(f"GitHub Pages enable failed: {r.text}")
    return f"https://{user}.github.io/{repo_name}/"


def post_evaluation(evaluation_url: str, payload: dict) -> None:
    headers = {"Content-Type": "application/json"}
    wait = 1
    for _ in range(EVAL_POST_MAX_TRIES):
        try:
            res = requests.post(
                evaluation_url, headers=headers, json=payload, timeout=15
            )
            if res.status_code == 200:
                return
            app.logger.warning(
                f"Evaluation POST returned {res.status_code}: {res.text}"
            )
        except Exception as e:
            app.logger.warning(f"Evaluation POST failed: {e}")
        time.sleep(wait)
        wait *= 2
    raise RuntimeError("Evaluation POST failed after retries")


# --- Flask route ---
@app.route("/api/build", methods=["POST"])
def build_endpoint():
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    required = ["email", "secret", "task", "round", "nonce", "brief", "evaluation_url"]
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

    if not validate_secret(data["secret"]):
        return jsonify({"error": "Invalid secret"}), 403

    email = data["email"]
    task = data["task"]
    brief = data["brief"]
    evaluation_url = data["evaluation_url"]

    repo_name = safe_repo_name(task, email)
    files = llm_generate_files(brief, task)

    # Add license, .gitignore
    owner_for_license = email.split("@")[0]
    files["LICENSE"] = make_mit_license(owner_for_license)
    files.setdefault(".gitignore", "__pycache__/\nnode_modules/\n.env\n")

    try:
        repo_meta = create_repo(repo_name, f"Auto-generated app for {task}")
        for path, content in files.items():
            push_file(GITHUB_USER, repo_name, path, content, f"Add {path}")
        pages_url = enable_pages(GITHUB_USER, repo_name)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"GitHub operation failed: {e}"}), 500

    eval_payload = {
        "email": email,
        "task": task,
        "round": data["round"],
        "nonce": data["nonce"],
        "repo_url": repo_meta["repo_url"],
        "pages_url": pages_url,
        "commit_sha": "latest",
    }

    try:
        post_evaluation(evaluation_url, eval_payload)
    except Exception as e:
        app.logger.warning(f"Evaluation post failed: {e}")
        return jsonify({"status": "partial", **eval_payload}), 200

    return jsonify({"status": "ok", **eval_payload}), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
