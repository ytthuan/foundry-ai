# Agents Documentation

This document provides comprehensive documentation for all agents used across the Microsoft Foundry workflow projects in this repository.

## Overview

This repository contains two main workflow projects, each with their own set of specialized agents:

- **`msfoundry-deep-research`**: Canonical reference implementation for deep research workflows
- **`agentic-rag`**: RAG (Retrieval-Augmented Generation) workflow implementation

All agents follow consistent patterns and conventions established in the canonical `msfoundry-deep-research` project.

## Agent Architecture

### Agent Template Structure

All agents follow this standard YAML structure:

```yaml
metadata:
  logo: Avatar_Default.svg
  description: ""
  modified_at: "<timestamp>"
object: agent.version
id: AgentName:version
name: AgentName
version: "<version>"
description: ""
created_at: <timestamp>
definition:
  kind: prompt
  model: <model-id>  # e.g., gpt-5-nano, model-router
  instructions: |-
    <agent instructions>
  temperature: 0.01  # Optional
  top_p: 0.01        # Optional
  tools: []          # Only WebSearchAgent uses tools
  text:
    format:
      type: json_schema  # or "text" for free-form responses
      name: <schema_name>
      schema:
        <JSON Schema definition>
      strict: true
    verbosity: null
```

### Key Patterns

1. **Model Selection**:
   - `gpt-5-nano`: For simpler, faster tasks (query generation, basic extraction)
   - `model-router`: For complex reasoning tasks (learnings, reports, answers)

2. **Temperature Settings**:
   - Default: `0.01` for deterministic, consistent outputs
   - Only adjust if creativity is explicitly needed

3. **Schema Strictness**:
   - Always use `strict: true` for JSON schema responses
   - Always set `additionalProperties: false`
   - Avoid nested objects in arrays—use parallel arrays instead

4. **Tools**:
   - Only agents that need external capabilities declare tools
   - `WebSearchAgent` uses `web_search_preview` (Bing grounding)
   - `RagRetrieverAgent` uses MCP tools for Azure AI Search

## msfoundry-deep-research Agents

### ClarifyingQuestionsAgent

**Purpose**: Generates follow-up questions to refine and clarify the research direction before starting the main research process.

**Location**: `msfoundry-deep-research/agents/clarifying-questions-agent.yaml`

**Schema**: `msfoundry-deep-research/schemas/clarifying-questions-schema.json`

**Model**: `gpt-5-nano`

**Output Format**: Text (free-form numbered list)

**Behavior**:
- Asks 3-5 concise clarifying questions
- Helps narrow down research scope
- Identifies specific areas of interest
- Ensures research focuses on user's actual needs

**Usage in Workflow**:
- Called at the beginning of the workflow
- User answers each question sequentially
- Answers are accumulated into `enriched_query`

**Key Instructions**:
- Treat user as highly experienced analyst
- Be detailed and thorough
- Consider new technologies and contrarian ideas
- Value good arguments over authorities

---

### SERPQueryAgent

**Purpose**: Generates web search queries based on the research topic and accumulated learnings.

**Location**: `msfoundry-deep-research/agents/serp-query-agent.yaml`

**Schema**: `msfoundry-deep-research/schemas/serp-queries-schema.json`

**Model**: `model-router`

**Output Format**: JSON Schema (strict)

**Response Structure**:
```json
{
  "queries": ["keyword query 1", "keyword query 2", ...],
  "research_goals": ["goal for query 1", "goal for query 2", ...]
}
```

**Behavior**:
- Generates keyword-only queries (no full sentences)
- Creates unique queries covering different aspects
- Uses previous learnings to generate more targeted queries in later iterations
- Generates exactly the number of queries requested (breadth parameter)

**Usage in Workflow**:
- Called at the start of each depth iteration
- Outputs parallel arrays (queries and research_goals)
- Accessed via `Index(Local.serpQueries.queries, 1)` in Power Fx

**Key Instructions**:
- Reduce queries to keywords only
- Make each query unique and cover different angles
- Consider technical, practical, comparative, historical, and future trends
- Build upon previous learnings when provided

---

### WebSearchAgent

**Purpose**: Performs web searches using Bing grounding and extracts relevant content from search results.

**Location**: `msfoundry-deep-research/agents/web-search-agent.yaml`

**Schema**: `msfoundry-deep-research/schemas/web-search-agent-schema.json`

**Model**: `gpt-5-nano`

**Output Format**: Messages table (not JSON)

**Tools**: 
- `web_search_preview` (Bing grounding)

**Behavior**:
- Uses Web Search tool to find relevant web pages
- Extracts main content from top results
- Summarizes key information found
- Includes source URLs for attribution
- Focuses on authoritative and credible sources

