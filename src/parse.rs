use std::path::{Path, PathBuf};

use anyhow::{Result, bail};

pub const MINERU_BACKEND: &str = "hybrid-auto-engine";

pub fn resolve_mineru_cli() -> Result<PathBuf> {
    let venv_cli = Path::new(".venv").join("bin").join("mineru");
    if venv_cli.exists() {
        return Ok(venv_cli);
    }

    match which("mineru") {
        Some(path) => Ok(path),
        None => bail!("MinerU CLI not found. Expected `.venv/bin/mineru` or `mineru` on PATH."),
    }
}

pub async fn run_mineru(pdf_path: &Path, output_dir: &Path) -> Result<()> {
    let cli = resolve_mineru_cli()?;
    tokio::fs::create_dir_all(output_dir).await?;

    let output = tokio::process::Command::new(&cli)
        .arg("-p")
        .arg(pdf_path)
        .arg("-o")
        .arg(output_dir)
        .arg("-b")
        .arg(MINERU_BACKEND)
        .output()
        .await?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let stdout = String::from_utf8_lossy(&output.stdout);
        bail!(
            "MinerU exited with code {:?}.\nstdout:\n{}\nstderr:\n{}",
            output.status.code(),
            stdout.trim(),
            stderr.trim()
        );
    }

    Ok(())
}

fn which(binary: &str) -> Option<PathBuf> {
    let path = std::env::var_os("PATH")?;
    for entry in std::env::split_paths(&path) {
        let candidate = entry.join(binary);
        if candidate.exists() {
            return Some(candidate);
        }
    }
    None
}
