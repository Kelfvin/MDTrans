from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path


PDF_PATH = Path("tmp/doc.pdf")
OUTPUT_DIR = Path("outputs_mineru")
BACKEND = "hybrid-auto-engine"


def resolve_mineru_cli() -> str:
    """
    检查 mineru 是否安装，如果已经安装就返回路径
    """
    venv_cli = Path(".venv/bin/mineru")
    if venv_cli.exists():
        return str(venv_cli)

    mineru_cli = shutil.which("mineru")
    if mineru_cli is None:
        raise FileNotFoundError("MinerU CLI not found. Expected `.venv/bin/mineru` or `mineru` on PATH.")
    return mineru_cli


def ensure_inputs() -> None:
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"Input PDF not found: {PDF_PATH}")


async def stream_lines(stream: asyncio.StreamReader | None, prefix: str) -> list[str]:
    if stream is None:
        return []

    lines: list[str] = []
    while True:
        line = await stream.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace").rstrip()
        lines.append(text)
        print(f"[{prefix}] {text}")
    return lines


async def run_mineru(pdf_path: Path, output_dir: Path) -> None:
    cli = resolve_mineru_cli()
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        cli,
        "-p",
        str(pdf_path),
        "-o",
        str(output_dir),
        "-b",
        BACKEND,
    ]

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    print(f"Starting MinerU: {' '.join(cmd)}")
    sys.stdout.flush()

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    stdout_task = asyncio.create_task(stream_lines(process.stdout, "stdout"))
    stderr_task = asyncio.create_task(stream_lines(process.stderr, "stderr"))
    stdout_lines, stderr_lines = await asyncio.gather(stdout_task, stderr_task)
    returncode = await process.wait()
    stderr_text = "\n".join(line for line in stderr_lines if line).strip()

    if returncode != 0:
        error_message = [
            f"MinerU exited with code {returncode}.",
            f"Command: {' '.join(cmd)}",
        ]
        if stderr_text:
            error_message.append(f"stderr:\n{stderr_text}")
        raise RuntimeError("\n".join(error_message))


async def main() -> None:
    ensure_inputs()
    await run_mineru(PDF_PATH, OUTPUT_DIR)
    print(f"MinerU output directory: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    asyncio.run(main())
