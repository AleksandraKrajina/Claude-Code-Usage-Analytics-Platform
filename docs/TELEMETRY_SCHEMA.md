# Telemetry Schema (from generate_fake_data.py)

## Event Structure

Each event in `telemetry_logs.jsonl` has:
- **body**: Event type (e.g. `claude_code.api_request`)
- **attributes**: Event-specific fields
- **resource**: User/environment metadata
- **scope**: Instrumentation metadata

## Common Attributes (all events)

| Field | Source | Description |
|-------|--------|-------------|
| event.timestamp | attributes | ISO timestamp |
| organization.id | attributes | Org UUID |
| session.id | attributes | Session UUID |
| terminal.type | attributes | vscode, pycharm, etc. |
| user.account_uuid | attributes | User account UUID |
| user.email | attributes | User email |
| user.id | attributes | User hash (64 chars) |

## Resource (all events)

| Field | Source | Description |
|-------|--------|-------------|
| user.practice | resource | Role (e.g. "Backend Engineering") |
| user.profile | resource | Profile name |
| user.serial | resource | Serial |
| host.arch | resource | arm64, x86_64 |
| host.name | resource | Hostname |
| os.type | resource | darwin, linux, windows |
| os.version | resource | OS version |
| service.name | resource | claude-code-None |
| service.version | resource | Scope version |

## api_request Event (model usage)

| Field | Source | Description |
|-------|--------|-------------|
| input_tokens | attributes | Input token count |
| output_tokens | attributes | Output token count |
| cache_read_tokens | attributes | Cache read tokens |
| cache_creation_tokens | attributes | Cache creation tokens |
| model | attributes | Model name (e.g. claude-sonnet-4-5-20250929) |
| cost_usd | attributes | Cost in USD |
| duration_ms | attributes | Request duration |

## tool_decision / tool_result (tool usage)

| Field | Source | Description |
|-------|--------|-------------|
| tool_name | attributes | Read, Bash, Edit, Grep, etc. |
| decision | attributes | accept / reject |
| source | attributes | config, user_temporary, user_reject |

## Event Types

- `claude_code.api_request` → api_request (tokens, cost, model)
- `claude_code.tool_decision` → tool_decision
- `claude_code.tool_result` → tool_result
- `claude_code.user_prompt` → user_prompt
- `claude_code.api_error` → api_error

## DB Mapping (TelemetryEvent)

| DB Column | Source |
|-----------|--------|
| user_id | attributes.user.id |
| session_id | attributes.session.id |
| role | resource.user.practice |
| project_type | resource.user.practice |
| event_type | body (mapped) |
| timestamp | attributes.event.timestamp |
| model | attributes.model |
| input_tokens | attributes.input_tokens |
| output_tokens | attributes.output_tokens |
| cache_read_tokens | attributes.cache_read_tokens |
| cache_creation_tokens | attributes.cache_creation_tokens |
| cost_usd | attributes.cost_usd |
| duration_ms | attributes.duration_ms |
| tool_name | attributes.tool_name |
