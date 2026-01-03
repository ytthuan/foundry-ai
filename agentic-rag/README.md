# Agentic RAG (Azure AI Foundry Workflow)

This folder contains a minimal **agentic RAG** workflow built for **Azure AI Foundry**. It answers a user question by:
1) deciding whether RAG is needed,
2) planning up to 3 retrieval queries,
3) retrieving chunks from your knowledge store (any vector DB / search backend),
4) reranking chunks,
5) assessing evidence sufficiency + confidence,
6) optionally running a single targeted follow-up retrieval iteration,
7) generating a grounded answer with inline citations.

## High-level architecture

```
User
  │
  ▼
Workflow (OnConversationStart)
  │
  ├─► RagIntentRouterAgent
  │      ├─ if should_run_rag = false → send assistant_message → end
  │      └─ if should_run_rag = true  → continue
  │
  ├─► RagQueryPlanAgent (up to 3 queries + goals + optional filter)
  │
  ├─► For each planned query:
  │      └─► RagRetrieverAgent (calls your retriever backend)
  │             └─ returns chunk_texts + chunk_sources
  │
  ├─► RagRerankAgent (select up to 8 best chunks, dedupe)
  │
  ├─► RagEvidenceAgent (evidence sufficiency + confidence + follow-up queries)
  │      ├─ if is_sufficient = true → continue
  │      └─ if is_sufficient = false → run up to 1 targeted follow-up retrieval loop
  │             ├─► RagRetrieverAgent (for each follow-up query)
  │             └─► RagRerankAgent → RagEvidenceAgent (re-evaluate)
  │
  └─► RagAnswerAgent (final Markdown answer, cites sources)
         └─ output auto-sent to user
```

## Step-by-step flow (request → final answer)

The implementation is in `workflows/current-agentic-rag-workflow.yaml`.

### 0) Initialize variables

The workflow initializes state such as:
- `Local.user_question`, `Local.intent`, `Local.query_plan`
- query-loop counters (`Local.query_index`, `Local.total_queries`)
- retrieval accumulation (`Local.retrieved_context`)
- evidence & retry controls (`Local.evidence`, `Local.retry_count`, `Local.max_retries`)
- final outputs (`Local.rerank`, `Local.final_answer`)

### 1) Ask the user’s question

Action: `Question` → stores user input in `Local.user_question`.

### 2) Route: should we run RAG?

Action: `InvokeAzureAgent` → `RagIntentRouterAgent`

Input built as:
- current date
- raw user message

Output schema: `schemas/rag-intent-router-schema.json`
- `should_run_rag` (boolean)
- `route` (`run_rag` | `no_rag`)
- `assistant_message` (string)

Decision:
- If `should_run_rag` is false, the workflow sends `assistant_message` and ends.
- If `should_run_rag` is true, the workflow continues into retrieval planning.

### 3) Build a retrieval plan (multi-query)

Action: `InvokeAzureAgent` → `RagQueryPlanAgent`

Input:
- `Local.user_question`

Output schema: `schemas/rag-query-plan-schema.json`
- `queries` (0–3 short queries)
- `retrieval_goals` (aligned with `queries`)
- `filter` (string; empty if none)

The workflow sets:
- `Local.current_filter = Coalesce(Local.query_plan.filter, "")`
- `Local.total_queries = CountRows(Local.query_plan.queries)`

### 4) Retrieve chunks (loop over planned queries)

Action group: `ConditionGroup` loop over `Local.query_plan.queries`

For each query:
1) Set `Local.current_query` and aligned `Local.current_goal`.
2) Build `Local.retrieval_input` including:
   - user question
   - current query + retrieval goal
   - optional filter
3) Invoke `RagRetrieverAgent`.

Retriever output schema: `schemas/rag-retrieval-schema.json`
- `query_used`
- `chunk_texts` (up to 20)
- `chunk_sources` (up to 20; aligned)

The workflow then:
- builds `Local.chunk_pairs` (text + source aligned)
- appends each query’s chunks into `Local.retrieved_context` as a text block:
  - includes the executed query
  - enumerates chunks and sources

### 5) Rerank and select the best context

Action: `InvokeAzureAgent` → `RagRerankAgent`

Input:
- `Local.user_question`
- accumulated `Local.retrieved_context`

Rerank output schema: `schemas/rag-rerank-schema.json`
- `selected_chunk_texts` (up to 8)
- `selected_sources` (aligned)
- `selected_rationales` (aligned)
- `missing_info_questions` (0–3)

The reranker is responsible for:
- choosing the most answer-relevant chunks
- reducing redundancy (avoid near-duplicates)
- signaling missing info when retrieval is insufficient

### 6) Evidence assessment (confidence gate)

Action: `InvokeAzureAgent` → `RagEvidenceAgent`

