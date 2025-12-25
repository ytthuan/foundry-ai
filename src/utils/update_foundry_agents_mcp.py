#!/usr/bin/env python3
"""
Script to update Azure AI agents with common fixes:
1. Update MCP tool to require_approval: never (auto-approve MCP tool calls)
2. Remove temperature/top_p parameters for GPT-5 models (which don't support them)

Only requires the project endpoint - preserves all other agent settings
"""

import os
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, MCPTool
from dotenv import load_dotenv

load_dotenv()

# Set your endpoint - Update this with your actual endpoint
ENDPOINT = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "")


def list_agents(project_client):
    """List all agents in the project"""
    print("\n📋 Fetching agents...")
    agents = project_client.agents.list()
    agent_list = list(agents)
    
    if not agent_list:
        print("❌ No agents found in this project.")
        return None
    
    print("\n" + "="*60)
    print("Available Agents:")
    print("="*60)
    
    for idx, agent in enumerate(agent_list, 1):
        print(f"\n  [{idx}] {agent.name}")
        print(f"      ID: {agent.id}")
        if hasattr(agent, 'description') and agent.description:
            print(f"      Description: {agent.description[:50]}...")
    
    print("\n" + "="*60)
    return agent_list


def get_agent_details(project_client, agent_name):
    """Get the latest version of an agent with full details"""
    versions = project_client.agents.list_versions(agent_name=agent_name)
    version_list = list(versions)
    
    if not version_list:
        return None
    
    # Get the latest version (highest version number)
    latest = max(version_list, key=lambda x: int(x.version) if x.version.isdigit() else 0)
    return latest


def find_mcp_tools(agent):
    """Find MCP tools in the agent's tool configuration"""
    mcp_tools = []
    
    if hasattr(agent, 'definition') and agent.definition:
        definition = agent.definition
        if hasattr(definition, 'tools') and definition.tools:
            for idx, tool in enumerate(definition.tools):
                # Check if it's an MCP tool
                if hasattr(tool, 'server_label') or (isinstance(tool, dict) and tool.get('type') == 'mcp'):
                    mcp_tools.append((idx, tool))
    
    return mcp_tools


def is_gpt5_model(model_name):
    """Check if the model is a GPT-5 variant that doesn't support temperature"""
    if not model_name:
        return False
    return 'gpt-5' in model_name.lower()


def update_agent_mcp_approval(project_client, agent):
    """Update the agent's MCP tools to have require_approval='never'"""
    
    if not hasattr(agent, 'definition') or not agent.definition:
        print("❌ Agent has no definition to update.")
        return None
    
    definition = agent.definition
    
    # Get current tools
    current_tools = list(definition.tools) if hasattr(definition, 'tools') and definition.tools else []
    
    if not current_tools:
        print("❌ Agent has no tools configured.")
        return None
    
    # Find and update MCP tools
    updated_tools = []
    mcp_updated = False
    
    for tool in current_tools:
        if hasattr(tool, 'server_label'):  # It's an MCP tool
            # Create new MCP tool with require_approval='never'
            new_mcp_tool = MCPTool(
                server_label=tool.server_label,
                server_url=tool.server_url if hasattr(tool, 'server_url') and tool.server_url is not None else "",
                require_approval="never",
                project_connection_id=tool.project_connection_id if hasattr(tool, 'project_connection_id') else None,
                allowed_tools=tool.allowed_tools if hasattr(tool, 'allowed_tools') else None,
            )
            updated_tools.append(new_mcp_tool)
            mcp_updated = True
            print(f"   ✅ Updated MCP tool: {tool.server_label}")
        else:
            # Keep other tools as-is
            updated_tools.append(tool)
    
    if not mcp_updated:
        print("❌ No MCP tools found in this agent.")
        return None
    
    # Create new version with updated tools
    print(f"\n🚀 Creating new version of agent: {agent.name}...")
    
    new_agent = project_client.agents.create_version(
        agent_name=agent.name,
        definition=PromptAgentDefinition(
            model=definition.model if hasattr(definition, 'model') and definition.model is not None else "",
            instructions=definition.instructions if hasattr(definition, 'instructions') else None,
            tools=updated_tools,
            temperature=definition.temperature if hasattr(definition, 'temperature') else None,
            top_p=definition.top_p if hasattr(definition, 'top_p') else None,
        ),
    )
    
    return new_agent


def remove_temperature_for_gpt5(project_client, agent):
    """Remove temperature parameter for agents using GPT-5 models (which don't support it)"""
    
    if not hasattr(agent, 'definition') or not agent.definition:
        print("❌ Agent has no definition to update.")
        return None
    
    definition = agent.definition
    model_name = definition.model if hasattr(definition, 'model') else ""
    
    # Get current tools
    current_tools = list(definition.tools) if hasattr(definition, 'tools') and definition.tools else []
    
    # Create new version without temperature (set to None explicitly)
    print(f"\n🚀 Creating new version of agent: {agent.name} (removing temperature/top_p)...")
    
    new_agent = project_client.agents.create_version(
        agent_name=agent.name,
        definition=PromptAgentDefinition(
            model=model_name,
            instructions=definition.instructions if hasattr(definition, 'instructions') else None,
            tools=current_tools if current_tools else None,
            temperature=None,  # Remove temperature for GPT-5
            top_p=None,  # Also remove top_p as it may have similar issues
        ),
    )
    
    return new_agent


