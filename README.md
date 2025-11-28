# Deep Research Workflow for Microsoft Foundry

A multi-step, recursive research workflow converted from n8n to Microsoft Foundry format. This workflow replicates functionality similar to OpenAI's DeepResearch feature, using AI agents to perform comprehensive research on complex topics.

---

## 🎯 How It Works (Plain English)

This workflow acts like an AI research assistant that:

1. **Asks what you want to research** and clarifies your needs with follow-up questions
2. **Searches the web** using AI-generated search queries
3. **Learns from what it finds** and digs deeper based on discoveries
4. **Compiles everything** into a detailed research report

Think of it as having a research assistant who:
- Asks smart questions before starting
- Searches multiple sources
- Takes notes on important findings
- Goes back to search for more based on what they learned
- Writes a comprehensive report at the end

---

## 📋 Workflow Flow Diagram (Step-by-Step)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PHASE 1: INITIALIZATION                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────┐         ┌─────────────────────────┐                 │
│   │ Initialize       │         │ Ask User:               │                 │
│   │ Variables:       │────────▶│ "What would you like    │                 │
│   │ • depth = 2      │         │  to research?"          │                 │
│   │ • breadth = 3    │         └───────────┬─────────────┘                 │
│   │ • learnings = [] │                     │                               │
│   │ • iteration = 0  │                     ▼                               │
│   └──────────────────┘         ┌─────────────────────────┐                 │
│                                │ User enters research    │                 │
│                                │ query (e.g., "Sugar     │                 │
│                                │ effect to human brain?")│                 │
│                                └───────────┬─────────────┘                 │
└────────────────────────────────────────────┼────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PHASE 2: CLARIFYING QUESTIONS                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │ 🤖 ClarifyingQuestionsAgent generates up to 3 questions              │ │
│   │                                                                      │ │
│   │ Example output:                                                      │ │
│   │ • "Are you interested in short-term or long-term effects?"          │ │
│   │ • "Do you want to focus on children, adults, or both?"              │ │
│   │ • "Are you looking for dietary recommendations too?"                │ │
│   └───────────────────────────────┬──────────────────────────────────────┘ │
│                                   │                                        │
│                                   ▼                                        │
│   ┌────────────────────────────────────────────────────────────────────┐   │
│   │ FOR EACH question (loop through all 3):                            │   │
│   │                                                                    │   │
│   │   ┌───────────────┐     ┌───────────────┐     ┌────────────────┐  │   │
│   │   │ Show Q1 to    │────▶│ User answers  │────▶│ ACCUMULATE     │  │   │
│   │   │ user          │     │ Q1            │     │ Q1 + A1        │  │   │
│   │   └───────────────┘     └───────────────┘     └───────┬────────┘  │   │
│   │                                                       │           │   │
│   │   ┌───────────────┐     ┌───────────────┐     ┌───────▼────────┐  │   │
│   │   │ Show Q2 to    │────▶│ User answers  │────▶│ ACCUMULATE     │  │   │
│   │   │ user          │     │ Q2            │     │ Q1+A1 + Q2+A2  │  │   │
│   │   └───────────────┘     └───────────────┘     └───────┬────────┘  │   │
│   │                                                       │           │   │
│   │   ┌───────────────┐     ┌───────────────┐     ┌───────▼────────┐  │   │
│   │   │ Show Q3 to    │────▶│ User answers  │────▶│ ACCUMULATE     │  │   │
│   │   │ user          │     │ Q3            │     │ ALL Q&A pairs  │  │   │
│   │   └───────────────┘     └───────────────┘     └───────┬────────┘  │   │
│   │                                                       │           │   │
│   │   ⚠️  KEY: Each answer is APPENDED, not overwritten!             │   │
│   └───────────────────────────────────────────────────────┼───────────┘   │
│                                                           │               │
│                                                           ▼               │
│   ┌──────────────────────────────────────────────────────────────────────┐│
│   │ Build "enrichedQuery" = Original Query + ALL Question/Answer pairs  ││
│   │                                                                      ││
│   │ Example:                                                             ││
│   │ "Initial query: Sugar effect to human brain?                        ││
│   │  Q1: Are you interested in short-term or long-term effects?         ││
│   │  A1: Both, but mainly long-term effects                             ││
│   │  Q2: Do you want to focus on children, adults, or both?             ││
│   │  A2: Adults primarily                                               ││
│   │  Q3: Are you looking for dietary recommendations too?               ││
│   │  A3: Yes, please include recommendations"                           ││
│   └──────────────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────┬────────────────┘
                                                             │
                                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PHASE 3: REPORT INITIALIZATION                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────┐  │
│   │ 🤖 ReportTitleAgent generates title and description                  │ │
│   │                                                                      │ │
│   │ Example output:                                                      │ │
│   │ {                                                                    │ │
│   │   "title": "Long-term Effects of Sugar on Adult Brain Health",      │ │
│   │   "description": "A comprehensive analysis of how sugar             │ │
│   │                   consumption affects cognitive function..."        │ │
│   │ }                                                                    │ │
│   └───────────────────────────────┬──────────────────────────────────────┘ │
│                                   │                                        │
│                                   ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │ 📋 Display: "Research Started - Title: Long-term Effects of..."     │ │
│   └──────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┬────────────────┘
                                                             │
                                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   PHASE 4: RECURSIVE RESEARCH LOOP                          │
│                   (Repeats "depth" times - default 2)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │                        ITERATION 1 of 2                              │ │
│   └───────────────────────────────┬──────────────────────────────────────┘ │
│                                   │                                        │
│   ┌───────────────────────────────▼──────────────────────────────────────┐ │
│   │ 🤖 SERPQueryAgent generates search queries (up to "breadth" = 3)     │ │
│   │                                                                      │ │
│   │ Example output:                                                      │ │
│   │ [                                                                    │ │
│   │   { query: "sugar brain effects long-term adults",                   │ │
│   │     researchGoal: "Find studies on chronic sugar consumption..." },  │ │
│   │   { query: "glucose cognitive function research",                    │ │
│   │     researchGoal: "Explore how glucose affects brain activity..." }, │ │
│   │   { query: "sugar addiction brain dopamine",                         │ │
│   │     researchGoal: "Investigate neurological addiction pathways..." } │ │
│   │ ]                                                                    │ │
│   └───────────────────────────────┬──────────────────────────────────────┘ │
│                                   │                                        │
│   ┌───────────────────────────────▼──────────────────────────────────────┐ │
│   │ FOR EACH search query (loop through all 3):                          │ │
│   │                                                                      │ │
│   │   ┌─────────────────────────────────────────────────────────────┐   │ │
│   │   │ 🔍 WebSearchAgent searches web using Bing                    │   │ │
│   │   │    Query: "sugar brain effects long-term adults"            │   │ │
│   │   │    Returns: Web content from top results                    │   │ │
│   │   └───────────────────────────┬─────────────────────────────────┘   │ │
│   │                               │                                      │ │
│   │   ┌───────────────────────────▼─────────────────────────────────┐   │ │
│   │   │ 📝 LearningsAgent extracts key learnings (max 3)            │   │ │
│   │   │                                                             │   │ │
│   │   │ Example output:                                             │   │ │
│   │   │ {                                                           │   │ │
│   │   │   "learnings": [                                            │   │ │
│   │   │     "A 2023 UCLA study found that high sugar diets          │   │ │
│   │   │      reduce BDNF levels by 35% in adults over 40",          │   │ │
│   │   │     "Chronic sugar consumption is linked to 23%             │   │ │
│   │   │      increased risk of cognitive decline (JAMA, 2022)",     │   │ │
│   │   │     "Sugar triggers dopamine release similar to             │   │ │
│   │   │      addictive substances (NIH research)"                   │   │ │
│   │   │   ],                                                        │   │ │
│   │   │   "follow_up_questions": [                                  │   │ │
│   │   │     "What is the mechanism behind BDNF reduction?",         │   │ │
│   │   │     "Are there reversible effects after reducing sugar?"    │   │ │
│   │   │   ]                                                         │   │ │
│   │   │ }                                                           │   │ │
│   │   └───────────────────────────┬─────────────────────────────────┘   │ │
│   │                               │                                      │ │
│   │   ┌───────────────────────────▼─────────────────────────────────┐   │ │
│   │   │ 📦 ACCUMULATE learnings to all_learnings array              │   │ │
│   │   │                                                             │   │ │
│   │   │ After 3 queries: all_learnings now has ~9 learnings         │   │ │
│   │   └─────────────────────────────────────────────────────────────┘   │ │
│   │                                                                      │ │
│   └──────────────────────────────────────────────────────────────────────┘ │
│                                   │                                        │
│   ┌───────────────────────────────▼──────────────────────────────────────┐ │
│   │ Update enrichedQuery with follow-up questions for next iteration    │ │
│   │ "Previous research goal: ... + Follow-up: What is BDNF mechanism?"  │ │
│   └───────────────────────────────┬──────────────────────────────────────┘ │
│                                   │                                        │
│                                   ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │                        ITERATION 2 of 2                              │ │
│   │                                                                      │ │
│   │ (Same process repeats with MORE SPECIFIC queries based on           │ │
│   │  what was learned in iteration 1)                                   │ │
│   │                                                                      │ │
│   │ Now has: ~18 learnings total                                        │ │
│   └───────────────────────────────┬──────────────────────────────────────┘ │
│                                   │                                        │
│                                   ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │ current_iteration (2) >= depth (2) ✓                                 │ │
│   │ EXIT LOOP → Go to PHASE 5                                            │ │
│   └──────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────┬────────────────┘
                                                             │
                                                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PHASE 5: REPORT GENERATION                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │ 🤖 ReportAgent receives ALL accumulated learnings (~18 items)        │ │
│   │                                                                      │ │
│   │ Generates comprehensive markdown report (3+ pages):                  │ │
│   │ • Executive Summary                                                  │ │
│   │ • Detailed Findings                                                  │ │
│   │ • Tables with metrics                                                │ │
│   │ • Recommendations                                                    │ │
│   │ • Conclusion                                                         │ │
│   └───────────────────────────────┬──────────────────────────────────────┘ │
│                                   │                                        │
│                                   ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │ Add Sources section with all URLs collected                          │ │
│   └───────────────────────────────┬──────────────────────────────────────┘ │
│                                   │                                        │
│                                   ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │ ✅ Display final report to user                                      │ │
│   │                                                                      │ │
│   │ 📊 Research Statistics:                                              │ │
│   │ • Iterations completed: 2                                            │ │
│   │ • Total learnings collected: 18                                      │ │
│   │ • Research depth: 2                                                  │ │
│   │ • Research breadth: 3                                                │ │
│   └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│                              🎉 COMPLETE!                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔑 Key Concept: Accumulator Pattern

The most important technical concept in this workflow is the **accumulator pattern** - ensuring data is **appended** not **overwritten** during loops.

### ❌ Wrong Way (Overwrites):
```yaml
# Inside loop - each iteration OVERWRITES the previous answer
- kind: SetVariable
  variable: Local.answer
  value: =Local.currentAnswer  # Only last answer is kept!
```

### ✅ Correct Way (Accumulates):
```yaml
# Before loop - initialize empty accumulator
- kind: SetVariable
  variable: Local.allAnswers
  value: ""

# Inside loop - APPEND to accumulator
- kind: SetVariable
  variable: Local.allAnswers
  value: =Concatenate(Local.allAnswers, Local.currentAnswer, Char(10))
  # All answers are kept!
```

---

## Overview

The Deep Research workflow performs the following steps:

1. **User Input Collection**: Gathers the research query and configuration (depth/breadth)
2. **Clarifying Questions**: Generates and asks follow-up questions to refine the research direction
3. **Report Initialization**: Creates a title and description for the research report
4. **Recursive Research Loop**:
   - Generates SERP (search) queries based on the topic and accumulated learnings
   - Performs web searches using Bing grounding
   - Extracts key learnings from web content
   - Generates follow-up questions for deeper research
   - Repeats based on depth setting
5. **Report Generation**: Compiles all learnings into a comprehensive markdown report

## File Structure

```
ai-foundry-new/
├── deep-research-workflow.yaml    # Main workflow definition
├── agents/
│   ├── clarifying-questions-agent.yaml  # Generates clarifying questions
│   ├── serp-query-agent.yaml            # Generates search queries
│   ├── learnings-agent.yaml             # Extracts learnings from content
│   ├── report-agent.yaml                # Generates final report
│   ├── report-title-agent.yaml          # Generates report title/description
│   └── web-search-agent.yaml            # Performs web searches
└── schemas/
    ├── clarifying-questions-schema.json
    ├── learnings-schema.json
    ├── report-agent-schema.json
    ├── report-title-schema.json
    ├── serp-queries-schema.json
    └── web-search-agent-schema.json
```

## Prerequisites

### Azure Resources
- Microsoft Foundry project with Azure AI services
- Azure OpenAI deployment (recommended: gpt-4o-mini or gpt-4o)
- Bing Search resource (for web grounding)

### Environment Variables
```bash
AZURE_OPENAI_ENDPOINT=<your-endpoint>
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
```

## Deployment

### Using Microsoft Foundry Portal

1. Sign in to [Microsoft Foundry](https://ai.azure.com)
2. Navigate to your project
3. Select **Build** > **Workflows**
4. Select **Create new workflow** > **Import from YAML**
5. Upload `deep-research-workflow.yaml`
6. Configure agent references to point to deployed agents
7. Save and test the workflow

### Using Azure Developer CLI

```bash
# Install Azure AI Foundry extension
azd extension add ai-foundry

# Deploy the workflow
azd up
```

### Using VS Code Extension

1. Install the [Microsoft Foundry for VS Code](https://marketplace.visualstudio.com/items?itemName=TeamsDevApp.vscode-ai-foundry) extension
2. Open the workflow YAML file
3. Use the visual editor to review and modify
4. Deploy directly from VS Code

## Configuration

### Research Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `depth` | 2 | 1-5 | Number of research iterations |
| `breadth` | 3 | 1-5 | Number of search queries per iteration |

### Estimated Execution Times

| Depth | Breadth | Approximate Time |
|-------|---------|------------------|
| 1 | 2 | 5-10 minutes |
| 2 | 3 | 15-25 minutes |
| 3 | 4 | 45-60 minutes |
| 4-5 | 5 | 2+ hours |

## Workflow Nodes

### Node Types Used

| Node Type | Purpose |
|-----------|---------|
| `AskQuestion` | Collect user input |
| `SendMessage` | Display information to user |
| `SetVariable` | Store and manipulate data |
| `ParseValue` | Parse JSON responses |
| `InvokeAzureAgent` | Call AI agents |
| `If` | Conditional logic |
| `ForEach` | Loop through items |
| `GoTo` | Control flow (recursive loop) |

### Variables

| Variable | Type | Description |
|----------|------|-------------|
| `research_query` | string | Original user query |
| `enriched_research_query` | string | Query enhanced with clarifying answers |
| `all_questions_and_answers` | string | Accumulated Q&A pairs from clarifying questions |
| `depth` | number | Research depth setting (default: 2) |
| `breadth` | number | Research breadth setting (default: 3) |
| `all_learnings` | array | Accumulated learnings from all iterations |
| `all_urls` | array | Source URLs collected |
| `current_iteration` | number | Current loop iteration |
| `latest_followup_questions` | array | Follow-up questions from last learning extraction |

## Agent Descriptions

### ClarifyingQuestionsAgent
Generates follow-up questions to refine the research direction. Outputs JSON with a `questions` array (max 3 questions).

### SERPQueryAgent
Creates web search queries based on the research topic. Each query includes:
- `query`: The search keywords
- `researchGoal`: What this query aims to discover

Uses previous learnings to generate more targeted, specific queries in later iterations.

### WebSearchAgent
Performs web searches using Bing grounding and extracts relevant content from results. Configured with `bing_grounding` tool.

### LearningsAgent
Extracts key learnings from web content. Outputs:
- `learnings`: Array of concise, information-dense findings (max 3)
- `follow_up_questions`: Array of questions for deeper research (max 3)

### ReportAgent
Synthesizes all learnings into a comprehensive markdown report with:
- Executive summary
- Detailed findings
- Tables and metrics
- Recommendations
- Sources

### ReportTitleAgent
Generates a concise title and description for the research report.

## Customization

### Adding Custom Tools

To enhance research capabilities, you can add custom tools to agents:

```yaml
tools:
  - type: bing_grounding
    id: bing_search
  - type: file_search
    id: internal_docs
  - type: function
    id: custom_api
    function:
      name: my_custom_function
      parameters:
        type: object
        properties:
          query:
            type: string
```

### Modifying Agent Instructions

Each agent's instructions can be customized in their respective YAML files. Key areas to modify:

- `instructions`: Main agent behavior and guidelines
- `response_format`: JSON schema for structured outputs
- `settings.temperature`: Creativity level (0.0-1.0)
- `settings.max_tokens`: Maximum response length

## Comparison: n8n vs Microsoft Foundry

| Feature | n8n (Original) | Microsoft Foundry (Converted) |
|---------|----------------|-------------------------------|
| Format | JSON | YAML |
| Execution | Self-hosted/Cloud | Azure-managed |
| AI Integration | OpenAI API | Azure OpenAI |
| Web Search | Apify RAG Browser | Bing Grounding |
| Output Storage | Notion | Azure/Custom |
| Expressions | JavaScript | Power Fx |
| Looping | SplitInBatches node | ForEach + GoTo |
| Subworkflows | Execute Workflow node | Inline with GoTo targets |

## Troubleshooting

### Common Issues

1. **Only seeing one clarifying question answered**: Make sure the workflow uses the accumulator pattern - initialize `all_questions_and_answers` before the loop, then `Concatenate()` inside the loop.

2. **Agent not found**: Ensure agent YAML files are deployed and referenced correctly with `ref: agents/agent-name.yaml`

3. **Timeout errors**: Reduce depth/breadth or increase timeout settings

4. **Web search fails**: Verify Bing Search resource is configured in your Foundry project

5. **JSON parse errors**: Check agent response format configuration and ensure `strict: true` in JSON schemas

### Debugging

Enable verbose logging in Foundry portal:
1. Navigate to workflow execution history
2. Select failed execution
3. View step-by-step trace with inputs/outputs

## References

- [Microsoft Foundry Workflows Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/concepts/workflow)
- [Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/)
- [Power Fx Reference](https://learn.microsoft.com/en-us/power-platform/power-fx/overview)
- [Original n8n DeepResearch Template](https://n8n.io/workflows/)

## License

This workflow is provided as a reference implementation. Adapt as needed for your specific use case.

---

## Sample Question

Try the workflow with this sample research query:

Sugar effect to human brain?