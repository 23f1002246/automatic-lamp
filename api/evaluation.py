"""
api/evaluation.py

Vercel-compatible Flask serverless function exposing POST /api/evaluation.

Purpose:
- Accepts JSON payloads from /api/build or /api/revise.
- Validates secret.
- Stores repository metadata (email, task, round, nonce, repo_url, commit_sha, pages_url).
- Returns HTTP 200 for successful inserts, HTTP 400 for errors.
- Optional: In production, hook this into a DB or Google Sheets for persistence.
"""

import os
import json
import traceback
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

VALID_SECRET = os.getenv("VALID_SECRET")

# Simple in-memory storage for demonstration (replace with DB in production)
REPO_SUBMISSIONS = {}


def validate_secret(provided: str) -> bool:
    if not VALID_SECRET:
        return False
    valid = [s.strip() for s in VALID_SECRET.split(",") if s.strip()]
    return provided in valid


@app.route("/api/evaluation", methods=["POST"])
def receive_evaluation():
    try:
        payload = request.get_json(force=True)

        required_fields = [
            "email",
            "task",
            "round",
            "nonce",
            "repo_url",
            "commit_sha",
            "pages_url",
            "secret",
        ]
        missing = [f for f in required_fields if f not in payload]
        if missing:
            return jsonify({"error": f"Missing fields: {missing}"}), 400

        if not validate_secret(payload["secret"]):
            return jsonify({"error": "Invalid secret"}), 403

        key = f"{payload['email']}|{payload['task']}|{payload['round']}|{payload['nonce']}"
        REPO_SUBMISSIONS[key] = {
            "email": payload["email"],
            "task": payload["task"],
            "round": payload["round"],
            "nonce": payload["nonce"],
            "repo_url": payload["repo_url"],
            "commit_sha": payload["commit_sha"],
            "pages_url": payload["pages_url"],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        return jsonify({"status": "ok", "stored_key": key}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/evaluation/list", methods=["GET"])
def list_submissions():
    """Optional helper: list all stored submissions."""
    return jsonify(REPO_SUBMISSIONS), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
