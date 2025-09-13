## 1. Embedding Knowledge Base (ekb)
- [1. Embedding Knowledge Base (ekb)](#1-embedding-knowledge-base-ekb)
- [2. Features](#2-features)
- [3. Usage](#3-usage)
  - [3.1. Examples](#31-examples)


Convert various document types to vector database for AI retrieval.

## 2. Features

- **Independent .gitignore**: support .gitignore filtering
- **Regex Patterns**: support standard Python regex syntax for include/exclude rules
- **Configurable Order**: support control whether exclude or include patterns are applied first

## 3. Usage

Use `python manage_kb.py` to manage knowledge bases.

```bash
usage: manage_kb.py [-h] {update,search,add,status,list} ...

Generic embedding knowledge base management tool

positional arguments:
  {update,search,add,status,list}
                        Available commands
    update              Create or update knowledge base
    search              Search knowledge base
    add                 Add text content to knowledge base
    status              Show statistics
    list                List all knowledge bases

options:
  -h, --help            show this help message and exit
```

Use `python manage_kb.py command --help` to get help for each command.

### 3.1. Examples

Create ekb from current directory

```bash
python manage_kb.py update -n cur_kb .
```

Create ekb from `data/blog_content`

```bash
python manage_kb.py update -n blog -s data/blog_content
```

Update blog ekb (if you want to update an existing ekb, you don't need to specify any parameters except the name)

```bash
python manage_kb.py update -n blog
```

Search ekb

```bash
python manage_kb.py search -n blog "What is the capital of France?"
```

Show ekb stats

```bash
python manage_kb.py status -n blog
```

List all ekb

```bash
python manage_kb.py list
```