**Usage in Workflow**:
- Called for each search query in the breadth loop
- Returns results as a `messages` table
- Must be converted to text: `Concat(Local.web_search_results, Text, Char(10))`
- Results passed to LearningsAgent for extraction

**Key Instructions**:
- Find authoritative and credible sources
- Extract factual information
- Avoid duplicate or redundant content
- Prioritize recent and up-to-date information

---

### InternalSearchAgent

**Purpose**: Performs internal document search instead of web search (alternative to WebSearchAgent).

**Location**: `msfoundry-deep-research/agents/internal-search-agent.yaml`

**Schema**: `msfoundry-deep-research/schemas/web-search-agent-schema.json`

**Model**: `gpt-5-nano`

**Output Format**: Messages table

**Behavior**:
- Searches internal knowledge base or document repository
- Similar structure to WebSearchAgent but for internal sources
- Used in `current-deep-research-internally-workflow.yaml`

**Usage in Workflow**:
- Replaces WebSearchAgent in internal-only workflows
- Same conversion pattern: `Concat(Local.internal_search_results, Text, Char(10))`

---

### LearningsAgent

**Purpose**: Extracts key learnings, follow-up questions, and sources from web search content.

**Location**: `msfoundry-deep-research/agents/learnings-agent.yaml`

**Schema**: `msfoundry-deep-research/schemas/learnings-schema.json`

**Model**: `model-router`

**Output Format**: JSON Schema (strict)

**Response Structure**:
```json
{
  "learnings": ["learning 1", "learning 2", "learning 3"],
  "follow_up_questions": ["question 1", "question 2", "question 3"],
  "sources": ["source 1", "source 2", ...]
}
```

**Behavior**:
- Extracts maximum 3 unique, information-dense learnings
- Generates up to 3 follow-up questions for deeper research
- Extracts all source URLs (max 10)
- Each learning should be concise but information-dense
- Includes specific entities, metrics, numbers, dates

**Usage in Workflow**:
- Called after each web search
- Learnings accumulated to `all_learnings`
- Follow-up questions accumulated to `all_iteration_followups`
- Sources collected for final report

**Key Instructions**:
- Return maximum 3 learnings (fewer if content is clear)
- Make each learning unique and not similar to others
- Include specific entities: people, companies, products, places, things
- Include exact metrics, numbers, dates when available

---

### ReportTitleAgent

**Purpose**: Generates a concise title and description for the research report.

**Location**: `msfoundry-deep-research/agents/report-title-agent.yaml`

**Schema**: `msfoundry-deep-research/schemas/report-title-schema.json`

**Model**: `model-router`

**Output Format**: JSON Schema (strict)

**Response Structure**:
```json
{
  "title": "Research Report Title",
  "description": "Brief description of the research scope"
}
```

**Behavior**:
- Creates a clear, descriptive title
- Generates a brief description of research scope
- Called early in workflow after clarifying questions

**Usage in Workflow**:
- Called after clarifying questions phase
- Title and description displayed to user
- Used to initialize the report structure

---

### ReportAgent

**Purpose**: Synthesizes all accumulated learnings into a comprehensive markdown research report.

**Location**: `msfoundry-deep-research/agents/report-agent.yaml`

**Schema**: `msfoundry-deep-research/schemas/report-agent-schema.json`

**Model**: `model-router`

**Output Format**: Text (Markdown)

**Behavior**:
- Writes comprehensive research report (3+ pages)
- Includes ALL learnings from research
- Formats in Markdown with headings, lists, tables
- Adds context and analysis to raw facts
- Ends with conclusions and actionable recommendations
- Includes "Sources" section at the end

**Usage in Workflow**:
- Called at the end after all research iterations
- Receives all accumulated learnings
- Generates final markdown report
- Sources section includes all collected URLs

**Key Instructions**:
- Make report as detailed as possible (3+ pages)
- Include ALL learnings - do not omit any
- Use Markdown formatting (H1, H2, H3, tables, bullet points)
- Add context and analysis to raw facts
- End with conclusions and actionable recommendations

---

## agentic-rag Agents

### RagIntentRouterAgent

**Purpose**: Routes user questions to determine the appropriate RAG workflow path.

**Location**: `agentic-rag/agents/rag-intent-router-agent.yaml`

**Schema**: `agentic-rag/schemas/rag-intent-router-schema.json`

**Model**: `model-router`

**Output Format**: JSON Schema (strict)

**Behavior**:
- Analyzes user question intent
- Determines if question requires simple retrieval or complex multi-step planning
- Routes to appropriate workflow path

**Usage in Workflow**:
- First agent called in RAG workflow
- Determines workflow routing

