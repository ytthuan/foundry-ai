"""Create or update Azure AI Foundry agents from YAML definitions.

Usage:
    python create_or_update_agents.py

Environment:
    - AZURE_AI_PROJECT_ENDPOINT (preferred) or AZURE_AIPROJECT_ENDPOINT
    - Optional: .env file alongside the repo

This script:
    1. Reads every *.yaml file under msfoundry-deep-research/agents
    2. Asks whether to create missing agents, update existing agents, sync, or apply maintenance fixes
    3. Creates/updates agents with model, instructions, tools, and response format
    4. Maintenance: set MCP tools to require_approval='never' or strip temperature/top_p for GPT-5 models
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
AGENTS_DIR = PROJECT_ROOT / "msfoundry-deep-research" / "agents"


def get_endpoint() -> str:
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT") or os.environ.get("AZURE_AIPROJECT_ENDPOINT")
    if not endpoint:
        raise RuntimeError("Missing AZURE_AI_PROJECT_ENDPOINT (or legacy AZURE_AIPROJECT_ENDPOINT).")
    return endpoint


def load_agent_files() -> List[Path]:
    agents_dir = AGENTS_DIR
    if not agents_dir.exists():
        legacy = PROJECT_ROOT / "ai-foundry-new" / "agents"
        if legacy.exists():
            agents_dir = legacy
        else:
            raise FileNotFoundError(f"Agents directory not found: {agents_dir}")
    files = sorted(agents_dir.glob("*.yaml"))
    if not files:
        raise FileNotFoundError(f"No YAML files found in {agents_dir}")
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
    print("  [4] Update MCP tools (require_approval='never')")
    print("  [5] Remove temperature/top_p for GPT-5 models")
    print("  [q] Quit")
    while True:
        choice = input("Enter choice (1/2/3/4/5/q): ").strip()
        if choice.lower() == "q":
            return "q"
        if choice in {"1", "2", "3", "4", "5"}:
            return choice
        print("Invalid choice. Please enter 1, 2, 3, 4, 5, or q to quit.")


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


def prompt_remote_agent_selection(project_client) -> List[str]:
    agents = list(project_client.agents.list())
    if not agents:
        print("❌ No agents found in the project.")
        return []

    print("\nAgents in project:")
    for idx, agent in enumerate(agents, 1):
        print(f"  [{idx}] {agent.name}")
    print("  [a] All agents")
    print("  [q] Quit")

    while True:
        choice = input("Select agents by number (comma-separated), or 'a' for all, 'q' to quit: ").strip().lower()
        if choice == "q":
            return []
        if choice == "a":
            return [agent.name for agent in agents]
        parts = [c.strip() for c in choice.split(",") if c.strip()]
        indices: List[int] = []
        try:
            for part in parts:
                indices.append(int(part))
        except ValueError:
            print("Invalid entry. Use numbers, 'a', or 'q'.")
            continue
        selected: List[str] = []
        for i in indices:
            if 1 <= i <= len(agents):
                selected.append(agents[i - 1].name)
            else:
                print(f"Index out of range: {i}")
                selected = []
                break
        if selected:
            return selected


def list_existing_agents(project_client: AIProjectClient) -> Dict[str, str]:
    return {agent.name: agent.id for agent in project_client.agents.list()}


def get_latest_agent_version(project_client: AIProjectClient, agent_name: str):
    versions = list(project_client.agents.list_versions(agent_name=agent_name))
    if not versions:
        return None

    def version_key(version):
        try:
            return int(version.version)
        except (TypeError, ValueError):
            return -1

    return max(versions, key=version_key)


def find_mcp_tools(definition) -> List:
    tools = getattr(definition, "tools", None)
    if not tools:
        return []

    return [
        (idx, tool)
        for idx, tool in enumerate(tools)
        if hasattr(tool, "server_label") or (isinstance(tool, dict) and tool.get("type") == "mcp")
    ]


def is_gpt5_model(model_name: Optional[str]) -> bool:
    return bool(model_name and "gpt-5" in model_name.lower())


def update_mcp_tools_to_auto_approve(project_client: AIProjectClient, agent_details):
    definition = getattr(agent_details, "definition", None)
    if not definition:
        print("⚠️  Skip: no definition available.")
        return

    current_tools = list(getattr(definition, "tools", None) or [])
    updated_tools = []
    changed = False

    for tool in current_tools:
        if hasattr(tool, "server_label") or (isinstance(tool, dict) and tool.get("type") == "mcp"):
            updated_tools.append(
                MCPTool(
                    server_label=getattr(tool, "server_label", ""),
                    server_url=getattr(tool, "server_url", ""),
                    project_connection_id=getattr(tool, "project_connection_id", None),
                    allowed_tools=getattr(tool, "allowed_tools", None),
                    require_approval="never",
                )
            )
            changed = True
        else:
            updated_tools.append(tool)

    if not changed:
        print("➡️  Skip: no MCP tools to update.")
        return

    new_version = project_client.agents.create_version(
        agent_name=agent_details.name,
        definition=PromptAgentDefinition(
            kind=getattr(definition, "kind", None),
            model=getattr(definition, "model", None),
            instructions=getattr(definition, "instructions", None),
            tools=updated_tools or None,
            temperature=getattr(definition, "temperature", None),
            top_p=getattr(definition, "top_p", None),
            text=getattr(definition, "text", None),
        ), # type: ignore
        description=getattr(agent_details, "description", None),
    )

    print(f"   ✅ MCP tools updated; new version {new_version.version}")


def remove_temperature_params(project_client: AIProjectClient, agent_details):
    definition = getattr(agent_details, "definition", None)
    if not definition:
        print("⚠️  Skip: no definition available.")
        return

    current_tools = list(getattr(definition, "tools", None) or [])
    model = getattr(definition, "model", None)

    new_version = project_client.agents.create_version(
        agent_name=agent_details.name,
        definition=PromptAgentDefinition(
            kind=getattr(definition, "kind", None),
            model=model,
            instructions=getattr(definition, "instructions", None),
            tools=current_tools or None,
            temperature=None,
            top_p=None,
            text=getattr(definition, "text", None),
        ), # type: ignore
        description=getattr(agent_details, "description", None),
    )

    print(f"   ✅ Temperature/top_p removed; new version {new_version.version}")


def process_agent(project_client: AIProjectClient, mode: str, agent_payload: Dict, path: Path, existing: Dict[str, str]):
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
        print(f"   ✅ Created with version {created.versions.get('version', 'N/A')}")


def process_mcp_auto_approval(project_client: AIProjectClient, agent_name: str, existing: Dict[str, str]):
    if not agent_name:
        print("⚠️  Skipping entry without agent name.")
        return
    if agent_name not in existing:
        print(f"➡️  Skip (missing remotely): {agent_name}")
        return

    latest = get_latest_agent_version(project_client, agent_name)
    if not latest:
        print(f"⚠️  Unable to fetch versions for {agent_name}")
        return

    if not find_mcp_tools(getattr(latest, "definition", None)):
        print(f"➡️  Skip (no MCP tools): {agent_name}")
        return

    print(f"🔄 Updating MCP tools for '{agent_name}'...")
    update_mcp_tools_to_auto_approve(project_client, latest)


def process_temperature_removal(project_client: AIProjectClient, agent_name: str, existing: Dict[str, str]):
    if not agent_name:
        print("⚠️  Skipping entry without agent name.")
        return
    if agent_name not in existing:
        print(f"➡️  Skip (missing remotely): {agent_name}")
        return

    latest = get_latest_agent_version(project_client, agent_name)
    if not latest:
        print(f"⚠️  Unable to fetch versions for {agent_name}")
        return

    model_name = getattr(getattr(latest, "definition", None), "model", None)
    if not is_gpt5_model(model_name):
        print(f"ℹ️  {agent_name}: model '{model_name}' is not GPT-5; removing temperature/top_p anyway.")

    print(f"🔄 Removing temperature/top_p for '{agent_name}'...")
    remove_temperature_params(project_client, latest)


def main():
    try:
        endpoint = get_endpoint()
    except RuntimeError as err:
        print(f"❌ {err}")
        return

    credential = DefaultAzureCredential()

    while True:
        mode = prompt_mode()
        if mode == "q":
            print("👋 Goodbye!")
            return

        with AIProjectClient(endpoint=endpoint, credential=credential) as project_client:
            if mode in {"4", "5"}:
                remote_selection = prompt_remote_agent_selection(project_client)
                if not remote_selection:
                    print("👋 Goodbye!")
                    return
                existing_agents = list_existing_agents(project_client)
                for agent_name in remote_selection:
                    if mode == "4":
                        process_mcp_auto_approval(project_client, agent_name, existing_agents)
                    else:
                        process_temperature_removal(project_client, agent_name, existing_agents)
            else:
                agent_files = load_agent_files()
                agent_payloads = load_agent_payloads(agent_files)
                selection = prompt_agent_selection(agent_payloads)
                if not selection:
                    print("👋 Goodbye!")
                    return
                existing_agents = list_existing_agents(project_client)
                for info in selection:
                    process_agent(project_client, mode, info["payload"], info["path"], existing_agents)

        again = input("\nRun another operation? (y/n): ").strip().lower()
        if again != "y":
            print("👋 Goodbye!")
            return


if __name__ == "__main__":
    main()



