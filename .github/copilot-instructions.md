# Copilot Instructions for Deep Research Workflow

## Project Overview
This is a **Microsoft Foundry workflow** that replicates OpenAI's DeepResearch feature using recursive AI agents. The project consists of:
- **`ai-foundry-new/current-deep-research-workflow.yaml`** - The **current working implementation** that is actually deployed and running with Microsoft Foundry
- Six specialized agents in `ai-foundry-new/agents/` for clarifying questions, SERP queries, web search, learning extraction, and report generation
- JSON schemas in `ai-foundry-new/schemas/` for structured agent outputs

## Important: Workflow File Distinction
| File | Status | Purpose |
|------|--------|---------|
| `current-deep-research-workflow.yaml` | ✅ **Working** | The actual production workflow running on Microsoft Foundry |

When making changes to the **production workflow**, edit `current-deep-research-workflow.yaml`.

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

### ⚠️ CRITICAL: No Comments in Workflow YAML Files
**Do NOT add YAML comments (`#`) to workflow `.yaml` files.** Comments can break the Foundry workflow parser and cause syntax errors. Keep workflow files clean without inline or block comments.

### Variable Scoping
- `Local.variableName` - access workflow variables
- `System.Now` - current timestamp in agent instructions
- Variables declared via `SetVariable` nodes with explicit types

### JSON Schema Requirements
- All agent responses use `strict: true` JSON schemas
- Matching schemas exist in `schemas/` directory for reference
- Use `additionalProperties: false` to prevent extra fields
- Array items need `maxItems` constraints (typically 3)

### ⚠️ CRITICAL: Flat JSON Structure Requirement
Foundry's `responseObject` binding **does NOT properly handle arrays of nested objects**. The nested properties get stripped, leaving empty `{}` objects.

**❌ DON'T USE (nested objects in arrays):**
```json
{
  "queries": [
    { "query": "search terms", "research_goal": "goal description" }
  ]
}
```

**✅ USE (parallel flat arrays):**
```json
{
  "queries": ["search terms 1", "search terms 2"],
  "research_goals": ["goal 1", "goal 2"]
}
```

**Accessing paired data in Power Fx:**
```
Index(Local.serpQueries.queries, 1)         // First query
Index(Local.serpQueries.research_goals, 1)  // Corresponding goal
```

This pattern applies to ALL agents with complex structured outputs. Always use parallel arrays of primitives instead of arrays of objects.

## Workflow Node Types
| Node | Purpose | Example Usage |
|------|---------|---------------|
| `InvokeAzureAgent` | Call AI agent | `ref: agents/clarifying-questions-agent.yaml` |
| `SetVariable` | Store data | Variable initialization, accumulation |
| `ParseValue` | Parse JSON | Convert agent string response to object |
| `GoTo` | Control flow | Recursive loop back to `research_iteration` |
| `ConditionGroup` | Conditional | Check `current_iteration >= depth` |

### ⚠️ KNOWN ISSUE: ForEach Node Limitation
**Do NOT use `ForEach` nodes** in Foundry workflows - they are currently unreliable/unsupported.

**Instead, use the Iterator Pattern with ConditionGroup + GotoAction:**

The pattern involves:
1. Initialize iterator to 0 in `SetMultipleVariables`
2. Get total count before the loop
3. Use `ConditionGroup` as the loop target with compound condition
4. Increment iterator **first**, then access item (makes `Index()` 1-based naturally)
5. Use `GotoAction` with `actionId` to loop back to the `ConditionGroup`

```yaml
- kind: SetVariable
  id: action-get-total
  variable: Local.total_items
  value: '=CountRows(Local.response.items)'

- kind: ConditionGroup
  conditions:
    - condition: '=((Local.total_items > 0) && (Local.iterator < Local.total_items))'
      actions:
        - kind: SetVariable
          id: action-increment
          variable: Local.iterator
          value: '=Local.iterator + 1'
        - kind: SetVariable
          id: action-get-current
          variable: Local.current_item
          value: '=Index(Local.response.items, Local.iterator).Value'
        - kind: GotoAction
          actionId: loop-condition-id
          id: action-loop-back
      id: if-has-more-items
    - condition: '=Local.total_items = 0'
      actions:
        - kind: SetVariable
          id: action-fallback
          variable: Local.current_item
          value: '=Local.fallback_value'
      id: if-no-items
  id: loop-condition-id
  elseActions: []
```

**Key points:**
- Use `Index(array, position).Value` where position is 1-based
- Increment iterator **before** accessing with `Index()` (iterator goes 0→1→2, `Index()` uses 1→2→3)
- Use compound condition `((count > 0) && (iterator < count))` to handle empty arrays
- Use `GotoAction` with `actionId` (not `GoTo` with `target`)
- The `ConditionGroup` node ID serves as the loop target
- Add a fallback condition for empty arrays if needed

## Adding New Agents
1. Create YAML in `ai-foundry-new/agents/<name>-agent.yaml`
2. Create matching schema in `ai-foundry-new/schemas/<name>-schema.json`
3. Reference in workflow: `ref: agents/<name>-agent.yaml`
4. Use shared instruction preamble from existing agents (researcher persona)

## Common Patterns
- **Accumulator pattern**: Use string variables (`all_learnings`, `all_iteration_followups`) with `Concatenate()` and `Concat()` to aggregate across iterations
- **Follow-up accumulation**: Reset `all_iteration_followups` at the start of each depth iteration, then append follow-ups from every query in the breadth loop
- **Agent output handling**: Always `saveResponseAs` then `ParseValue` before accessing structured data
- **Message table to text**: When using `messages:` output type, convert to text with `Concat(Local.messages_var, Text, Char(10))`
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
