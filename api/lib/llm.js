// LLM code generation using Anthropic Claude

export async function generateCode(brief, checks, attachments = []) {
  const prompt = buildPrompt(brief, checks, attachments);

  try {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": process.env.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: "claude-sonnet-4-20250514",
        max_tokens: 4000,
        messages: [
          {
            role: "user",
            content: prompt,
          },
        ],
      }),
    });

    const data = await response.json();
    const generatedCode = data.content[0].text;

    return parseGeneratedCode(generatedCode, brief);
  } catch (error) {
    console.error("LLM generation error:", error);
    throw error;
  }
}

function buildPrompt(brief, checks, attachments) {
  let prompt = `You are an expert web developer. Generate a complete, production-ready single-page application based on this brief:

${brief}

The application must pass these checks:
${checks.map((check, i) => `${i + 1}. ${check}`).join("\n")}

`;

  if (attachments && attachments.length > 0) {
    prompt += `\nAttachments:\n`;
    attachments.forEach((att) => {
      prompt += `- ${att.name}: ${att.url}\n`;
    });
  }

  prompt += `
Requirements:
1. Create a single index.html file with embedded CSS and JavaScript
2. Use CDN links for any external libraries (Bootstrap, marked.js, highlight.js, etc.)
3. Make it visually appealing with modern design
4. Ensure all checks will pass
5. Include proper error handling
6. Add comments explaining key functionality

Also create:
- LICENSE file (MIT License)
- README.md with: project summary, setup instructions, usage guide, code explanation, and license info

Return your response in this format:
=== index.html ===
[your HTML code]

=== LICENSE ===
[MIT License text]

=== README.md ===
[comprehensive README]
`;

  return prompt;
}

function parseGeneratedCode(response, brief) {
  const files = [];

  // Parse index.html
  const htmlMatch = response.match(
    /=== index\.html ===\s*([\s\S]*?)(?===== |$)/,
  );
  if (htmlMatch) {
    files.push({ path: "index.html", content: htmlMatch[1].trim() });
  }

  // Parse LICENSE
  const licenseMatch = response.match(
    /=== LICENSE ===\s*([\s\S]*?)(?===== |$)/,
  );
  if (licenseMatch) {
    files.push({ path: "LICENSE", content: licenseMatch[1].trim() });
  } else {
    // Default MIT License
    files.push({
      path: "LICENSE",
      content: `MIT License

Copyright (c) ${new Date().getFullYear()}

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.`,
    });
  }

  // Parse README.md
  const readmeMatch = response.match(
    /=== README\.md ===\s*([\s\S]*?)(?===== |$)/,
  );
  if (readmeMatch) {
    files.push({ path: "README.md", content: readmeMatch[1].trim() });
  } else {
    files.push({
      path: "README.md",
      content: `# Generated Application\n\n${brief}\n\n## Setup\n\nOpen index.html in a web browser.\n\n## License\n\nMIT`,
    });
  }

  return {
    files,
    readme: brief,
  };
}
