"""Create or update Azure AI Foundry agents from YAML definitions.

Usage:
    python create_or_update_agents.py

Environment:
    - AZURE_AI_PROJECT_ENDPOINT (preferred) or AZURE_AIPROJECT_ENDPOINT
    - Optional: .env file alongside the repo

This script:
    1. Detects available workflow projects (e.g., msfoundry-deep-research, agentic-rag)
    2. Lets you choose which project's agents to work with
    3. Reads every *.yaml file under the selected project's agents directory
    4. Asks whether to create missing agents, update existing agents, sync, or apply maintenance fixes
    5. Creates/updates agents with model, instructions, tools, and response format
    6. Maintenance: set MCP tools to require_approval='never' or strip temperature/top_p for GPT-5 models
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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


def get_endpoint() -> str:
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT") or os.environ.get("AZURE_AIPROJECT_ENDPOINT")
    if not endpoint:
        raise RuntimeError("Missing AZURE_AI_PROJECT_ENDPOINT (or legacy AZURE_AIPROJECT_ENDPOINT).")
    return endpoint


def detect_workflow_projects() -> List[Tuple[str, Path]]:
    """Detect workflow projects that have an agents directory.
    
    Returns:
        List of tuples (project_name, agents_dir_path) for each detected project.
    """
    projects = []
    
    # Check known workflow project directories
    known_projects = ["msfoundry-deep-research", "agentic-rag"]
    
    for project_name in known_projects:
        agents_dir = PROJECT_ROOT / project_name / "agents"
        if agents_dir.exists() and agents_dir.is_dir():
            projects.append((project_name, agents_dir))
    
    # Also check for legacy location
    legacy_dir = PROJECT_ROOT / "ai-foundry-new" / "agents"
    if legacy_dir.exists() and legacy_dir.is_dir():
        projects.append(("ai-foundry-new (legacy)", legacy_dir))
    
    return projects


def prompt_workflow_selection() -> Optional[Path]:
    """Prompt user to select which workflow project's agents to work with.
    
    Returns:
        Path to the selected agents directory, or None if user quits.
    """
    projects = detect_workflow_projects()
    
    if not projects:
        print("❌ No workflow projects with agents directories found.")
        print(f"   Checked in: {PROJECT_ROOT}")
        return None
    
    print("\nAvailable workflow projects:")
    for idx, (project_name, agents_dir) in enumerate(projects, 1):
        yaml_count = len(list(agents_dir.glob("*.yaml")))
        print(f"  [{idx}] {project_name} ({yaml_count} agent files)")
    print("  [q] Quit")
    
    while True:
        choice = input("Select workflow project (number or 'q' to quit): ").strip().lower()
        if choice == "q":
            return None
        try:
            index = int(choice)
            if 1 <= index <= len(projects):
                selected_name, selected_dir = projects[index - 1]
                print(f"✓ Selected: {selected_name}")
                return selected_dir
            else:
                print(f"Invalid choice. Please enter a number between 1 and {len(projects)}, or 'q'.")
        except ValueError:
            print("Invalid entry. Please enter a number or 'q'.")


def load_agent_files(agents_dir: Path) -> List[Path]:
    """Load agent YAML files from the specified agents directory.
    
    Args:
        agents_dir: Path to the agents directory
        
    Returns:
        List of Path objects for each YAML file
    """
    if not agents_dir.exists():
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


def parse_selection_indices(choice: str, max_index: int) -> Optional[List[int]]:
    """Parse selection input that may include ranges (e.g., '1-6' or '1-3,5,7-9').
    
    Args:
        choice: User input string (e.g., "1-6", "1,2,3", "1-3,5,7-9")
        max_index: Maximum valid index
        
    Returns:
        List of parsed indices (1-based), or None if parsing failed
    """
    parts = [c.strip() for c in choice.split(",") if c.strip()]
    indices = []
    
    for part in parts:
        if "-" in part:
            # Handle range like "1-6"
            range_parts = part.split("-", 1)
            if len(range_parts) != 2:
                return None
            try:
                start = int(range_parts[0].strip())
                end = int(range_parts[1].strip())
                if start > end:
                    return None
                # Expand range (inclusive)
                indices.extend(range(start, end + 1))
            except ValueError:
                return None
        else:
            # Handle single number
            try:
                indices.append(int(part))
            except ValueError:
                return None
    
    # Remove duplicates and sort
    indices = sorted(set(indices))
    
    # Validate all indices are in range
    if indices and (indices[0] < 1 or indices[-1] > max_index):
        return None
    
    return indices


def prompt_agent_selection(agent_payloads: List[Dict]) -> List[Dict]:
    print("\nAgents found in YAML:")
    for idx, info in enumerate(agent_payloads, 1):
        display_name = info.get("name") or "<missing name>"
        print(f"  [{idx}] {display_name} ({info['path'].name})")
    print("  [a] All agents")
    print("  [q] Quit")
    print("  Examples: '1-6' (range), '1,3,5' (individual), '1-3,5,7-9' (mixed)")

    while True:
        choice = input("Select agents by number (comma-separated or range like '1-6'), or 'a' for all, 'q' to quit: ").strip().lower()
        if choice == "q":
            return []
        if choice == "a":
            return agent_payloads
        
        indices = parse_selection_indices(choice, len(agent_payloads))
        if indices is None:
            print("Invalid entry. Use numbers, ranges (e.g., '1-6'), comma-separated values, 'a', or 'q'.")
            continue
        
        selected = [agent_payloads[i - 1] for i in indices]
        if selected:
            return selected
        print("No valid agents selected.")


def prompt_remote_agent_selection(project_client, filter_gpt5_only: bool = False) -> List[str]:
    agents = list(project_client.agents.list())
    if not agents:
        print("❌ No agents found in the project.")
        return []

    # Filter to GPT-5 agents only if requested
    if filter_gpt5_only:
        filtered_agents = []
        print("Filtering agents with GPT-5 models...")
        for agent in agents:
            latest = get_latest_agent_version(project_client, agent.name)
            if latest:
                definition = getattr(latest, "definition", None)
                if definition:
                    model = getattr(definition, "model", None)
                    if is_gpt5_model(model):
                        filtered_agents.append(agent)
        
        if not filtered_agents:
            print("❌ No agents with GPT-5 models found in the project.")
            return []
        
        agents = filtered_agents
        print(f"✓ Found {len(agents)} agent(s) with GPT-5 models")

    print("\nAgents in project:")
    for idx, agent in enumerate(agents, 1):
        print(f"  [{idx}] {agent.name}")
    print("  [a] All agents")
    print("  [q] Quit")
    print("  Examples: '1-6' (range), '1,3,5' (individual), '1-3,5,7-9' (mixed)")

    while True:
        choice = input("Select agents by number (comma-separated or range like '1-6'), or 'a' for all, 'q' to quit: ").strip().lower()
        if choice == "q":
            return []
        if choice == "a":
            return [agent.name for agent in agents]
        
        indices = parse_selection_indices(choice, len(agents))
        if indices is None:
            print("Invalid entry. Use numbers, ranges (e.g., '1-6'), comma-separated values, 'a', or 'q'.")
            continue
        
        selected = [agents[i - 1].name for i in indices]
        if selected:
            return selected
        print("No valid agents selected.")


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

    model = getattr(definition, "model", None)
    if not model:
        print("⚠️  Skip: no model found in definition.")
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
            model=model,
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

    model = getattr(definition, "model", None)
    if not model:
        print("⚠️  Skip: no model found in definition.")
        return

    current_tools = list(getattr(definition, "tools", None) or [])

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
                # For mode 5, filter to only GPT-5 agents
                filter_gpt5 = (mode == "5")
                remote_selection = prompt_remote_agent_selection(project_client, filter_gpt5_only=filter_gpt5)
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
                # Prompt for workflow project selection
                agents_dir = prompt_workflow_selection()
                if not agents_dir:
                    print("👋 Goodbye!")
                    return
                
                agent_files = load_agent_files(agents_dir)
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



