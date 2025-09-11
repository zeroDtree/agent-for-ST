# LLM Configuration Guide

## Overview

The agent system now supports flexible LLM configuration through command line arguments. You can easily switch between different models and API providers without modifying code.

## Configuration Options (`web_server.py`)

### Available Parameters

| Parameter           | Description                      | Example                                                    |
| ------------------- | -------------------------------- | ---------------------------------------------------------- |
| `--llm-model`       | Set the LLM model name           | `deepseek-chat`, `gpt-4`, `claude-3.5-sonnet`              |
| `--llm-url`         | Set the API base URL             | `https://api.deepseek.com/v1`, `https://api.openai.com/v1` |
| `--llm-api-key-env` | Environment variable for API key | `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`                       |
| `--llm-max-tokens`  | Maximum response tokens          | `4096`, `8192`                                             |
| `--llm-temperature` | Response creativity (0.0-2.0)    | `0.7`, `1.0`                                               |

### Default Configuration

By default, the system uses:

- Model: `deepseek-chat`
- URL: `https://api.deepseek.com/v1`
- API Key Environment: `DEEPSEEK_API_KEY`
- Max Tokens: `8192`
- Temperature: `1.0`
