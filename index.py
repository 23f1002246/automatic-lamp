import os
import json
import hashlib
import uuid
import time
from flask import Flask, request, jsonify

from utils.generator import llm_generate_files
from utils.github_tools import (
    create_github_repo_and_push,
    enable_github_pages,
    make_mit_license,
)

app = Flask(__name__)

# ---------------- Configuration ----------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
VALID_SECRET = os.getenv("VALID_SECRET", "")
GITHUB_ACTOR = os.getenv("GITHUB_ACTOR")  # Optional
EVAL_POST_MAX_TRIES = 6


# ---------------- Helper Functions ----------------
def validate_secret(provided):
    """Check if provided secret is valid."""
    valid = [s.strip() for s in VALID_SECRET.split(",") if s.strip()]
    return provided in valid


def safe_repo_name(task, email):
    """Generate a unique repo name."""
    email_hash = hashlib.sha1(email.encode("utf-8")).hexdigest()[:8]
    uid = uuid.uuid4().hex[:6]
    base = task.replace(" ", "-").replace("/", "-").lower()
    return f"{base}-{email_hash}-{uid}"


def post_evaluation_submission(evaluation_url, payload):
    """POSTs JSON to evaluation_url with exponential backoff."""
    import requests

    headers = {"Content-Type": "application/json"}
    wait = 1.0
    tries = 0
    while tries < EVAL_POST_MAX_TRIES:
        try:
            resp = requests.post(
                evaluation_url, headers=headers, json=payload, timeout=15
            )
            if resp.status_code == 200:
                return
        except Exception:
            pass
        tries += 1
        time.sleep(wait)
        wait *= 2
    raise RuntimeError("Failed to POST evaluation submission")


# ---------------- Build Endpoint ----------------
@app.route("/build", methods=["POST"])
def build_endpoint():
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    # Required fields
    for key in ["email", "secret", "task", "round", "nonce", "brief", "evaluation_url"]:
        if key not in payload:
            return jsonify({"error": f"Missing {key}"}), 400

    if not validate_secret(payload["secret"]):
        return jsonify({"error": "Invalid secret"}), 403

    email = payload["email"]
    task = payload["task"]
    brief = payload["brief"]
    evaluation_url = payload["evaluation_url"]
    attachments = payload.get("attachments", [])

    # Generate unique repo name
    repo_name = safe_repo_name(task, email)

    # Generate app files (LLM or default)
    files = llm_generate_files(brief, task)
    owner_for_license = email.split("@")[0] if "@" in email else email
    files["LICENSE"] = make_mit_license(owner_for_license)
    files.setdefault(".gitignore", "node_modules/\n__pycache__/\n.env\n")

    # Create GitHub repo and push files
    try:
        gh_result = create_github_repo_and_push(
            repo_name, files, GITHUB_TOKEN, owner_override=GITHUB_ACTOR
        )
        repo_url = gh_result["repo_url"]
        commit_sha = gh_result["commit_sha"]
        owner = gh_result["owner"]

        # Enable GitHub Pages
        enable_github_pages(owner, repo_name, GITHUB_TOKEN)
        pages_url = f"https://{owner}.github.io/{repo_name}/"
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Prepare evaluation callback
    eval_payload = {
        "email": email,
        "task": task,
        "round": payload["round"],
        "nonce": payload["nonce"],
        "repo_url": repo_url,
        "commit_sha": commit_sha,
        "pages_url": pages_url,
    }

    # POST to evaluation_url
    try:
        post_evaluation_submission(evaluation_url, eval_payload)
    except Exception as e:
        return (
            jsonify(
                {
                    "status": "partial",
                    "repo_url": repo_url,
                    "pages_url": pages_url,
                    "error": str(e),
                }
            ),
            200,
        )

    return (
        jsonify(
            {
                "status": "ok",
                "repo_url": repo_url,
                "pages_url": pages_url,
                "commit_sha": commit_sha,
            }
        ),
        200,
    )


# ---------------- Revise Endpoint ----------------
@app.route("/revise", methods=["POST"])
def revise_endpoint():
    """
    Accepts a second POST (round 2) to update the app.
    Logic can be extended: verify secret, update files, push, redeploy Pages.
    """
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    # Required fields
    for key in [
        "email",
        "secret",
        "task",
        "round",
        "nonce",
        "brief",
        "evaluation_url",
        "repo_url",
    ]:
        if key not in payload:
            return jsonify({"error": f"Missing {key}"}), 400

    if not validate_secret(payload["secret"]):
        return jsonify({"error": "Invalid secret"}), 403

    # For simplicity, we just acknowledge revise here
    # You can extend to modify files, push updates, and notify evaluation_url
    return jsonify({"status": "ok", "message": "Revise received"}), 200


# ---------------- Main Entry ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
