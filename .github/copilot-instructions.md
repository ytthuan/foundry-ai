# Copilot Instructions for Microsoft Foundry Workflows (Multi-Workflow Repo)

This repo contains multiple Microsoft Foundry workflow projects. The **canonical reference implementation** is `msfoundry-deep-research`. When building or modifying any other workflow project (including the upcoming `agentic-rag`), always follow the same patterns used in `msfoundry-deep-research` for:

- How we create agents (YAML)
- How we define agent response schemas (strict JSON Schema)
- How we author workflows (Power Fx expressions, control flow, accumulators)

## Canonical Project: `msfoundry-deep-research`

- Workflows live in [msfoundry-deep-research/workflows/current-deep-research-workflow-v2.yaml](../msfoundry-deep-research/workflows/current-deep-research-workflow-v2.yaml) (Bing/WebSearch + sources) and [msfoundry-deep-research/workflows/current-deep-research-internally-workflow.yaml](../msfoundry-deep-research/workflows/current-deep-research-internally-workflow.yaml) (InternalSearch only).
- Agents and schemas are paired:
	- Agents: [msfoundry-deep-research/agents](../msfoundry-deep-research/agents)
	- Schemas: [msfoundry-deep-research/schemas](../msfoundry-deep-research/schemas)
- Do not add YAML comments anywhere.

## New Project: `agentic-rag`

`agentic-rag` is reserved for the RAG workflow and should mirror the structure and conventions from `msfoundry-deep-research`.

- When you create new files under `agentic-rag/{agents,schemas,workflows}`, use `msfoundry-deep-research` as the template for:
	- agent YAML shape and naming
	- schema strictness and structure
	- workflow state variables, iteration patterns, and accumulator handling

## Schema Rules (Strict)

- Agents and schemas are paired and must stay in sync.
- Keep `response_format.json_schema.strict: true` and `additionalProperties: false`.
- Avoid nested objects inside arrays—prefer parallel primitive arrays (e.g., `queries`, `research_goals`, etc.).

## Workflow Authoring Rules (Power Fx)

- Expressions are Power Fx, not JavaScript:
	- Prefix with `=`
	- Use `Concatenate()`/`Concat()` for strings and tables
	- Use `Char(10)` for newlines
	- Use `Sequence()` + `Index(...).Value` for 1-based access
- Do not use `ForEach`; loop with `ConditionGroup` + `GotoAction` as shown in the `msfoundry-deep-research` workflows.

## Accumulators & Web Search Interop

- Accumulators are strings: append learnings/follow-ups with `Concatenate`/`Concat` instead of overwriting.
- Reset `Local.all_iteration_followups` each depth iteration; append per query.
- Web search content comes back as a `messages` table; convert to text with `Concat(Local.web_search_results, Text, Char(10))` before passing to LearningsAgent.
- Keep follow-up questions aggregated before updating `Local.enriched_query`.

## Default Run Paths (Deep Research)

- V2 defaults to depth=2/breadth=3 and uses WebSearchAgent → LearningsAgent → ReportAgent.
- Internal workflow defaults to depth=1/breadth=1 and swaps WebSearchAgent for InternalSearchAgent.
- Both collect clarifications first, then title, iterate queries, and finish with ReportAgent.

## Agent Template

- Agent template: `type: foundry_agent`, `model.id: ${AzureAI:ChatModelId}`, optional `temperature`/`max_tokens`.
- Only the WebSearch agent should declare tools (e.g., `tools: - type: bing_grounding`).
- Keep instructions concise and schemas capped at ~3 items per list.

## Utilities

- [src/utils/create_or_update_agents.py](../src/utils/create_or_update_agents.py) loads agent YAMLs and creates/updates them in Azure AI Foundry (requires `AZURE_AI_PROJECT_ENDPOINT`/`AZURE_AIPROJECT_ENDPOINT`, DefaultAzureCredential, optional .env).

## Quick Test Tips

- Run workflows in Foundry with depth=1, breadth=1 for speed.
- Use Foundry execution traces to debug data flow and iterator state.

If anything is unclear or missing for this repo, say what to refine.