---

### RagQueryPlanAgent

**Purpose**: Designs retrieval plans for RAG system backed by Azure AI Search.

**Location**: `agentic-rag/agents/rag-query-plan-agent.yaml`

**Schema**: `agentic-rag/schemas/rag-query-plan-schema.json`

**Model**: `model-router`

**Output Format**: JSON Schema (strict)

**Response Structure**:
```json
{
  "queries": ["query 1", "query 2", "query 3"],
  "retrieval_goals": ["goal 1", "goal 2", "goal 3"],
  "filter": "OData filter string or empty"
}
```

**Behavior**:
- Generates up to 3 short search queries
- Provides retrieval goal for each query
- Creates OData filter string if user provides constraints
- Prefers 1 query when question is clear
- Uses separate queries per option for comparisons

**Key Instructions**:
- Queries should be short phrases/keywords, not long sentences
- Prefer 1 query when question is clear
- If user asks for comparison, use separate queries per option
- Provide OData filter only if user explicitly provides constraints

---

### RagRetrieverAgent

**Purpose**: Retrieves relevant chunks from Azure AI Search Index using MCP tools.

**Location**: `agentic-rag/agents/rag-retriever-agent.yaml`

**Schema**: `agentic-rag/schemas/rag-retrieval-schema.json`

**Model**: `gpt-5-nano`

**Output Format**: JSON Schema (strict)

**Tools**:
- MCP tool for Azure AI Search Index queries

**Response Structure**:
```json
{
  "query_used": "actual query executed",
  "chunk_texts": ["chunk 1", "chunk 2", ...],
  "chunk_sources": ["source 1", "source 2", ...]
}
```

**Behavior**:
- Runs search using retrieval tool (MCP)
- Prefers hybrid retrieval (vector + keyword)
- Uses semantic ranking when available
- Retrieves up to 20 diverse, non-duplicative chunks
- Returns chunk_texts and aligned chunk_sources
- Passes OData filters through to index query when supported

**Key Instructions**:
- Prefer hybrid retrieval (vector + keyword) when available
- Use semantic ranking when available and relevant
- Retrieve up to 20 diverse, non-duplicative chunks
- Extract most useful fields into text if tool returns rich objects

---

### RagRerankAgent

**Purpose**: Reranks and selects the best chunks for answering the user question.

**Location**: `agentic-rag/agents/rag-rerank-agent.yaml`

**Schema**: `agentic-rag/schemas/rag-rerank-schema.json`

**Model**: `model-router`

**Output Format**: JSON Schema (strict)

**Response Structure**:
```json
{
  "selected_chunk_texts": ["chunk 1", "chunk 2", ...],
  "selected_sources": ["source 1", "source 2", ...],
  "selected_rationales": ["rationale 1", "rationale 2", ...],
  "missing_info_questions": ["question 1", "question 2", ...]
}
```

**Behavior**:
- Reranks retrieved chunks
- Picks best chunks for answering question
- Prefers chunks that directly answer, define, or provide authoritative steps
- Reduces redundancy (avoids near-duplicates)
- Selects up to 8 chunks
- Returns missing_info_questions if context is insufficient

**Key Instructions**:
- Prefer chunks that directly answer, define, or provide authoritative steps
- Reduce redundancy: avoid selecting near-duplicates
- Select up to 8 chunks
- Return up to 3 missing_info_questions if context insufficient

---

### RagEvidenceAgent

**Purpose**: Extracts and validates evidence from retrieved chunks.

**Location**: `agentic-rag/agents/rag-evidence-agent.yaml`

**Schema**: `agentic-rag/schemas/rag-evidence-schema.json`

**Model**: `model-router`

**Output Format**: JSON Schema (strict)

**Behavior**:
- Extracts evidence from retrieved chunks
- Validates evidence quality
- Structures evidence for answer generation

**Usage in Workflow**:
- Called after reranking
- Prepares evidence for answer agent

---

### RagAnswerAgent

**Purpose**: Generates final answer using provided reranked chunks and sources.

**Location**: `agentic-rag/agents/rag-answer-agent.yaml`

**Schema**: `agentic-rag/schemas/rag-answer-schema.json`

**Model**: `model-router`

**Output Format**: JSON Schema (strict)

**Response Structure**:
```json
{
  "answer_markdown": "Final answer in Markdown format",
  "sources": ["source 1", "source 2", ...]
}
```

**Behavior**:
- Answers ONLY using provided chunks
- If chunks are insufficient, says what is missing and asks focused follow-up questions
- Writes clear, direct answer in Markdown
- Includes citations by referencing sources inline like [Source]
- Does not invent URLs or facts

