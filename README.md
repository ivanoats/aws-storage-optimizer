# AWS Storage Optimizer

This command line utility helps you optimize your AWS storage costs by identifying and recommending actions for underutilized resources. It analyzes your AWS environment and provides insights into which resources can be downsized, terminated, or moved to more cost-effective storage options.

It lists the largest S3 buckets and offers to download, then delete those files. It also identifies EBS volumes that are not attached to any instances and offers to delete them. Additionally, it checks for RDS instances that are underutilized and suggests resizing or terminating them.

## Technologies Used
- Python
- Boto3 (AWS SDK for Python)
- Click (for command-line interface)

## Documentation
- Implementation plan: [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md)
- Command specification: [docs/COMMAND_SPEC.md](docs/COMMAND_SPEC.md)
- Scaffold overview: [docs/SCAFFOLD.md](docs/SCAFFOLD.md)

## Quick Start

### 1. Create virtual environment and install
```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

After activation, run commands directly (no `uv run` needed).

Both command names are available:
- `aws-storage-optimizer`
- `aso`

If you prefer the standard tooling:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Analyze resources
```bash
aws-storage-optimizer analyze --output-format table
aso analyze --output-format table
```

### 3. Save and re-render report
```bash
aso analyze --save artifacts/findings.json --output-format json
aso report --input artifacts/findings.json --output-format table
```

### 4. Dry-run actions
```bash
aso execute --action-type delete-ebs-volume --resource-id vol-0123456789abcdef0 --dry-run
```

### 5. Execute action (explicit confirmation)
```bash
aso execute --action-type delete-ebs-volume --resource-id vol-0123456789abcdef0 --no-dry-run --yes
```

## Global Options
```bash
aso --profile my-aws-profile --region us-east-1 analyze
```

## Optional zsh aliases/functions

Auto-install script:
```bash
./scripts/install-zsh-aliases.sh
source ~/.zshrc
```

Add one of these to your `~/.zshrc`:

### Option A: Simple aliases (recommended)
```bash
alias aso='aws-storage-optimizer'
alias asodry='aso execute --dry-run'
```

### Option B: Function with project-aware fallback
```bash
aso() {
	if [[ -x "$PWD/.venv/bin/aso" ]]; then
		"$PWD/.venv/bin/aso" "$@"
	elif command -v aws-storage-optimizer >/dev/null 2>&1; then
		aws-storage-optimizer "$@"
	else
		echo "aso not found. Run: uv venv && source .venv/bin/activate && uv pip install -e ."
		return 1
	fi
}
```

Reload your shell after editing:
```bash
source ~/.zshrc
```

## Development

Install dev dependencies:
```bash
uv pip install -e '.[dev]'
```

Run linting:
```bash
pylint src/aws_storage_optimizer tests
```

## Safety Notes
- All action commands default to `--dry-run`.
- Non-dry-run mutations require `--yes`.
- Use least-privilege IAM and validate findings before execution.

