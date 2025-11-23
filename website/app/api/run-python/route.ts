import { NextResponse } from 'next/server';
import { spawn } from 'child_process';

export async function GET() {
  return new Promise((resolve) => {
    const py = spawn("python3", ["./scripts/demo.py"]);

    let output = "";
    let error = "";

    py.stdout.on("data", (data) => {
      output += data.toString();
    });

    py.stderr.on("data", (data) => {
      error += data.toString();
    });

    py.on("close", (code) => {
      if (code !== 0) {
        resolve(
          NextResponse.json({ error: error || "Python error", code }, { status: 500 })
        );
      } else {
        resolve(NextResponse.json({ output }));
      }
    });
  });
}