def main():
    if not ENDPOINT:
        print("❌ Error: AZURE_AI_PROJECT_ENDPOINT environment variable is not set.")
        print("   Please set it in your .env file or environment.")
        return
    
    print("🔐 Authenticating with Azure...")
    credential = DefaultAzureCredential()
    
    print(f"📡 Connecting to: {ENDPOINT}")
    
    with AIProjectClient(endpoint=ENDPOINT, credential=credential) as project_client:
        
        # List all agents
        agent_list = list_agents(project_client)
        
        if not agent_list:
            return
        
        # Main loop - keep running until user quits
        while True:
            # Ask user to select an agent
            while True:
                try:
                    selection = input("\n👉 Enter the number of the agent to update (or 'q' to quit): ").strip()
                    
                    if selection.lower() == 'q':
                        print("👋 Goodbye!")
                        return
                    
                    idx = int(selection) - 1
                    if 0 <= idx < len(agent_list):
                        selected_agent = agent_list[idx]
                        break
                    else:
                        print(f"❌ Please enter a number between 1 and {len(agent_list)}")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            print(f"\n📖 Getting details for agent: {selected_agent.name}...")
            
            # Get full agent details with latest version
            agent_details = get_agent_details(project_client, selected_agent.name)
            
            if not agent_details:
                print(f"❌ Could not retrieve details for agent: {selected_agent.name}")
                print("   Returning to agent list...\n")
                continue
            
            print(f"   Current version: {agent_details.version}")
            
            # Show agent model info
            model_name = ""
            if hasattr(agent_details, 'definition') and agent_details.definition:
                model_name = agent_details.definition.model if hasattr(agent_details.definition, 'model') else ""
                print(f"   Model: {model_name}")
            
            # Show action menu
            print("\n" + "-"*40)
            print("Available Actions:")
            print("-"*40)
            print("  [1] Update MCP tools (set require_approval='never')")
            print("  [2] Remove temperature parameter (for GPT-5 models)")
            print("  [0] Back to agent list")
            print("-"*40)
            
            action = input("\n👉 Select action: ").strip()
            
            if action == '0':
                print("   Returning to agent list...\n")
                continue
            
            elif action == '1':
                # Find MCP tools
                mcp_tools = find_mcp_tools(agent_details)
                
                if not mcp_tools:
                    print(f"\n❌ No MCP tools found in agent: {selected_agent.name}")
                    print("   Returning to agent list...\n")
                    continue
                
                print(f"\n🔧 Found {len(mcp_tools)} MCP tool(s):")
                for idx, tool in mcp_tools:
                    label = tool.server_label if hasattr(tool, 'server_label') else 'unknown'
                    current_approval = getattr(tool, 'require_approval', 'not set')
                    print(f"   - {label} (current require_approval: {current_approval})")
                
                # Confirm update
                confirm = input(f"\n⚠️  Update MCP tools to require_approval='never'? (y/n): ").strip().lower()
                
                if confirm != 'y':
                    print("❌ Update cancelled.")
                    print("   Returning to agent list...\n")
                    continue
                
                # Update the agent
                print("\n🔄 Updating agent...")
                new_agent = update_agent_mcp_approval(project_client, agent_details)
                
                if new_agent:
                    print(f"\n✅ Agent updated successfully!")
                    print(f"   - Name: {new_agent.name}")
                    print(f"   - New Version: {new_agent.version}")
                    print(f"   - MCP tools now have require_approval='never'")
                else:
                    print("\n❌ Failed to update agent.")
            
            elif action == '2':
                # Check if it's a GPT-5 model
                if not is_gpt5_model(model_name):
                    print(f"\n⚠️  Warning: Agent model '{model_name}' doesn't appear to be a GPT-5 model.")
                    force = input("   Do you still want to remove temperature? (y/n): ").strip().lower()
                    if force != 'y':
                        print("❌ Update cancelled.")
                        print("   Returning to agent list...\n")
                        continue
                
                # Show current temperature
                current_temp = None
                current_top_p = None
                if hasattr(agent_details, 'definition') and agent_details.definition:
                    current_temp = agent_details.definition.temperature if hasattr(agent_details.definition, 'temperature') else None
                    current_top_p = agent_details.definition.top_p if hasattr(agent_details.definition, 'top_p') else None
                
                print(f"\n📊 Current parameters:")
                print(f"   - temperature: {current_temp}")
                print(f"   - top_p: {current_top_p}")
                
                if current_temp is None and current_top_p is None:
                    print("\nℹ️  Agent already has no temperature/top_p parameters set.")
                    print("   Returning to agent list...\n")
                    continue
                
                # Confirm update
                confirm = input(f"\n⚠️  Remove temperature and top_p parameters? (y/n): ").strip().lower()
                
                if confirm != 'y':
                    print("❌ Update cancelled.")
                    print("   Returning to agent list...\n")
                    continue
                
                # Remove temperature
                print("\n🔄 Updating agent...")
                new_agent = remove_temperature_for_gpt5(project_client, agent_details)
                
                if new_agent:
                    print(f"\n✅ Agent updated successfully!")
                    print(f"   - Name: {new_agent.name}")
                    print(f"   - New Version: {new_agent.version}")
                    print(f"   - Temperature and top_p parameters removed")
                else:
                    print("\n❌ Failed to update agent.")
            
            else:
                print("❌ Invalid action. Please try again.")
                continue
            
            # Ask if user wants to continue
            another = input("\n🔄 Update another agent? (y/n): ").strip().lower()
            if another != 'y':
                print("👋 Goodbye!")
                return
            
            # Refresh agent list
            print("\n" + "="*60)
            agent_list = list_agents(project_client)
            if not agent_list:
                return


if __name__ == "__main__":
    main()
