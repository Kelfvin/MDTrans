use anyhow::{Result, anyhow};
use clap::Parser;
use transmd::{
    config::{load_config, require_openai_api_key},
    discovery::{find_markdown, resolve_output_dir, resolve_pdf_path},
    parse::run_mineru,
    translate::LLMTranslator,
};

#[derive(Parser)]
#[command(name = "transmd")]
#[command(version)]
#[command(
    about = "Convert a PDF with MinerU and translate the generated Markdown into Simplified Chinese."
)]
struct Cli {
    pdf_path: String,
    output_dir: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();
    let pdf_path = resolve_pdf_path(&cli.pdf_path)?;
    let output_dir = resolve_output_dir(&cli.output_dir)?;

    let config = load_config(None).await?;
    let api_key = require_openai_api_key()?;
    let client = LLMTranslator::new(
        config.llm.base_url.clone(),
        api_key,
        config.llm.model.clone(),
        config.llm.max_output_tokens,
        config.llm.max_chunk_tokens,
    );
    println!("Parsing PDF with MinerU...");

    run_mineru(&pdf_path, &output_dir).await?;

    println!("Translating Markdown files...");

    let pdf_stem = pdf_path
        .file_stem()
        .and_then(|value| value.to_str())
        .ok_or_else(|| anyhow!("Invalid PDF file name: {}", pdf_path.display()))?;

    let files = find_markdown(output_dir.join(pdf_stem))?;

    for file in files {
        let text = std::fs::read_to_string(&file)?;
        let trans_text = client.translate_markdown(&text).await?;

        let stem = file
            .file_stem()
            .and_then(|value| value.to_str())
            .ok_or_else(|| anyhow!("Invalid markdown file name: {}", file.display()))?;
        let out_file = file.with_file_name(format!("{stem}.zh.md"));

        tokio::fs::write(&out_file, trans_text).await?;
        println!("{}", out_file.display());
    }

    Ok(())
}
