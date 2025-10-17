import { Octokit } from "@octokit/rest";

const octokit = new Octokit({
  auth: process.env.GITHUB_TOKEN,
});

const username = process.env.GITHUB_USERNAME;

export async function createRepo(name, description) {
  try {
    const { data } = await octokit.repos.createForAuthenticatedUser({
      name,
      description,
      private: false,
      auto_init: false,
    });

    console.log(`Created repo: ${data.html_url}`);
    return data.html_url;
  } catch (error) {
    if (error.status === 422) {
      // Repo already exists, return URL
      return `https://github.com/${username}/${name}`;
    }
    throw error;
  }
}

export async function pushCode(repoName, files) {
  try {
    // Get default branch
    const { data: repo } = await octokit.repos.get({
      owner: username,
      repo: repoName,
    });

    let sha;
    let branch = repo.default_branch || "main";

    try {
      // Try to get existing branch
      const { data: ref } = await octokit.git.getRef({
        owner: username,
        repo: repoName,
        ref: `heads/${branch}`,
      });
      sha = ref.object.sha;
    } catch (error) {
      // Branch doesn't exist, create initial commit
      const { data: blob } = await octokit.git.createBlob({
        owner: username,
        repo: repoName,
        content: Buffer.from("# Initial commit").toString("base64"),
        encoding: "base64",
      });

      const { data: tree } = await octokit.git.createTree({
        owner: username,
        repo: repoName,
        tree: [
          {
            path: "README.md",
            mode: "100644",
            type: "blob",
            sha: blob.sha,
          },
        ],
      });

      const { data: commit } = await octokit.git.createCommit({
        owner: username,
        repo: repoName,
        message: "Initial commit",
        tree: tree.sha,
      });

      await octokit.git.createRef({
        owner: username,
        repo: repoName,
        ref: `refs/heads/${branch}`,
        sha: commit.sha,
      });

      sha = commit.sha;
    }

    // Create blobs for all files
    const blobs = await Promise.all(
      files.map(async (file) => {
        const { data } = await octokit.git.createBlob({
          owner: username,
          repo: repoName,
          content: Buffer.from(file.content).toString("base64"),
          encoding: "base64",
        });
        return { path: file.path, sha: data.sha };
      }),
    );

    // Create tree
    const { data: tree } = await octokit.git.createTree({
      owner: username,
      repo: repoName,
      base_tree: sha,
      tree: blobs.map((blob) => ({
        path: blob.path,
        mode: "100644",
        type: "blob",
        sha: blob.sha,
      })),
    });

    // Create commit
    const { data: commit } = await octokit.git.createCommit({
      owner: username,
      repo: repoName,
      message: "Deploy application",
      tree: tree.sha,
      parents: [sha],
    });

    // Update reference
    await octokit.git.updateRef({
      owner: username,
      repo: repoName,
      ref: `heads/${branch}`,
      sha: commit.sha,
    });

    console.log(`Pushed code to ${repoName}: ${commit.sha}`);
    return commit.sha;
  } catch (error) {
    console.error("Error pushing code:", error);
    throw error;
  }
}

export async function enablePages(repoName) {
  try {
    await octokit.repos.createPagesSite({
      owner: username,
      repo: repoName,
      source: {
        branch: "main",
        path: "/",
      },
    });

    const pagesUrl = `https://${username}.github.io/${repoName}/`;
    console.log(`Enabled Pages: ${pagesUrl}`);
    return pagesUrl;
  } catch (error) {
    if (error.status === 409) {
      // Pages already enabled
      return `https://${username}.github.io/${repoName}/`;
    }
    throw error;
  }
}
