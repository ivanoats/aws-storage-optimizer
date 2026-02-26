# AWS Storage Optimizer CLI - Command Specification

## Command Group
`aws-storage-optimizer`

Alias:
`aso`

## Global Options
- `--profile TEXT`: AWS profile name (optional)
- `--region TEXT`: AWS region override (optional)

---

## 1) `analyze`
Collect findings from selected AWS services and print/export results.

### Usage
```bash
aws-storage-optimizer analyze [OPTIONS]
```

### Options
- `--services [s3|ebs|rds]...`: one or more services to analyze (default: all)
- `--output-format [table|json]`: output renderer (default: table)
- `--top-n-s3 INTEGER`: number of S3 buckets to include (default: 10)
- `--save PATH`: optional path to persist findings JSON

### Behavior
- Calls analyzers for selected services
- Normalizes and prioritizes findings
- Prints report in requested format
- Optionally writes JSON artifact to disk

### Exit Codes
- `0` success
- `1` analysis failed

---

## 2) `report`
Render an existing findings JSON file in table/json output.

### Usage
```bash
aws-storage-optimizer report --input findings.json [OPTIONS]
```

### Options
- `--input PATH` (required): findings JSON file
- `--output-format [table|json]`: renderer format (default: table)

### Behavior
- Reads persisted findings JSON
- Validates structure
- Re-renders for console viewing or downstream piping

### Exit Codes
- `0` success
- `1` parse or validation error

---

## 3) `execute`
Apply a single approved action with explicit parameters.

### Usage
```bash
aws-storage-optimizer execute --action-type TYPE --resource-id ID [OPTIONS]
```

### Options
- `--action-type [delete-ebs-volume|delete-s3-object|resize-rds-instance]` (required)
- `--resource-id TEXT` (required): primary resource identifier
- `--bucket TEXT`: required for `delete-s3-object`
- `--key TEXT`: required for `delete-s3-object`
- `--target-class TEXT`: required for `resize-rds-instance`
- `--dry-run/--no-dry-run`: simulate only by default (`--dry-run`)
- `--yes`: required to execute non-dry-run changes

### Behavior
- Validates action-specific required arguments
- In `--dry-run` mode: prints intended action only
- In non-dry-run mode: executes via AWS API and prints result status

### Exit Codes
- `0` action completed (or dry-run simulated)
- `1` validation or execution error

---

## Output Schema (Findings JSON)

```json
{
  "generated_at": "2026-02-26T00:00:00Z",
  "findings": [
    {
      "service": "ebs",
      "resource_id": "vol-123",
      "region": "us-east-1",
      "recommendation": "Delete unattached EBS volume",
      "estimated_monthly_savings_usd": 8.0,
      "risk_level": "low",
      "details": {
        "size_gib": 100,
        "volume_type": "gp3"
      }
    }
  ]
}
```

## Notes
- All mutating actions should be treated as opt-in and reversible where possible.
- Future versions may add batch execution and approval files.
