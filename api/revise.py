import os
import json
import traceback
import requests
from datetime import datetime
from flask import Flask, request, jsonify

from api.utils.generator import generate_app_code
from api.utils.github_tools import (
    push_file,
    get_repo_tree,
    create_commit,
)

app = Flask(__name__)

GITHUB_USER = os.environ.get("GITHUB_USER")
VALID_SECRET = os.environ.get("VALID_SECRET")


@app.route("/api/revise", methods=["POST"])
def revise_app():
    try:
        data = request.get_json(force=True)

        # --- 1️⃣ Secret validation ---
        if not data or data.get("secret") != VALID_SECRET:
            return jsonify({"error": "Invalid secret"}), 403

        email = data.get("email")
        task = data.get("task")
        brief = data.get("brief")
        evaluation_url = data.get("evaluation_url")
        nonce = data.get("nonce")
        round_num = data.get("round", 2)

        if not all([email, task, brief, evaluation_url, nonce]):
            return jsonify({"error": "Missing required fields"}), 400

        repo_name = f"{email.replace('@', '_').replace('.', '-')}_{task}"

        # --- 2️⃣ Regenerate or refine app code ---
        new_app_data = generate_app_code(brief)
        new_index_html = new_app_data.get("index.html", "")
        new_readme = new_app_data.get("README.md", "")

        # --- 3️⃣ Push revision updates ---
        commit_message = f"Round {round_num} revision for {task}"
        push_file(GITHUB_USER, repo_name, "index.html", new_index_html, commit_message)
        push_file(GITHUB_USER, repo_name, "README.md", new_readme, commit_message)

        # --- 4️⃣ Trigger evaluation for revised version ---
        payload = {
            "email": email,
            "task": task,
            "round": round_num,
            "nonce": nonce,
            "repo_url": f"https://github.com/{GITHUB_USER}/{repo_name}",
            "commit_sha": "latest",
        }

        try:
            res = requests.post(
                evaluation_url,
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            if res.status_code != 200:
                print(f"[WARN] Evaluation URL returned {res.status_code}: {res.text}")
        except Exception as e:
            print(f"[WARN] Failed to reach evaluation_url: {e}")

        return (
            jsonify(
                {
                    "status": "success",
                    "message": f"Revision round {round_num} complete",
                    "repo_url": f"https://github.com/{GITHUB_USER}/{repo_name}",
                    "evaluation_payload": payload,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
            ),
            200,
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
