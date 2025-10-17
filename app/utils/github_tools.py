import time
from github import Github, GithubException
import requests

MIT_LICENSE_TEXT = """MIT License

Copyright (c) {year} {owner}

Permission is hereby granted, free of charge, to any person obtaining a copy...
(standard MIT body omitted for brevity)
"""


def make_mit_license(owner: str):
    """Returns MIT license text with year and owner."""
    year = time.strftime("%Y")
    owner_txt = owner or "Unknown"
    return MIT_LICENSE_TEXT.format(year=year, owner=owner_txt)


def create_github_repo_and_push(
    repo_name: str, files: dict, github_token: str, owner_override=None
):
    """
    Create a public GitHub repo and push given files.
    Returns repo_url, commit_sha, owner.
    """
    g = Github(github_token)
    user = g.get_user()
    owner = owner_override or user.login

    try:
        repo = user.create_repo(name=repo_name, private=False, auto_init=False)
    except GithubException as e:
        raise RuntimeError(
            f"Failed to create repo: {e.data if hasattr(e, 'data') else str(e)}"
        )

    last_sha = None
    for path, content in files.items():
        try:
            repo.create_file(path, f"Add {path}", content, branch="main")
            last_sha = repo.get_commits()[0].sha
        except GithubException as ge:
            raise RuntimeError(
                f"Failed to create file {path}: {ge.data if hasattr(ge, 'data') else str(ge)}"
            )

    return {"repo_url": repo.html_url, "commit_sha": last_sha, "owner": owner}


def enable_github_pages(
    owner: str, repo_name: str, github_token: str, branch="main", path="/"
):
    """Enable GitHub Pages for a repo using REST API."""
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/pages"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json",
    }
    payload = {"source": {"branch": branch, "path": path}}
    resp = requests.put(api_url, headers=headers, json=payload, timeout=20)
    if resp.status_code not in (201, 204):
        raise RuntimeError(
            f"Failed to enable Pages: status={resp.status_code} body={resp.text}"
        )
