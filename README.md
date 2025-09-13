# Agent-For-SillyTavern

- [Agent-For-SillyTavern](#agent-for-sillytavern)
  - [1. Function Introduction](#1-function-introduction)
  - [2. Installation](#2-installation)
    - [2.1. Basic Dependencies](#21-basic-dependencies)
    - [2.2. Dependencies for Embedding Knowledge Base](#22-dependencies-for-embedding-knowledge-base)
  - [3. Usage](#3-usage)
    - [3.1. Basic Usage](#31-basic-usage)
    - [3.2. local run in console](#32-local-run-in-console)
    - [3.3. Embedding Knowledge Base (ekb or EKB)](#33-embedding-knowledge-base-ekb-or-ekb)
    - [3.4. SillyTavern Configuration](#34-sillytavern-configuration)
  - [4. All Documents](#4-all-documents)

## 1. Function Introduction

- Agent can refer to the embedding knowledge base (ekb) when answering user questions.
- Agent can execute shell commands and view their output. Non-secure commands will prompt the user for confirmation.
- OpenAI-compatible API for [SillyTavern](https://github.com/SillyTavern/SillyTavern) to call.

## 2. Installation

### 2.1. Basic Dependencies

```bash
conda create -n agent4st python=3.10 -y
conda activate agent4st
git clone git@github.com:zeroDtree/agent-for-ST.git
cd agent-for-ST
pip install -r requirements.txt
```

### 2.2. Dependencies for Embedding Knowledge Base

Because indexing embedding knowledge base uses a language model, you need to install `sentence-transformers` (this package depends on PyTorch, so it is recommended that you install PyTorch separately first; otherwise, a newer version of CUDA will be automatically downloaded). pytorch)

```bash
pip install -r requirements_kb.txt
```

## 3. Usage

### 3.1. Basic Usage

web server for SillyTavern

```bash
python web_server.py
```

After successful execution, the server will listen on the default `http://127.0.0.1:5000` address.

In web server mode, the agent will not store the conversation history in memory. All conversations will be stored and managed by SillyTavern.

Run`python web_server.py --help` to see options.

### 3.2. local run in console

```bash
python main.py
```

In console mode, the agent will store the conversation history in memory.

Run `python main.py --help` to see options.

### 3.3. Embedding Knowledge Base (ekb or EKB)

Convert various document types to vector database for AI retrieval.

Features:

- **Independent .gitignore**: support .gitignore filtering
- **Regex Patterns**: support standard Python regex syntax for include/exclude rules
- **Configurable Order**: support control whether exclude or include patterns are applied first

Detailed documentation: [Embedding Knowledge Base](./doc/embedding-knowledge-base.md)

### 3.4. SillyTavern Configuration

Assuming you have already installed SillyTavern.

Configure SillyTavern's API address to `http://0.0.0.0:5000/v1`.

Install [Tavern Helper](https://n0vi028.github.io/JS-Slash-Runner-Doc/) in SillyTavern.

Import the [Character Card](./char-cards/Qwer.json) into SillyTavern. The character card contains the character definition, the tool call confirmation JS script, and lorebook.

You can (should) modify the character definition and lorebook as needed.

To display LaTeX formulas, you need to install the [SillyTavern LaTeX plugin](https://github.com/SillyTavern/Extension-LaTeX) in SillyTavern. The [char card](./char-cards/Qwer.json) already contains regular expressions for displaying mathematical formulas.

If you change the server port when run `python web_server.py`, you need to change `const serverUrl = "http://localhost:5000";
` in [st-confirm.js](./javascripts/st-confirm.js). Then put it into libs of [Tavern Helper](https://n0vi028.github.io/JS-Slash-Runner-Doc/).

## 4. All Documents

- **[Command Check Flow](./doc/zh/command-check-flow.md)** - Comprehensive flowchart and documentation explaining the multi-layered security validation process for shell commands, including blacklist/whitelist checks, path validation, and restricted mode operations.

- **[Auto Mode](./doc/zh/auto-mode.md)** - Guide to automated command approval system with 5 different modes (Manual, Blacklist Reject, Universal Reject, Whitelist Accept, Universal Accept) for varying security requirements and automation levels.

- **[LLM Configuration](./doc/llm-configuration.md)** - Configuration guide for switching between different LLM models and API providers through command line arguments.

- **[Embedding Knowledge Base](./doc/embedding-knowledge-base.md)** - Documentation for the vector database system that converts various document types into searchable embeddings, featuring .gitignore support, regex patterns, and configurable filtering options.
