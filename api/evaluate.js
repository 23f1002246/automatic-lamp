// This is the evaluation callback endpoint that receives repo details

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  try {
    const { email, task, round, nonce, repo_url, commit_sha, pages_url } =
      req.body;

    // Validate required fields
    if (
      !email ||
      !task ||
      !round ||
      !nonce ||
      !repo_url ||
      !commit_sha ||
      !pages_url
    ) {
      return res.status(400).json({ error: "Missing required fields" });
    }

    // Log the submission (in production, store in database)
    console.log("Received evaluation submission:", {
      email,
      task,
      round,
      nonce,
      repo_url,
      commit_sha,
      pages_url,
      timestamp: new Date().toISOString(),
    });

    // Return success
    return res.status(200).json({
      success: true,
      message: "Submission received",
    });
  } catch (error) {
    console.error("Evaluate endpoint error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
}
