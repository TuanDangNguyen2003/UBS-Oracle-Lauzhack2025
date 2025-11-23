import { NextResponse } from "next/server";
import { spawn } from "child_process";

export async function POST(req: Request) {
  const body = await req.json();
  const prompt = body.prompt ?? "";
  const history = body.history ?? [];

  const payload = JSON.stringify({ prompt, history });

  return new Promise((resolve) => {
    const py = spawn("python3", ["./scripts/ai_entry.py", payload]);

    let stdout = "";
    let stderr = "";

    py.stdout.on("data", (d) => {
      stdout += d.toString();
    });

    py.stderr.on("data", (d) => {
      stderr += d.toString();
    });

    py.on("close", (code) => {
      if (code !== 0 || !stdout) {
        return resolve(
          NextResponse.json(
            {
              error: stderr || "Python process failed",
              code,
            },
            { status: 500 }
          )
        );
      }

      try {
        const parsed = JSON.parse(stdout);
        return resolve(NextResponse.json(parsed));
      } catch {
        return resolve(
          NextResponse.json(
            {
              error: "Could not parse JSON from Python",
              raw: stdout,
            },
            { status: 500 }
          )
        );
      }
    });
  });
}