**Key Instructions**:
- Answer ONLY using the provided chunks
- If chunks are insufficient, say what is missing and ask focused follow-up questions
- Write a clear, direct answer in Markdown
- Include citations by referencing the provided sources inline like [Source]
- Do not invent URLs or facts

---

## Schema Rules

### Strict JSON Schema Requirements

All agents with JSON schema responses must follow these rules:

1. **Strict Mode**: Always set `strict: true`
2. **Additional Properties**: Always set `additionalProperties: false`
3. **Parallel Arrays**: Avoid nested objects in arrays—use parallel primitive arrays instead

**Example - Good (Parallel Arrays)**:
```json
{
  "queries": ["query 1", "query 2"],
  "research_goals": ["goal 1", "goal 2"]
}
```

**Example - Bad (Nested Objects)**:
```json
{
  "items": [
    {"query": "query 1", "goal": "goal 1"},
    {"query": "query 2", "goal": "goal 2"}
  ]
}
```

### Schema-Agent Pairing

Agents and schemas are paired and must stay in sync:

- Agent YAML files: `{project}/agents/{agent-name}-agent.yaml`
- Schema JSON files: `{project}/schemas/{agent-name}-schema.json`

When modifying an agent's output structure:
1. Update the schema in the agent YAML file
2. Update the corresponding schema JSON file
3. Ensure both have identical structure

---

## Agent Deployment

### Using create_or_update_agents.py

The utility script `src/utils/create_or_update_agents.py` loads agent YAMLs and creates/updates them in Azure AI Foundry.

**Requirements**:
- `AZURE_AI_PROJECT_ENDPOINT` or `AZURE_AIPROJECT_ENDPOINT` environment variable
- DefaultAzureCredential (or .env file with credentials)

**Usage**:
```bash
source .venv/bin/activate && python3 src/utils/create_or_update_agents.py
```

**Note**: Always use a virtual environment when running Python code in this project.

---

## Best Practices

### Agent Instructions

1. **Be Concise**: Keep instructions focused and clear
2. **Expert User**: Treat user as highly experienced analyst
3. **Detailed Output**: Be as detailed as possible, don't simplify
4. **Accuracy First**: Mistakes erode trust, be accurate and thorough
5. **Consider Edge Cases**: Handle subjects after knowledge cutoff gracefully

### Schema Design

1. **Cap List Sizes**: Keep arrays capped at ~3-10 items per list (as specified)
2. **Use Parallel Arrays**: For paired data, use parallel arrays instead of nested objects
3. **Required Fields**: Only mark fields as required if they're always needed
4. **Descriptions**: Include clear descriptions for all schema properties

### Model Selection

- **Simple Tasks** (query generation, basic extraction): Use `gpt-5-nano`
- **Complex Reasoning** (learnings, reports, answers): Use `model-router`

### Temperature Settings

- Default: `0.01` for deterministic outputs
- Only increase if creativity is explicitly needed

---

## Workflow Integration

### Agent Invocation Pattern

In workflows, agents are invoked using:

```yaml
- kind: InvokeAzureAgent
  id: invoke_agent
  agent: <agent-reference>
  input:
    messages:
      - role: user
        content: =<PowerFx expression>
  output:
    messages: Local.agent_response
```

### Output Handling

1. **JSON Schema Responses**: Parse using `ParseValue` node
2. **Messages Table**: Convert to text using `Concat(Local.messages, Text, Char(10))`
3. **Text Responses**: Use directly or accumulate with `Concatenate()`

### Accumulator Pattern

When accumulating agent outputs in loops:

```yaml
# Initialize before loop
- kind: SetVariable
  variable: Local.accumulator
  value: ""

# Inside loop - append
- kind: SetVariable
  variable: Local.accumulator
  value: =Concatenate(Local.accumulator, Local.new_value, Char(10))
```

---

## Troubleshooting

### Common Issues

1. **Agent Not Found**: Ensure agent YAML files are deployed and referenced correctly
2. **JSON Parse Errors**: Check schema structure matches between agent and schema file
3. **Empty Objects in Arrays**: Convert nested objects to parallel arrays
4. **Invalid Argument Type (Table)**: Convert messages table to text before concatenation
5. **Schema Validation Errors**: Ensure `strict: true` and `additionalProperties: false`

### Debugging Tips

1. Use Foundry execution traces to debug data flow
2. Check agent output format matches expected schema
3. Verify Power Fx expressions handle table vs text correctly
4. Test with depth=1, breadth=1 for faster iteration

---

## References

- [Microsoft Foundry Agents Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/)
- [Power Fx Reference](https://learn.microsoft.com/en-us/power-platform/power-fx/overview)
- [JSON Schema Specification](https://json-schema.org/)

