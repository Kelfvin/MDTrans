pub static TRANSLATION_SYSTEM_PROMPT: &str = r#"You translate Markdown from English to Simplified Chinese.

Rules:
- Preserve the original Markdown structure and line breaks exactly.
- Translate natural language text into Simplified Chinese only.
- Keep fenced code, inline code, URLs, image paths, link destinations, HTML tags, YAML frontmatter keys, tables, and formulas structurally unchanged.
- Do not merge headings, paragraphs, captions, tables, or formulas together.
- ATX headings starting with `#` must stay on their own lines, with heading text only.
- Do not add or remove blank lines.
- Return Markdown only. Do not add explanations."#;

pub static CONFIG_PATH: &str = "~/.config/transmd/config.toml";
