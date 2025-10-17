import os
import base64
import json
import requests
import time


GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_API = "https://api.github.com"


def github_headers():
    """Returns standard GitHub API headers."""
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def create_repo(repo_name: str, description: str = "", private: bool = False):
    """Creates a new GitHub repo under the authenticated user."""
    url = f"{GITHUB_API}/user/repos"
    payload = {
        "name": repo_name,
        "description": description,
        "private": private,
        "auto_init": False,
    }

    r = requests.post(url, headers=github_headers(), json=payload)
    if r.status_code not in (200, 201):
        raise Exception(f"GitHub repo creation failed: {r.text}")

    data = r.json()
    return {
        "repo_url": data["html_url"],
        "clone_url": data["clone_url"],
        "default_branch": data.get("default_branch", "main"),
    }


def push_file(user: str, repo: str, path: str, content: str, message: str):
    """Push a single file to a GitHub repo (base64 encoded)."""
    url = f"{GITHUB_API}/repos/{user}/{repo}/contents/{path}"

    payload = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "branch": "main",
    }

    r = requests.put(url, headers=github_headers(), json=payload)
    if r.status_code not in (200, 201):
        raise Exception(f"Push failed for {path}: {r.text}")

    return r.json()["commit"]["sha"]


def enable_github_pages(user: str, repo: str):
    """Enables GitHub Pages on the repo's main branch."""
    url = f"{GITHUB_API}/repos/{user}/{repo}/pages"
    payload = {
        "source": {"branch": "main", "path": "/"},
        "build_type": "legacy",
    }

    r = requests.post(url, headers=github_headers(), json=payload)
    if r.status_code not in (201, 202):
        # In some cases GitHub auto-enables Pages on push, so retry GET
        check = requests.get(url, headers=github_headers())
        if check.status_code != 200:
            raise Exception(f"Failed to enable GitHub Pages: {r.text}")

    # Wait for Pages URL to be available
    for _ in range(10):
        time.sleep(3)
        resp = requests.get(url, headers=github_headers())
        if resp.status_code == 200:
            pages_data = resp.json()
            return pages_data.get("html_url")

    raise Exception("Timed out waiting for GitHub Pages URL.")


def add_mit_license():
    """Returns the MIT License text."""
    year = time.strftime("%Y")
    holder = os.environ.get("GITHUB_USER", "Student Developer")
    return f"""MIT License

Copyright (c) {year} {holder}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