Input:
- `Local.user_question`
- selected chunks + sources from `RagRerankAgent`
- rerank rationales (for extra signal)
- missing-info questions (if any)

Evidence output schema: `schemas/rag-evidence-schema.json`
- `is_sufficient` (boolean)
- `confidence` (0.0–1.0)
- `key_points` + `key_point_sources` (aligned)
- `missing_info_questions` (0–3)
- `followup_queries` + `followup_retrieval_goals` (aligned, 0–3)

Decision:
- If `is_sufficient` is true, proceed to answer generation.
- If `is_sufficient` is false and follow-up queries exist, the workflow performs **one** targeted follow-up retrieval iteration.

### 7) Optional follow-up retrieval (max 1 retry)

Action group: `ConditionGroup` controlled by:
- `Not(Local.evidence.is_sufficient)`
- `Local.retry_count < Local.max_retries` (default `max_retries = 1`)
- follow-up queries exist

Behavior:
- The workflow loops over `Local.evidence.followup_queries` (and aligned `followup_retrieval_goals`).
- Each follow-up retrieval appends additional chunks to the existing `Local.retrieved_context`.
- The workflow reruns `RagRerankAgent` and `RagEvidenceAgent` to re-select and re-assess with the expanded evidence.

### 8) Generate the final answer (grounded + cited)

Action: `InvokeAzureAgent` → `RagAnswerAgent`

Input includes:
- user question
- selected chunks
- selected sources
- evidence assessment (`is_sufficient`, `confidence`)
- any missing-info questions (from the evidence step)

Answer output schema: `schemas/rag-answer-schema.json`
- `answer_markdown`
- `sources` (sources actually cited)

Important behavior:
- The answer agent is instructed to answer **only** from the provided chunks.
- It must cite using the provided sources inline like `[Source]` (where `Source` is one of the strings in `selected_sources`).
- If the chunks are insufficient, it should say what’s missing and ask focused follow-ups.

## What each agent is responsible for

- `agents/rag-intent-router-agent.yaml`
  - Classifies “RAG needed?” vs “no RAG needed”.
  - Produces a safe, short assistant message when not running RAG.

- `agents/rag-query-plan-agent.yaml`
  - Decomposes the user question into up to 3 retrieval queries + goals.
  - Optionally produces an OData filter string (only if user provided explicit constraints).

- `agents/rag-retriever-agent.yaml`
  - Retrieves from your chosen knowledge store (vector DB, search index, doc store).
  - Implementation detail: today this repo models retrieval as an MCP tool call, but the backend is intentionally pluggable.
  - Returns up to 20 diverse chunks with aligned sources.

- `agents/rag-rerank-agent.yaml`
  - Reranks the retrieved context and selects up to 8 best chunks.
  - Outputs missing-info questions if needed.

- `agents/rag-evidence-agent.yaml`
  - Assesses whether the selected evidence is sufficient.
  - Produces a calibrated `confidence` score (0.0–1.0).
  - Extracts grounded `key_points` with aligned `key_point_sources`.
  - If insufficient, proposes up to 3 targeted follow-up retrieval queries + goals.

- `agents/rag-answer-agent.yaml`
  - Writes the final Markdown answer grounded in the selected chunks.
  - Includes inline citations and returns the cited sources.

## Configuration notes (plug in your retriever backend)

The workflow expects `RagRetrieverAgent` to return the JSON shape in `schemas/rag-retrieval-schema.json`:
- `query_used`
- `chunk_texts[]`
- `chunk_sources[]`

How you implement retrieval is up to you:
- MCP tool calling a custom service
- Direct database access (if supported in your environment)
- A thin HTTP API wrapper around VectorChord, MongoDB vector search, Postgres/pgvector, etc.

Azure AI Search Index is also a good fit here (without using “knowledge base” features):
- Vector search: return top-$k$ chunks by embedding similarity.
- Hybrid search: combine vector + keyword for better recall.
- Semantic ranking: apply semantic ranker to improve final ordering when appropriate.
- Filters: the planner’s `filter` string can map naturally to Azure AI Search OData filters.

In the current `agents/rag-retriever-agent.yaml`, retrieval is represented as an MCP tool with placeholder values.

If you keep the MCP approach, replace the placeholders with your environment values:
- `server_label`
- `server_url` (points to your MCP server)
- `project_connection_id`

For how MCP tools and approval/auth work with Foundry agents, see:
- Connect to MCP servers (preview): https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/tools/model-context-protocol?view=foundry-classic
- MCP tool authentication (preview): https://learn.microsoft.com/en-us/azure/ai-foundry/agents/how-to/mcp-authentication?view=foundry

## Files

- `workflows/current-agentic-rag-workflow.yaml`
- `agents/`
- `schemas/`
