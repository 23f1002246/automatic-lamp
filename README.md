# LLM Code Deployment — Student API

This project allows students to **automatically build, deploy, and revise web apps** in response to JSON task requests. It uses **GitHub Pages** for hosting and optionally **OpenAI** for code generation.

This README assumes you are deploying on **Vercel**.

---

## 📁 Project Structure

```
api/
 ├─ build.py      # Handles initial app build and GitHub Pages deployment
 ├─ revise.py     # Handles round 2 revisions and re-deployments
 └─ utils/
     ├─ generator.py     # Generates index.html and README.md
     └─ github_tools.py  # Helper functions for GitHub operations
```

---

## ⚙️ Environment Variables

Set these in **Vercel Dashboard → Project → Environment Variables**:

| Variable         | Description                                        | Required |
| ---------------- | -------------------------------------------------- | -------- |
| `GITHUB_TOKEN`   | GitHub personal access token with `repo` scope     | ✅       |
| `VALID_SECRET`   | Secret used to validate incoming task JSON         | ✅       |
| `OPENAI_API_KEY` | Optional — enables LLM-assisted code generation    | ❌       |
| `GITHUB_ACTOR`   | Optional — GitHub username to override token owner | ❌       |

---

## 🚀 Deployment on Vercel

1. Create a new project in [Vercel](https://vercel.com/).
2. Connect your Git repository (or import manually).
3. Place all `api/` files in your project root.
4. Set the environment variables listed above.
5. Deploy the project.

**Endpoints exposed:**

| Endpoint      | Method | Description                                                                                  |
| ------------- | ------ | -------------------------------------------------------------------------------------------- |
| `/api/build`  | POST   | Accepts a JSON task request, builds app, deploys to GitHub Pages, posts back metadata.       |
| `/api/revise` | POST   | Accepts a second JSON task request, updates the app, pushes to GitHub Pages, posts metadata. |

---

## 📝 Example Task JSON (Round 1)

```json
{
  "email": "student@example.com",
  "secret": "YOUR_SECRET",
  "task": "captcha-solver-001",
  "round": 1,
  "nonce": "abc123",
  "brief": "Create a captcha solver that handles ?url=https://.../image.png",
  "checks": [
    "Repo has MIT license",
    "README.md is professional",
    "Page displays captcha URL passed at ?url=...",
    "Page displays solved captcha text within 15 seconds"
  ],
  "evaluation_url": "https://example.com/notify",
  "attachments": [
    { "name": "sample.png", "url": "data:image/png;base64,iVBORw0..." }
  ]
}
```

---

## 🔧 Testing the API

### Build (Round 1)

```bash
curl -X POST https://your-vercel-app.vercel.app/api/build \
  -H "Content-Type: application/json" \
  -d @task1.json
```

**Response:**

```json
{
  "status": "ok",
  "repo_url": "https://github.com/username/captcha-solver-001-xxxxxx",
  "pages_url": "https://username.github.io/captcha-solver-001-xxxxxx/",
  "commit_sha": "abcdef123456"
}
```

---

### Revise (Round 2)

```bash
curl -X POST https://your-vercel-app.vercel.app/api/revise \
  -H "Content-Type: application/json" \
  -d @task2.json
```

**Response:**

```json
{
  "status": "success",
  "message": "Revision round 2 complete",
  "repo_url": "https://github.com/username/captcha-solver-001-xxxxxx",
  "evaluation_payload": {
    "email": "student@example.com",
    "task": "captcha-solver-001",
    "round": 2,
    "nonce": "def456",
    "repo_url": "https://github.com/username/captcha-solver-001-xxxxxx",
    "commit_sha": "latest"
  },
  "timestamp": "2025-10-17T17:22:51Z"
}
```

---

## ⚡ Notes & Best Practices

- **Secrets**: Always keep `VALID_SECRET` secure; it prevents unauthorized requests.
- **GitHub Token**: Ensure `repo` scope is enabled; Pages cannot be deployed without it.
- **OpenAI**: Optional — generates better HTML and README.md. Without it, default static HTML is used.
- **GitHub Pages**: Enabled automatically; Pages URL returned in API response.
- **Attachments**: Base64-encoded files can be used in the build.

---

## ✅ Summary

This system allows students to:

1. **Receive tasks** via JSON.
2. **Build and deploy** an app to GitHub Pages automatically.
3. **Update/revise** apps in round 2 without manual intervention.
4. **Automatically notify instructors** via `evaluation_url`.

It is **fully deployable on Vercel**, requires minimal setup, and works with or without LLM assistance.
