# AWS Storage Optimizer CLI - Implementation Plan

## Goals
Build a safe, operator-friendly CLI that identifies AWS storage cost optimization opportunities and supports controlled execution of approved actions.

## Non-goals (MVP)
- Fully automated destructive cleanup with no confirmations
- Org-wide multi-account orchestration
- Precise real-time pricing integration from every AWS service SKU

## Guiding Principles
- Default to read-only analysis (`--dry-run` semantics for actions)
- Explicit human confirmation for destructive operations
- Clear audit trail for recommendations and actions
- Conservative recommendations (avoid aggressive false positives)

## MVP Architecture

### Runtime Layers
1. **CLI layer** (`cli.py`)
   - Command routing and options parsing
   - Output format selection
2. **Analyzer layer** (`analyzers/*.py`)
   - Service-specific data collection and heuristics
3. **Recommendation layer** (`recommender.py`)
   - Prioritization and risk scoring
4. **Action layer** (`actions.py`)
   - Safe execution wrappers and dry-run support
5. **Reporting layer** (`reporting.py`)
   - Table and JSON rendering

### Shared Components
- `aws_clients.py`: boto3 session/client factory
- `config.py`: configurable thresholds and defaults
- `models.py`: typed structures for findings and action results

## Delivery Phases

### Phase 1 - Read-only Analyzer (MVP baseline)
- Implement `analyze` command for S3, EBS, RDS
- Generate normalized findings objects
- Print report in table/json
- Optional save to JSON file

### Phase 2 - Controlled Action Execution
- Implement `execute` command for:
  - EBS unattached volume deletion
  - S3 object deletion (explicit bucket + key)
  - RDS resize placeholder workflow
- Enforce confirmations and dry-run defaults
- Log action outcomes

### Phase 3 - Better Cost Signal
- Add configurable monthly savings estimator
- Add environment/profile threshold overrides
- Improve prioritization strategy

### Phase 4 - Operational Hardening
- Add retries/backoff for API calls
- Add optional tag-based exclusions (`DoNotTouch=true`)
- Add integration tests against sandbox account

## Heuristic Rules (Initial)

### S3
- Surface top-N buckets by sampled object size
- Recommend archival/cleanup for old large objects
- Mark as medium risk without lifecycle policy checks

### EBS
- `available` volumes are deletion candidates
- Estimated savings based on size and type placeholder rates
- Mark as low-to-medium risk depending on tags

### RDS
- Underutilized if average CPU < threshold over lookback window
- Recommend instance class downsize (not automatic in MVP)
- Mark as medium/high risk until deeper workload checks are added

## Safety Model
- Every mutating command supports `--dry-run`
- Mutating commands require `--yes` to proceed
- Fail closed on missing required context
- Per-action result status: `dry-run`, `success`, `failed`, `skipped`

## Testing Strategy
- Unit tests for recommendation and action validation logic
- Analyzer tests with mocked/stubbed boto3 clients
- CLI smoke tests for command wiring and JSON output shape

## Repository Structure

```text
src/aws_storage_optimizer/
  cli.py
  aws_clients.py
  config.py
  models.py
  recommender.py
  reporting.py
  actions.py
  analyzers/
    s3.py
    ebs.py
    rds.py
```

## Success Criteria
- CLI runs with profile/region options
- `analyze` returns findings for at least one service
- `report` can render previously saved JSON findings
- `execute` supports dry-run and confirmed execution for at least one safe action
