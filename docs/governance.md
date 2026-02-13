# Finlify Scoring Policy Governance

## Policy Versioning
Decisions in Finlify are driven by versioned JSON policies. This ensures that:
1. **Traceability**: Every score returned by the API includes a `policy_version` field.
2. **Immutability**: Once a policy version (e.g., `v1.0`) is deployed, it should not be mutated. New logic requires `v1.1` or `v2.0`.

## Policy Naming Conventions

### Policy ID Format
`{strategy}_{version}`

Examples:
- `balanced_v1`
- `growth_hightech_v1`
- `conservative_v1`

### Strategy Names
- Use lowercase with underscores
- Be descriptive but concise
- Avoid version numbers in the strategy name itself

### Version Numbers
- Use semantic versioning: `v{major}.{minor}`
- Increment minor version for non-breaking changes
- Increment major version for breaking changes

## Change Classification

### Non-Breaking Changes (Minor Version Bump)
Changes that do NOT require code updates:
- Adjusting factor weights (as long as they sum to 1.0)
- Modifying thresholds
- Updating reason templates (text only)
- Changing assumption modifiers

**Example**: `balanced_v1` → `balanced_v1.1`

### Breaking Changes (Major Version Bump)
Changes that may require code updates:
- Adding or removing factors
- Changing factor semantics
- Modifying policy schema structure
- Renaming fields

**Example**: `balanced_v1` → `balanced_v2`

## Schema Definition
The policy JSON must adhere to the following schema:

```json
{
  "policy_id": "string (e.g. balanced_v1)",
  "policy_version": "string (e.g. v1.0)",
  "strategy_name": "string (human-readable)",
  "description": "string",
  "factors": {
    "factor_name": { "weight": "float (0.0-1.0, sum must equal 1.0)" }
  },
  "thresholds": {
    "strong_buy": "float (0.0-1.0)",
    "buy": "float",
    "hold": "float",
    "sell": "float"
  },
  "rating_labels": {
    "5": "string",
    "4": "string",
    "3": "string",
    "2": "string",
    "1": "string"
  },
  "action_mapping": {
    "strong_buy": "string",
    "buy": "string",
    "hold": "string",
    "sell": "string",
    "strong_sell": "string"
  },
  "assumption_modifiers": {
    "modifier_name": "integer"
  },
  "reason_templates": {
    "factor_name": {
      "match": "string (template with {variable})",
      "mismatch": "string"
    }
  }
}
```

## Validation Rules
All policies must satisfy:
1. **Factor weights sum to 1.0** (within 0.001 tolerance)
2. **Thresholds are monotonic**: `strong_buy > buy > hold > sell`
3. **All required reason templates exist** for each factor
4. **Policy ID matches filename** (without .json extension)

## Modification Process
1. Copy existing policy to `{policy_id}_v{new_version}.json`.
2. Adjust weights, thresholds, or templates.
3. Validate schema and rules.
4. Update `FINLIFY_POLICY_ID` environment variable.
5. Deploy and verify `policy_version` in API responses.
6. Document changes in version control commit message.
