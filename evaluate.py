"""
evaluate.py

Automated evaluation script for submitted GitHub repos.

Features:
- Loads submissions from api/evaluation.py in-memory or optionally a JSON/DB export.
- Checks:
  * LICENSE file exists and contains 'MIT'
  * README.md exists
  * GitHub Pages URL is live (HTTP 200)
- Optional: send code/README to LLM for quality analysis (requires OPENAI_API_KEY)
- Logs results to a local JSON file for record-keeping.
"""

import os
import json
import requests
from github import Github
from datetime import datetime

# Load environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EVALUATION_STORE_FILE = "evaluation_results.json"

# Import submissions from evaluation endpoint (in production, replace with DB query)
try:
    from api.evaluation import REPO_SUBMISSIONS
except ImportError:
    REPO_SUBMISSIONS = {}  # fallback

# GitHub API client
g = Github(GITHUB_TOKEN)


def check_license(repo):
    try:
        content = repo.get_contents("LICENSE").decoded_content.decode("utf-8")
        if "MIT" in content:
            return True, "MIT license found"
        return False, "LICENSE exists but does not mention MIT"
    except Exception:
        return False, "LICENSE not found"


def check_readme(repo):
    try:
        content = repo.get_contents("README.md").decoded_content.decode("utf-8")
        if len(content.strip()) > 20:
            return True, "README.md exists and non-trivial"
        return False, "README.md too short"
    except Exception:
        return False, "README.md not found"


def check_pages_url(pages_url):
    try:
        resp = requests.get(pages_url, timeout=15)
        if resp.status_code == 200:
            return True, "Pages URL reachable"
        return False, f"Pages returned status {resp.status_code}"
    except Exception as e:
        return False, f"Pages URL request failed: {e}"


def evaluate_submission(submission):
    email = submission["email"]
    task = submission["task"]
    repo_url = submission["repo_url"]
    commit_sha = submission["commit_sha"]
    pages_url = submission.get("pages_url")

    # Extract repo path
    try:
        path = repo_url.replace("https://github.com/", "")
        repo = g.get_repo(path)
    except Exception as e:
        return {"email": email, "task": task, "error": f"Repo access failed: {e}"}

    license_ok, license_msg = check_license(repo)
    readme_ok, readme_msg = check_readme(repo)
    pages_ok, pages_msg = (
        (False, "No pages_url") if not pages_url else check_pages_url(pages_url)
    )

    result = {
        "email": email,
        "task": task,
        "commit_sha": commit_sha,
        "license_ok": license_ok,
        "license_msg": license_msg,
        "readme_ok": readme_ok,
        "readme_msg": readme_msg,
        "pages_ok": pages_ok,
        "pages_msg": pages_msg,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # Optional: LLM evaluation for README or code quality
    if OPENAI_API_KEY and readme_ok:
        try:
            # simple example: send README to GPT for quality check
            import requests as rq

            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
            prompt = f"Evaluate the quality of this README.md in a 0-10 scale and give brief feedback:\n\n{repo.get_contents('README.md').decoded_content.decode('utf-8')}"
            body = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
            }
            resp = rq.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=body,
                timeout=20,
            )
            resp.raise_for_status()
            j = resp.json()
            feedback = j["choices"][0]["message"]["content"].strip()
            result["llm_readme_feedback"] = feedback
        except Exception as e:
            result["llm_readme_feedback"] = f"LLM evaluation failed: {e}"

    return result


def run_evaluation():
    results = []
    for key, submission in REPO_SUBMISSIONS.items():
        print(
            f"Evaluating {submission['email']} | {submission['task']} | round {submission['round']}"
        )
        try:
            res = evaluate_submission(submission)
            results.append(res)
        except Exception as e:
            print(f"[ERROR] Evaluation failed for {key}: {e}")

    # Save results
    with open(EVALUATION_STORE_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Evaluation completed. Results saved to {EVALUATION_STORE_FILE}")


if __name__ == "__main__":
    run_evaluation()
