import { Octokit } from "@octokit/rest";
import { generateCode } from "./lib/llm.js";
import { createRepo, pushCode, enablePages } from "./lib/github.js";

// In-memory storage for requests (use database in production)
const requests = new Map();

export default async function handler(req, res) {
  // Only accept POST requests
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  try {
    const {
      email,
      secret,
      task,
      round,
      nonce,
      brief,
      checks,
      evaluation_url,
      attachments,
    } = req.body;

    // Validate required fields
    if (
      !email ||
      !secret ||
      !task ||
      !round ||
      !nonce ||
      !brief ||
      !evaluation_url
    ) {
      return res.status(400).json({ error: "Missing required fields" });
    }

    // Verify secret
    if (secret !== process.env.SECRET_KEY) {
      return res.status(401).json({ error: "Invalid secret" });
    }

    // Send immediate 200 response
    res.status(200).json({
      success: true,
      message: "Request received and processing",
      task,
      round,
    });

    // Process asynchronously
    processRequest({
      email,
      secret,
      task,
      round,
      nonce,
      brief,
      checks,
      evaluation_url,
      attachments,
    }).catch((err) => console.error("Processing error:", err));
  } catch (error) {
    console.error("Handler error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
}

async function processRequest(request) {
  const {
    email,
    task,
    round,
    nonce,
    brief,
    checks,
    evaluation_url,
    attachments,
  } = request;

  console.log(`Processing ${task} round ${round}`);

  try {
    // Generate code using LLM
    const code = await generateCode(brief, checks, attachments);

    // Create unique repo name
    const repoName = task;

    // Create GitHub repo
    const repoUrl = await createRepo(repoName, code.readme);

    // Push code to repo
    const commitSha = await pushCode(repoName, code.files);

    // Enable GitHub Pages
    const pagesUrl = await enablePages(repoName);

    // Wait a bit for Pages to deploy
    await new Promise((resolve) => setTimeout(resolve, 5000));

    // Notify evaluation endpoint
    await notifyEvaluation(
      {
        email,
        task,
        round,
        nonce,
        repo_url: repoUrl,
        commit_sha: commitSha,
        pages_url: pagesUrl,
      },
      evaluation_url,
    );

    console.log(`Successfully completed ${task} round ${round}`);
  } catch (error) {
    console.error(`Error processing ${task}:`, error);
    // Retry logic could be added here
  }
}

async function notifyEvaluation(data, url) {
  let retries = 0;
  const maxRetries = 5;

  while (retries < maxRetries) {
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        console.log("Evaluation notification sent successfully");
        return;
      }

      throw new Error(`HTTP ${response.status}`);
    } catch (error) {
      retries++;
      const delay = Math.pow(2, retries) * 1000; // Exponential backoff
      console.log(`Retry ${retries}/${maxRetries} after ${delay}ms`);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw new Error("Failed to notify evaluation endpoint after retries");
}
