# Copilot Instructions for Deep Research Workflow

## Project Overview
This is a **Microsoft Foundry workflow** that replicates OpenAI's DeepResearch feature using recursive AI agents. The project consists of:
- A main workflow (`ai-foundry-new/deep-research-workflow.yaml`) orchestrating multi-step research
- Six specialized agents in `ai-foundry-new/agents/` for clarifying questions, SERP queries, web search, learning extraction, and report generation
- JSON schemas in `ai-foundry-new/schemas/` for structured agent outputs
- Original n8n workflow reference in `n8n-workflow/deep-research.json`

## Architecture & Data Flow
```
User Query → ClarifyingQuestionsAgent → ReportTitleAgent
                    ↓
         [Recursive Loop: depth iterations]
                    ↓
    SERPQueryAgent → WebSearchAgent → LearningsAgent
         ↑________________________________↓
              (accumulates learnings, follow-up questions)
                    ↓
            ReportAgent → Final Markdown Report
```

## Agent YAML Structure
All agents follow this pattern in `ai-foundry-new/agents/`:
```yaml
type: foundry_agent
name: <AgentName>
model:
  id: ${AzureAI:ChatModelId}  # Uses environment variable substitution
instructions: |
  # Multi-line prompt with system context
response_format:
  type: json_schema
  json_schema:
    strict: true  # Always use strict mode for reliable parsing
    schema: { ... }
settings:
  temperature: 0.3-0.8  # Lower for factual, higher for creative
  max_tokens: 500-8000
tools:
  - type: bing_grounding  # Only WebSearchAgent uses tools
```

## Key Conventions

### Power Fx Expressions
The workflow uses Power Fx (not JavaScript) for expressions:
- String concat: `Concatenate("a", "b")` not `"a" + "b"`
- Newlines: `Char(10)` not `\n`
- Conditionals: `If(condition, trueVal, falseVal)`
- Array ops: `CountRows()`, `Concat()`, `Distinct()`
- Prefix expressions with `=` in YAML values

### Variable Scoping
- `Local.variableName` - access workflow variables
- `System.Now` - current timestamp in agent instructions
- Variables declared via `SetVariable` nodes with explicit types

### JSON Schema Requirements
- All agent responses use `strict: true` JSON schemas
- Matching schemas exist in `schemas/` directory for reference
- Use `additionalProperties: false` to prevent extra fields
- Array items need `maxItems` constraints (typically 3)

## Workflow Node Types
| Node | Purpose | Example Usage |
|------|---------|---------------|
| `InvokeAzureAgent` | Call AI agent | `ref: agents/clarifying-questions-agent.yaml` |
| `SetVariable` | Store data | Variable initialization, accumulation |
| `ParseValue` | Parse JSON | Convert agent string response to object |
| `ForEach` | Iterate arrays | Process multiple SERP queries |
| `GoTo` | Control flow | Recursive loop back to `research_iteration` |
| `If` | Conditional | Check `current_iteration >= depth` |

## Adding New Agents
1. Create YAML in `ai-foundry-new/agents/<name>-agent.yaml`
2. Create matching schema in `ai-foundry-new/schemas/<name>-schema.json`
3. Reference in workflow: `ref: agents/<name>-agent.yaml`
4. Use shared instruction preamble from existing agents (researcher persona)

## Common Patterns
- **Accumulator pattern**: Use array variables (`all_learnings`) with `Concat()` to aggregate across iterations
- **Agent output handling**: Always `saveResponseAs` then `ParseValue` before accessing structured data
- **Iteration control**: `current_iteration` counter with `GoTo` for recursive loops

## Environment Setup
Required Azure resources: Azure OpenAI deployment, Bing Search resource
```bash
AZURE_OPENAI_ENDPOINT=<endpoint>
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini  # or gpt-4o
```

## Testing
- Use depth=1, breadth=1 for quick iteration tests (~5 min)
- Sample query from README: "Sugar effect to human brain?"
- Check Foundry portal execution history for step-by-step traces
