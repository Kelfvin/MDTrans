use async_openai::{
    Client,
    config::OpenAIConfig,
    types::chat::{
        ChatCompletionRequestSystemMessageArgs, ChatCompletionRequestUserMessageArgs,
        CreateChatCompletionRequestArgs,
    },
};

use anyhow::Result;
use pulldown_cmark::{Event, Parser, Tag, TagEnd};
use tiktoken_rs::o200k_base;

use crate::constant;

pub struct LLMTranslator {
    client: Client<OpenAIConfig>,
    model: String,
    max_output_tokens: usize,
    max_chunk_tokens: usize, // 用于限制给 LLM 发送的文本长度大小
}

impl LLMTranslator {
    pub fn new(
        base_url: String,
        api_key: String,
        model: String,
        max_output_tokens: usize,
        max_chunk_tokens: usize,
    ) -> Self {
        let config = OpenAIConfig::new()
            .with_api_base(base_url)
            .with_api_key(api_key);

        Self {
            client: Client::with_config(config),
            model,
            max_output_tokens,
            max_chunk_tokens,
        }
    }

    pub async fn translate_chunked_markdown(&self, chunk: &str) -> Result<String> {
        let prompt = self.build_translation_prompt(chunk);

        let system_msg = ChatCompletionRequestSystemMessageArgs::default()
            .content(constant::TRANSLATION_SYSTEM_PROMPT)
            .build()?
            .into();

        let user_msg = ChatCompletionRequestUserMessageArgs::default()
            .content(prompt)
            .build()?
            .into();

        let request = CreateChatCompletionRequestArgs::default()
            .model(self.model.clone())
            .messages([system_msg, user_msg])
            .max_tokens(self.max_output_tokens as u32)
            .build()?;

        let resp = self.client.chat().create(request).await?;

        let text = resp
            .choices
            .first()
            .and_then(|c| c.message.content.clone())
            .unwrap_or_default();

        Ok(text)
    }

    pub async fn translate_markdown(&self, markdown: &str) -> Result<String> {
        let chunker = Chunker {
            max_chunk_tokens: self.max_chunk_tokens,
        };
        let chunks = chunker.chunk_markdown(markdown)?;
        let total = chunks.len();
        let mut translated_chunks = Vec::new();
        for (idx, chunk) in chunks.into_iter().enumerate() {
            println!("Translating chunk {}/{}...", idx + 1, total);
            let trans_chunk = self.translate_chunked_markdown(&chunk).await?;
            translated_chunks.push(trans_chunk);
        }
        Ok(translated_chunks.join("\n\n"))
    }

    fn build_translation_prompt(&self, markdown: &str) -> String {
        markdown.to_string()
    }
}

pub struct Chunker {
    pub max_chunk_tokens: usize,
}

impl Chunker {
    pub fn chunk_markdown(&self, markdown: &str) -> Result<Vec<String>> {
        let blocks = self.extract_blocks(markdown)?;

        let bpe = o200k_base().unwrap();
        let mut chunks = Vec::new();
        // 贪心装填块
        let mut current_chunk = String::new();
        let mut current_tokens = 0;
        for block in blocks {
            let block_tokens = bpe.encode_ordinary(&block).len();

            if block_tokens > self.max_chunk_tokens {
                // 如果这个块非常大，就先将当前积累的块推入结果，再单独将这个大块作为一个 chunk 推入结果
                // 打印警告
                eprintln!(
                    "[WARN] oversized block: tokens={},limit={}, preview={:?}",
                    block_tokens,
                    self.max_chunk_tokens,
                    block.chars().take(30).collect::<String>()
                );
                if !current_chunk.is_empty() {
                    chunks.push(current_chunk);
                    current_chunk = String::new();
                    current_tokens = 0;
                }

                chunks.push(block);
                continue;
            }

            let sep_tokens = if current_chunk.is_empty() { 0 } else { 2 }; // 如果不是第一个块，预留两个 token 的分隔符

            if current_tokens + block_tokens + sep_tokens > self.max_chunk_tokens
                && !current_chunk.is_empty()
            {
                chunks.push(current_chunk.trim().to_string());
                current_chunk = String::new();
                current_tokens = 0;
            }

            if !current_chunk.is_empty() {
                current_chunk.push_str("\n\n");
                current_tokens += sep_tokens;
            }
            current_chunk.push_str(&block);
            current_tokens += block_tokens;
        }
        if !current_chunk.is_empty() {
            chunks.push(current_chunk);
        }

        Ok(chunks)
    }

