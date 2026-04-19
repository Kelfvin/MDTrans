use std::env;
use std::path::PathBuf;

use anyhow::{Result, bail};
use serde::{Deserialize, Serialize};

pub const DEFAULT_CONFIG_TEMPLATE: &str = r#"[llm]
base_url = "https://api.deepseek.com/v1"
model = "deepseek-chat"
context_window = 64000
max_output_tokens = 8000
max_chunk_tokens = 5000
"#;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Config {
    pub llm: LlmConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LlmConfig {
    pub base_url: String,
    pub model: String,
    pub context_window: usize,
    pub max_output_tokens: usize,
    pub max_chunk_tokens: usize,
}

pub fn default_config_path() -> PathBuf {
    dirs::home_dir()
        .expect("failed to resolve home directory")
        .join(".config")
        .join("transmd")
        .join("config.toml")
}

pub fn require_openai_api_key() -> Result<String> {
    match env::var("OPENAI_API_KEY") {
        Ok(value) if !value.trim().is_empty() => Ok(value),
        _ => bail!("OPENAI_API_KEY is required but not set."),
    }
}

pub async fn load_config(config_path: Option<&PathBuf>) -> Result<Config> {
    let config_path = config_path.unwrap_or(&default_config_path()).to_owned();

    if !config_path.exists() {
        if let Some(parent) = config_path.parent() {
            tokio::fs::create_dir_all(parent).await?;
        }
        tokio::fs::write(&config_path, DEFAULT_CONFIG_TEMPLATE).await?;
        bail!(
            "Created config template at {}. Please edit it and run again.",
            config_path.display()
        );
    }

    let text = tokio::fs::read_to_string(&config_path).await?;
    let config: Config = toml::from_str(&text)?;

    Ok(config)
}

#[cfg(test)]
mod tests {
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::*;

    #[tokio::test]
    async fn loads_llm_config() {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = env::temp_dir().join(format!("transmd-config-{unique}.toml"));

        tokio::fs::write(
            &path,
            r#"[llm]
base_url = "https://api.example.com/v1"
model = "demo"
context_window = 32000
max_output_tokens = 4000
max_chunk_tokens = 2000
"#,
        )
        .await
        .unwrap();

        let config = load_config(Some(&path)).await.unwrap();
        assert_eq!(config.llm.base_url, "https://api.example.com/v1");
        assert_eq!(config.llm.model, "demo");
        assert_eq!(config.llm.context_window, 32000);

        let _ = tokio::fs::remove_file(&path).await;
    }
}
