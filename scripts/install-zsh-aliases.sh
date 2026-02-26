#!/usr/bin/env bash
set -euo pipefail

ZSHRC="${HOME}/.zshrc"
START_MARK="# >>> aws-storage-optimizer aliases >>>"
END_MARK="# <<< aws-storage-optimizer aliases <<<"

mkdir -p "$(dirname "$ZSHRC")"
touch "$ZSHRC"

if grep -Fq "$START_MARK" "$ZSHRC"; then
  echo "AWS Storage Optimizer alias block already exists in $ZSHRC"
  echo "Reload with: source ~/.zshrc"
  exit 0
fi

cat >> "$ZSHRC" <<'EOF'
# >>> aws-storage-optimizer aliases >>>
alias aso='aws-storage-optimizer'
alias asodry='aso execute --dry-run'

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
# <<< aws-storage-optimizer aliases <<<
EOF

echo "Installed AWS Storage Optimizer aliases/functions to $ZSHRC"
echo "Run: source ~/.zshrc"