    pub fn extract_blocks<'a>(&self, markdown: &str) -> Result<Vec<String>> {
        let parser = Parser::new(markdown).into_offset_iter();

        let mut current_kind: Option<&str> = None;
        let mut start_pos: usize = 0;
        let mut blocks = Vec::new();

        for (event, range) in parser {
            match event {
                Event::Start(tag) => match tag {
                    Tag::Heading { .. } => {
                        current_kind = Some("heading");
                        start_pos = range.start;
                    }
                    Tag::Paragraph => {
                        current_kind = Some("paragraph");
                        start_pos = range.start;
                    }
                    Tag::CodeBlock(_) => {
                        current_kind = Some("code_block");
                        start_pos = range.start;
                    }
                    Tag::List(_) => {
                        current_kind = Some("list");
                        start_pos = range.start;
                    }
                    _ => {}
                },
                Event::End(end) => {
                    let matched = matches!(
                        (current_kind, end),
                        (Some("heading"), TagEnd::Heading(_))
                            | (Some("paragraph"), TagEnd::Paragraph)
                            | (Some("code_block"), TagEnd::CodeBlock)
                            | (Some("list"), TagEnd::List(_))
                    );

                    if matched {
                        let block = &markdown[start_pos..range.end];
                        blocks.push(block.trim().to_string());

                        current_kind = None;
                    }
                }
                _ => {}
            }
        }

        Ok(blocks)
    }
}

#[cfg(test)]
mod test {

    use std::fs;

    use super::*;
    use crate::{config::require_openai_api_key, translate::LLMTranslator};

    #[test]
    fn test_extract_blocks() {
        let chunker = Chunker {
            max_chunk_tokens: 1000,
        };

        let markdown = fs::read_to_string("./tmp/IML-VIT/hybrid_auto/IML-VIT.md").unwrap();
        let blocks = chunker.extract_blocks(&markdown);

        for block in blocks.unwrap() {
            println!("---\n{}", block);
        }
    }

    #[test]
    fn test_chunk_markdown() {
        let input = r#"# Heading 1
Text in Heading 1.

## Heading 2

- Apple
- Banana

$$
\alpha = \sum_0^n A
$$

```rust
fn main() {
    println!("hello");
}
```

# Heading 2

An inline math latex $B=A+C$
        "#;

        let chunker = Chunker {
            max_chunk_tokens: 1,
        };
        let chunks = chunker.chunk_markdown(input);

        println!("{:#?}", chunks);
    }

    #[tokio::test]
    async fn test_markdown_translate() {
        let api_key = require_openai_api_key().unwrap();
        let base_url = "https://api.xiaomimimo.com/v1".to_string();
        let model = "mimo-v2-flash".to_string();
        let max_output_tokens = 8000;
        let max_chunk_tokens = 5000;

        let translator = LLMTranslator::new(
            base_url,
            api_key,
            model,
            max_output_tokens,
            max_chunk_tokens,
        );

        let input = fs::read_to_string("./tmp/IML-VIT/hybrid_auto/IML-VIT.md").unwrap();

        let output = translator.translate_markdown(&input).await.unwrap();

        fs::write("./tmp/IML-VIT/hybrid_auto/IML-VIT.zh.md", output).unwrap();
    }
}
