CONFIG_PATH = "config.toml"
BACKEND = "hybrid-auto-engine"
RESERVED_OUTPUT_TOKENS = 4000

TRANSLATION_SYSTEM_PROMPT = """You translate Markdown from English to Simplified Chinese.

Rules:
- Preserve the original Markdown structure and line breaks exactly.
- Translate natural language text into Simplified Chinese only.
- Keep fenced code, inline code, URLs, image paths, link destinations, HTML tags, YAML frontmatter keys, tables, and formulas structurally unchanged.
- Do not merge headings, paragraphs, captions, tables, or formulas together.
- Do not add or remove blank lines.
- Return Markdown only. Do not add explanations."""
