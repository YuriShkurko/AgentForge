# Getting Started

This guide gets you from a fresh checkout to the primary AgentForge demo.

## Prerequisites

- Python 3.12+
- Node 18+
- `pip`
- `npm`
- `make` or the ability to run the commands from the `Makefile` manually

## Install the CLI

From the repository root:

```bash
pip install -e generator/
```

Confirm the CLI is available:

```bash
agentforge --help
```

## Option A: start with the Builder

The Builder is the recommended v1.0 front door.

```bash
agentforge serve-builder
```

Open the printed local URL. Use it to draft a Blueprint from an app idea, inspect the generated YAML, and copy the next `agentforge plan` / `agentforge generate` commands.

The Builder does not write files automatically, deploy infrastructure, call live LLMs, or modify existing repositories.

## Option B: use the committed demo Blueprint

```bash
agentforge plan domain-packs/hybrid-scoring-demo/domain-pack.yaml
agentforge generate domain-packs/hybrid-scoring-demo/domain-pack.yaml --force
```

The generated app appears at:

```text
examples/hybrid-scoring-demo/
```

## Validate

```bash
python -m pytest tests/generator/ -v
make validate
```

`make validate` runs generator tests, generated backend tests, frontend build, and frontend lint. It does not require live LLM/API keys.

## Run the generated app

In one terminal:

```bash
make run-backend
```

In another terminal:

```bash
make run-frontend
```

Open:

- Frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`

## Next

Follow the full guided story in [DEMO_GUIDE.md](DEMO_GUIDE.md), then use [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) for exact command behavior and [SAFETY_MODEL.md](SAFETY_MODEL.md) for trust boundaries.
