# MDTrans

简体中文 | [English](./README.md)   

## 简介

**将任意英文 PDF 文档转换中文的 Markdown 文档！**。

支持数字原生 PDF 和扫描件 PDF。转换过程将保留 PDF 中的文本内容、标题、列表、表格等结构，并将文本翻译成简体中文。由于翻译阶段利用了大模型较长的上下文窗口，MDTrans 在文档级一致性和整体翻译效果上通常优于一般的短上下文翻译软件。最终输出的 Markdown 文件将以 `.zh.md` 结尾，表示这是原始 Markdown 的中文版本。


## 原理

MDTrans 先通过异步 Python 子进程调用官方 `mineru` CLI 完成 PDF 转 Markdown，包括 MinerU 支持的扫描件处理流程，再使用 LangChain 和兼容 OpenAI 的聊天模型，在较大的文档上下文中将生成的 Markdown 翻译为简体中文，而不是碎片化地逐句翻译。

## 环境要求

- 一张能够运行 Mineru 的 GPU（建议至少 16GB 显存）

## 安装

```bash
uv tool install mdtrans
```

## 配置

配置文件位于 `~/.config/mdtrans/config.toml`，如果没有请创建。


```toml
[llm]
base_url = "https://api.deepseek.com"
model = "deepseek-chat"
context_window = 64000
max_output_tokens = 8000
max_chunk_tokens = 5000
```

推荐使用小米 mimo-flash 模型，翻译质量较好且速度快。


## 运行

由于 MDTrans 依赖 OpenAI 兼容的 API 来进行翻译，所以需要设置 `OPENAI_API_KEY` 环境变量指向你的 API 密钥：

```bash
export OPENAI_API_KEY="your-api-key"
```

```bash
mdtrans /path/to/input.pdf /path/to/output-dir
```

脚本会按下面的顺序执行：

1. 接收源 PDF 路径作为第一个位置参数
2. 接收输出目录作为第二个位置参数
3. 运行 `mineru -p <selected-pdf> -o <output-dir> -b hybrid-auto-engine`
4. 在指定输出目录下查找生成的 Markdown 文件
5. 在原始 Markdown 同目录写出 `*.zh.md` 的中文译文副本

## 工作进展

- [x] 基本翻译功能
- [ ] 服务化及Docker化部署：将 MDTrans 封装为一个 RESTful API 服务，并提供 Docker 镜像，方便用户部署和使用。
- [ ] 超长文档翻译：构建 Agent 翻译，实现超长文档翻译（支持 300 页+）
- [ ] 对不同模型翻译性能的评测和优化
- [ ] 支持更多语言的翻译（如日语、韩语等）
- [ ] 提供更多翻译选项（如正式/非正式语气、专业术语处理等）

## 免责声明

MDTrans 旨在提供一种便捷的 PDF 到 Markdown 的翻译工具，但翻译质量可能会受到模型能力、文档复杂度和上下文窗口限制等因素的影响。对于重要或敏感的文档，建议用户在使用 MDTrans 进行初步翻译后，进行人工校对和润色，以确保最终结果的准确性和可读性。MDTrans 不对因翻译错误导致的任何损失或误解负责。