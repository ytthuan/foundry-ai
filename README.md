# Microsoft Foundry Workflows

This repository contains multiple Microsoft Foundry workflow projects demonstrating advanced AI agent patterns and implementations.

## Projects

### [msfoundry-deep-research](./msfoundry-deep-research/)

A multi-step, recursive research workflow that replicates functionality similar to OpenAI's DeepResearch feature. Uses AI agents to perform comprehensive research on complex topics through iterative web searches, learning extraction, and report generation.

**Key Features:**
- Clarifying questions to refine research scope
- Recursive research loops with configurable depth and breadth
- Web search integration using Bing grounding
- Comprehensive markdown report generation

📖 **[Read the Deep Research Documentation →](./msfoundry-deep-research/README.md)**

---

### [agentic-rag](./agentic-rag/)

An agentic RAG (Retrieval-Augmented Generation) workflow that answers user questions by intelligently routing queries, planning retrieval strategies, retrieving and reranking chunks, assessing evidence sufficiency, and generating grounded answers with citations.

**Key Features:**
- Intent routing to determine if RAG is needed
- Multi-query retrieval planning
- Evidence sufficiency assessment
- Follow-up retrieval iterations when needed
- Grounded answers with inline citations

📖 **[Read the Agentic RAG Documentation →](./agentic-rag/README.md)**

---

## Repository Structure

```
foundry-ai/
├── msfoundry-deep-research/     # Deep research workflow project
│   ├── agents/                  # Agent definitions (YAML)
│   ├── schemas/                 # JSON schemas for agent responses
│   ├── workflows/               # Workflow definitions (YAML)
│   └── README.md               # Project-specific documentation
│
├── agentic-rag/                 # Agentic RAG workflow project
│   ├── agents/                  # Agent definitions (YAML)
│   ├── schemas/                 # JSON schemas for agent responses
│   ├── workflows/               # Workflow definitions (YAML)
│   └── README.md               # Project-specific documentation
│
├── src/
│   └── utils/
│       └── create_or_update_agents.py  # Utility for deploying agents
│
├── AGENTS.md                    # Comprehensive agent documentation
├── .github/
│   └── copilot-instructions.md  # Development guidelines
└── README.md                    # This file
```

## Common Patterns

All projects in this repository follow consistent patterns established in the canonical `msfoundry-deep-research` project:

- **Agent Structure**: YAML-based agent definitions with strict JSON schemas
- **Schema Rules**: Strict mode enabled, parallel arrays instead of nested objects
- **Workflow Patterns**: Power Fx expressions, accumulator patterns, loop handling
- **Model Selection**: `gpt-5-nano` for simple tasks, `model-router` for complex reasoning

For detailed information about agent patterns and conventions, see:
- **[AGENTS.md](./AGENTS.md)** - Comprehensive agent documentation
- **[.github/copilot-instructions.md](./.github/copilot-instructions.md)** - Development guidelines

## Prerequisites

### Azure Resources
- Microsoft Foundry project with Azure AI services
- Azure OpenAI deployment (recommended: gpt-4o-mini or gpt-4o)
- Bing Search resource (for deep research workflows)
- Azure AI Search Index (for RAG workflows)

### Environment Variables
```bash
AZURE_AI_PROJECT_ENDPOINT=<your-foundry-endpoint>
# or
AZURE_AIPROJECT_ENDPOINT=<your-foundry-endpoint>
```

## Deployment

### Deploy Agents

Use the utility script to deploy all agents:

```bash
source .venv/bin/activate && python3 src/utils/create_or_update_agents.py
```

### Deploy Workflows

1. Sign in to [Microsoft Foundry](https://ai.azure.com)
2. Navigate to your project
3. Select **Build** > **Workflows**
4. Select **Create new workflow** > **Import from YAML**
5. Upload the workflow YAML file from the respective project directory
6. Configure agent references to point to deployed agents
7. Save and test the workflow

## Documentation

- **[AGENTS.md](./AGENTS.md)** - Complete documentation for all agents across all projects
- **[msfoundry-deep-research/README.md](./msfoundry-deep-research/README.md)** - Deep research workflow documentation
- **[agentic-rag/README.md](./agentic-rag/README.md)** - Agentic RAG workflow documentation
- **[.github/copilot-instructions.md](./.github/copilot-instructions.md)** - Development guidelines and patterns

## References

- [Microsoft Foundry Workflows Documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/concepts/workflow)
- [Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/)
- [Power Fx Reference](https://learn.microsoft.com/en-us/power-platform/power-fx/overview)

## License

This repository contains reference implementations. Adapt as needed for your specific use case.

