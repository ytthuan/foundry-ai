"""Create or update Azure AI Foundry agents from YAML definitions.

Usage:
    python create_or_update_agents.py

Environment:
    - AZURE_AI_PROJECT_ENDPOINT (preferred) or AZURE_AIPROJECT_ENDPOINT
    - Optional: .env file alongside the repo

This script:
    1. Reads every *.yaml file under ai-foundry-new/agents
    2. Asks whether to create missing agents, update existing agents, or sync (create or update)
    3. Creates/updates agents with model, instructions, tools, and response format
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    MCPTool,
    PromptAgentDefinition,
    WebSearchPreviewTool,
)
from dotenv import load_dotenv


load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = PROJECT_ROOT / "ai-foundry-new" / "agents"


def get_endpoint() -> str:
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT") or os.environ.get("AZURE_AIPROJECT_ENDPOINT")
    if not endpoint:
        raise RuntimeError("Missing AZURE_AI_PROJECT_ENDPOINT (or legacy AZURE_AIPROJECT_ENDPOINT).")
    return endpoint


def load_agent_files() -> List[Path]:
    if not AGENTS_DIR.exists():
        raise FileNotFoundError(f"Agents directory not found: {AGENTS_DIR}")
    files = sorted(AGENTS_DIR.glob("*.yaml"))
    if not files:
        raise FileNotFoundError(f"No YAML files found in {AGENTS_DIR}")
    return files


def parse_agent_yaml(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_agent_payloads(files: List[Path]) -> List[Dict]:
    payloads = []
    for path in files:
        payload = parse_agent_yaml(path)
        agent_name = payload.get("name") if isinstance(payload, dict) else None
        payloads.append({"path": path, "payload": payload, "name": agent_name})
    return payloads


def build_tools(tool_defs: Optional[List[Dict]]) -> Optional[List]:
    if not tool_defs:
        return None

    tools = []
    for tool in tool_defs:
        tool_type = tool.get("type") if isinstance(tool, dict) else None
        if tool_type == "web_search_preview":
            tools.append(WebSearchPreviewTool())
        elif tool_type == "mcp":
            tools.append(
                MCPTool(
                    server_label=tool.get("server_label", ""),
                    server_url=tool.get("server_url", ""),
                    project_connection_id=tool.get("project_connection_id"),
                    allowed_tools=tool.get("allowed_tools"),
                    require_approval=tool.get("require_approval"),
                )
            )
        else:
            # Fallback to raw dict so the SDK can attempt to serialize it
            tools.append(tool)

    return tools if tools else None


def build_definition(def_block: Dict) -> PromptAgentDefinition:
    tools = build_tools(def_block.get("tools"))
    kwargs = {
        "kind": def_block.get("kind", "prompt"),
        "model": def_block.get("model"),
        "instructions": def_block.get("instructions"),
        "temperature": def_block.get("temperature"),
        "top_p": def_block.get("top_p"),
        "tools": tools,
        # Pass through text/response format if present; SDK accepts dicts for models
        "text": def_block.get("text"),
    }

    # Drop None values so we only send fields that exist in YAML
    filtered = {k: v for k, v in kwargs.items() if v is not None}
    return PromptAgentDefinition(**filtered)


def prompt_mode() -> str:
    print("\nSelect mode:")
    print("  [1] Create missing agents only")
    print("  [2] Update existing agents only")
    print("  [3] Sync all (create missing, update existing)")
    print("  [q] Quit")
    while True:
        choice = input("Enter choice (1/2/3/q): ").strip()
        if choice.lower() == "q":
            return "q"
        if choice in {"1", "2", "3"}:
            return choice
        print("Invalid choice. Please enter 1, 2, 3, or q to quit.")


def prompt_agent_selection(agent_payloads: List[Dict]) -> List[Dict]:
    print("\nAgents found in YAML:")
    for idx, info in enumerate(agent_payloads, 1):
        display_name = info.get("name") or "<missing name>"
        print(f"  [{idx}] {display_name} ({info['path'].name})")
    print("  [a] All agents")
    print("  [q] Quit")

    while True:
        choice = input("Select agents by number (comma-separated), or 'a' for all, 'q' to quit: ").strip().lower()
        if choice == "q":
            return []
        if choice == "a":
            return agent_payloads
        parts = [c.strip() for c in choice.split(",") if c.strip()]
        indices = []
        try:
            for part in parts:
                indices.append(int(part))
        except ValueError:
            print("Invalid entry. Use numbers, 'a', or 'q'.")
            continue
        selected = []
        for i in indices:
            if 1 <= i <= len(agent_payloads):
                selected.append(agent_payloads[i - 1])
            else:
                print(f"Index out of range: {i}")
                selected = []
                break
        if selected:
            return selected


def list_existing_agents(project_client) -> Dict[str, str]:
    return {agent.name: agent.id for agent in project_client.agents.list()}


def process_agent(project_client, mode: str, agent_payload: Dict, path: Path, existing: Dict[str, str]):
    agent_name = agent_payload.get("name")
    description = agent_payload.get("description") or agent_payload.get("metadata", {}).get("description")
    definition_block = agent_payload.get("definition")

    if not agent_name or not definition_block:
        print(f"⚠️  Skipping {path.name}: missing name or definition")
        return

    definition = build_definition(definition_block)

    agent_exists = agent_name in existing
    if mode == "1" and agent_exists:
        print(f"➡️  Skip (exists): {agent_name}")
        return
    if mode == "2" and not agent_exists:
        print(f"➡️  Skip (missing): {agent_name}")
        return

    if agent_exists:
        print(f"🔄 Updating agent '{agent_name}' from {path.name}...")
        new_version = project_client.agents.create_version(
            agent_name=agent_name,
            definition=definition,
            description=description,
        )
        print(f"   ✅ Updated to version {new_version.version}")
    else:
        print(f"🆕 Creating agent '{agent_name}' from {path.name}...")
        created = project_client.agents.create(
            name=agent_name,
            definition=definition,
            description=description,
        )
        print(f"   ✅ Created with version {created.version}")


def main():
    try:
        endpoint = get_endpoint()
    except RuntimeError as err:
        print(f"❌ {err}")
        return

    agent_files = load_agent_files()
    agent_payloads = load_agent_payloads(agent_files)

    credential = DefaultAzureCredential()

    while True:
        mode = prompt_mode()
        if mode == "q":
            print("👋 Goodbye!")
            return
        selection = prompt_agent_selection(agent_payloads)
        if not selection:
            print("👋 Goodbye!")
            return

        with AIProjectClient(endpoint=endpoint, credential=credential) as project_client:
            existing_agents = list_existing_agents(project_client)
            for info in selection:
                process_agent(project_client, mode, info["payload"], info["path"], existing_agents)

        again = input("\nRun another operation? (y/n): ").strip().lower()
        if again != "y":
            print("👋 Goodbye!")
            return


if __name__ == "__main__":
    main()



