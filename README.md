# Agent-For-SillyTavern

- [Agent-For-SillyTavern](#agent-for-sillytavern)
  - [1. Function Introduction](#1-function-introduction)
  - [2. Usage](#2-usage)
    - [2.1. Basic Usage](#21-basic-usage)
      - [2.1.1. Dependency Installation](#211-dependency-installation)
      - [2.1.2. Run `web_server.py`](#212-run-web_serverpy)
      - [2.1.3. SillyTavern Configuration](#213-sillytavern-configuration)
    - [2.2. Blog Knowledge Base](#22-blog-knowledge-base)
      - [2.2.1. Blog Knowledge Base Configuration](#221-blog-knowledge-base-configuration)
      - [2.2.2. Creating/Updating a Blog Knowledge Base](#222-creatingupdating-a-blog-knowledge-base)
  - [3. Documentation](#3-documentation)

## 1. Function Introduction

- Agent can refer to the blog content when answering user questions.
- Agent can execute shell commands and view their output. Non-secure commands will prompt the user for confirmation.
- OpenAI-compatible API for SillyTavern to call.

## 2. Usage

### 2.1. Basic Usage

#### 2.1.1. Dependency Installation

```bash
conda create -n agent4st python=3.10 -y
conda activate agent4st
git clone git@github.com:zeroDtree/agent-for-ST.git
cd agent-for-ST
pip install -r requirements.txt
```

#### 2.1.2. Run `web_server.py`

```bash
python web_server.py
```

After successful execution, the server will listen on the default `http://127.0.0.1:5000` address.

Run`python web_server.py --help` to see options.

#### 2.1.3. SillyTavern Configuration

Assuming you have already installed SillyTavern.

Configure SillyTavern's API address to `http://0.0.0.0:5000/v1`.

Install [Tavern Helper](https://n0vi028.github.io/JS-Slash-Runner-Doc/)

Import the [Character Card](./char-cards/Qwer.json) into SillyTavern. The character card contains the character definition and the tool call confirmation JS script.

You can (should) modify the character definition as needed.

To display LaTeX formulas, you need to install the [SillyTavern LaTeX plugin](https://github.com/SillyTavern/Extension-LaTeX). The [char card](./char-cards/Qwer.json) already contains regular expressions for displaying mathematical formulas.

### 2.2. Blog Knowledge Base

#### 2.2.1. Blog Knowledge Base Configuration

The following are the configuration parameters supported by the blog knowledge base, which can be configured in `config/config.py`.

You may need to modify `blog_path`, which is the directory where your blog content is located. For example, you can use a soft link to point to your blog content directory.

#### 2.2.2. Creating/Updating a Blog Knowledge Base

Because indexing blogs uses a language model, you need to install `sentence-transformers` (this package depends on PyTorch, so it is recommended that you install PyTorch separately first; otherwise, a newer version of CUDA will be automatically downloaded). pytorch)

```bash
pip install -r requirements_kb.txt
```

Update the database (automatically created for the first update)

```bash
python manage_kb.py update
```

The current code only scans `*.md` files in the blog content directory; files in other formats are not indexed.

## 3. Documentation

[Command Check Flow](./doc/zh/command-check-flow.md)
[Auto-Reject Mode](./doc/zh/auto-reject.md)
[LLM Configuration](./doc/llm-configuration.md)
