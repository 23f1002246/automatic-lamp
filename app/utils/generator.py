import os
import time
import json

DEFAULT_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{task} - Demo</title>
  <style>
    body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,"Helvetica Neue",Arial;padding:2rem;}}
    #image {{max-width:400px; display:block; margin: 1rem 0;}}
    #solved {{font-weight:700; margin-top:1rem; color:green;}}
  </style>
</head>
<body>
  <h1>{task}</h1>
  <p><strong>Brief:</strong> {brief}</p>

  <div>
    <label>Captcha URL (from ?url=):</label>
    <div id="url-display">none</div>
    <img id="image" alt="captcha" />
    <div id="solved">Solving not supported in default build — replace with LLM-assisted solver.</div>
  </div>

  <script>
    (function () {{
      const params = new URLSearchParams(window.location.search);
      const url = params.get("url");
      const imageEl = document.getElementById("image");
      const urlDisplay = document.getElementById("url-display");
      if (url) {{
        urlDisplay.textContent = url;
        imageEl.src = url;
        imageEl.style.display = "block";
      }} else {{
        urlDisplay.textContent = "No ?url provided; using attached sample if present.";
      }}
      setTimeout(() => {{
        document.getElementById("solved").textContent = "SAMPLE-SOLVED-TEXT";
      }}, 1200);
    }})();
  </script>
</body>
</html>"""


def llm_generate_files(brief: str, task: str):
    """
    Returns a dictionary with minimal app files: index.html and README.md.
    Can be extended for OpenAI LLM generation.
    """
    index_html = DEFAULT_HTML_TEMPLATE.format(task=task, brief=brief)
    readme_md = f"# {task}\n\nAuto-generated demo page.\n\nBrief: {brief}\n"
    return {"index.html": index_html, "README.md": readme_md}
