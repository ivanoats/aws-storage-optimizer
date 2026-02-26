# Scaffold Overview

This repository now includes an MVP scaffold for the AWS Storage Optimizer CLI.

## Structure

```text
.
├── README.md
├── docs/
│   ├── IMPLEMENTATION_PLAN.md
│   ├── COMMAND_SPEC.md
│   └── SCAFFOLD.md
├── pyproject.toml
└── src/
    └── aws_storage_optimizer/
        ├── __init__.py
        ├── actions.py
        ├── analyzers/
        │   ├── __init__.py
        │   ├── ebs.py
        │   ├── rds.py
        │   └── s3.py
        ├── aws_clients.py
        ├── cli.py
        ├── config.py
        ├── models.py
        ├── recommender.py
        └── reporting.py
```

## What is implemented
- Click-based command group with `analyze`, `report`, `execute`
- Service analyzers for S3, EBS, and RDS
- Prioritization logic for findings
- Console table and JSON output renderers
- Dry-run-first action execution wrappers
- Packaging and CLI entrypoint via `pyproject.toml`

## Current limitations
- S3 bucket sizing uses sampled pagination (bounded for speed)
- RDS recommendation is CPU-based heuristic only
- Savings estimates are intentionally conservative placeholders
- No retry/backoff and no account-wide multi-region sweep yet

## Next practical step
Implement tests for analyzer parsing and CLI command behavior, then harden action guardrails with tag exclusions.
