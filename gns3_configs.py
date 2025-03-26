import gns3fy
import requests
import os
from datetime import datetime
from typing import List, Dict

def get_gns3_projects(server_url: str) -> List[Dict]:
    """Connect to GNS3 server and return list of projects"""
    server = gns3fy.Gns3Connector(url=server_url)
    projects = server.projects_summary(is_print=False)
    return [{"name": p[0], "id": p[1]} for p in projects]

def select_project(projects: List[Dict], server_url: str) -> tuple[gns3fy.Project, str]:
    """Display projects and return selected project and its name"""
    print("\nAvailable Projects:")
    for i, project in enumerate(projects, 1):
        print(f"{i}) {project['name']}")
    
    while True:
        try:
            choice = int(input("\nSelect a project number: "))
            if 1 <= choice <= len(projects):
                selected = projects[choice-1]
                project = gns3fy.Project(
                    project_id=selected["id"], 
                    connector=gns3fy.Gns3Connector(url=server_url)
                )
                return project, selected["name"]  # Return both project object and name
            print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a number.")

def display_nodes(project: gns3fy.Project) -> List[gns3fy.Node]:
    """Get and display all nodes in project, return node list"""
    project.get(get_nodes=True)
    print("\nProject Nodes:")
    for i, node in enumerate(project.nodes, 1):
        print(f"{i}) {node.name} (Type: {node.node_type}, Status: {node.status})")
    return project.nodes

def select_nodes(nodes: List[gns3fy.Node]) -> List[gns3fy.Node]:
    """Allow user to select one, multiple, or all nodes"""
    print("\nNode Selection Options:")
    print("Enter number(s) separated by spaces, 'all' for all nodes, or single number")
    selection = input("Select node(s): ").strip().lower()
    
    if selection == "all":
        return nodes
    
    try:
        indices = [int(i)-1 for i in selection.split()]
        return [nodes[i] for i in indices if 0 <= i < len(nodes)]
    except (ValueError, IndexError):
        print("Invalid selection, selecting first node as default")
        return [nodes[0]]

def get_config_filename(server_url: str, project_id: str, node_id: str) -> str:
    """Probe for the correct config filename via API"""
    possible_filenames = ["i1_startup-config.cfg", "i2_startup-config.cfg", "i3_startup-config.cfg"]
    for filename in possible_filenames:
        url = f"{server_url}/v2/projects/{project_id}/nodes/{node_id}/files/configs/{filename}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                print(f"Found config file for node {node_id}: {filename}")
                return filename
        except requests.RequestException:
            continue
    print(f"No config file found for node {node_id}. Tried: {possible_filenames}")
    return None

def save_configs(server_url: str, project_id: str, project_name: str, nodes: List[gns3fy.Node], do_copy_run_start: bool):
    """Download configurations into timestamped/project_name subdirectories with original filenames"""
    if do_copy_run_start:
        print("\nNote: 'copy run start' cannot be executed via API")
        print("Existing startup-config files will be downloaded as-is")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    config_dir = os.path.join(timestamp, project_name)
    os.makedirs(config_dir, exist_ok=True)

    print(f"\nDownloading configurations to {config_dir}...")
    for node in nodes:
        if node.node_type == "dynamips":
            config_filename = get_config_filename(server_url, project_id, node.node_id)
            if not config_filename:
                print(f"Skipping {node.name}: No valid config file found")
                continue
            
            url = f"{server_url}/v2/projects/{project_id}/nodes/{node.node_id}/files/configs/{config_filename}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                local_path = os.path.join(config_dir, config_filename)
                with open(local_path, "w") as f:
                    f.write(response.text)
                print(f"Saved config for {node.name} to {local_path}")
            except requests.RequestException as e:
                print(f"Error downloading config for {node.name}: {e}")

def select_config_directory(project_name: str) -> str:
    """Let user select a timestamped config directory and use project_name subdir"""
    if not os.path.exists("."):
        print("No timestamped directories found. Please download configs first.")
        return None
    
    subdirs = [d for d in os.listdir(".") if os.path.isdir(d) and os.path.isdir(os.path.join(d, project_name))]
    if not subdirs:
        print(f"No timestamped directories with '{project_name}' subdir found. Please download configs first.")
        return None
    
    print("\nAvailable Config Directories:")
    for i, subdir in enumerate(subdirs, 1):
        print(f"{i}) {subdir}")
    
    while True:
        try:
            choice = int(input("\nSelect a directory number: "))
            if 1 <= choice <= len(subdirs):
                return os.path.join(subdirs[choice-1], project_name)
            print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a number.")

def upload_configs(server_url: str, project_id: str, project_name: str, nodes: List[gns3fy.Node], do_reload: bool):
    """Upload configurations from a selected timestamped/project_name directory using GNS3 API"""
    config_dir = select_config_directory(project_name)
    if not config_dir:
        print("Aborting upload due to no valid directory selected.")
        return

    print(f"\nUploading configurations from {config_dir}...")
    for node in nodes:
        if node.node_type == "dynamips":
            config_filename = get_config_filename(server_url, project_id, node.node_id)
            if not config_filename:
                print(f"Skipping {node.name}: No valid config file found")
                continue
            
            local_file = os.path.join(config_dir, config_filename)
            try:
                with open(local_file, "r") as f:
                    config_content = f.read()
            except FileNotFoundError:
                print(f"Local config file not found for {node.name}: {local_file}")
                continue
            
            url = f"{server_url}/v2/projects/{project_id}/nodes/{node.node_id}/files/configs/{config_filename}"
            try:
                response = requests.post(url, data=config_content)
                response.raise_for_status()
                print(f"Uploaded config to {node.name} (to {config_filename}) from {local_file}")
                
                if do_reload:
                    print(f"Reloading {node.name}...")
                    node.reload()
            except requests.RequestException as e:
                print(f"Error uploading config to {node.name}: {e}")

def stop_nodes(nodes: List[gns3fy.Node]):
    """Stop selected nodes"""
    print("\nStopping nodes...")
    for node in nodes:
        if node.node_type == "dynamips":
            try:
                node.stop()
                print(f"Stopped {node.name}")
            except Exception as e:
                print(f"Error stopping {node.name}: {e}")

def start_nodes(nodes: List[gns3fy.Node]):
    """Start selected nodes"""
    print("\nStarting nodes...")
    for node in nodes:
        if node.node_type == "dynamips":
            try:
                node.start()
                print(f"Started {node.name}")
            except Exception as e:
                print(f"Error starting {node.name}: {e}")

def reload_nodes(nodes: List[gns3fy.Node]):
    """Reload selected nodes"""
    print("\nReloading nodes...")
    for node in nodes:
        if node.node_type == "dynamips":
            try:
                node.reload()
                print(f"Reloaded {node.name}")
            except Exception as e:
                print(f"Error reloading {node.name}: {e}")

def main():
    SERVER_URL = "http://localhost:3080"  # GNS3 server on lab
    
    try:
        projects = get_gns3_projects(SERVER_URL)
        if not projects:
            print("No projects found!")
            return
        
        project, project_name = select_project(projects, SERVER_URL)  # Unpack project and name
        nodes = display_nodes(project)
        
        while True:
            print("\nMenu Options:")
            print("1) Download router configurations")
            print("2) Upload router configurations")
            print("3) Stop nodes")
            print("4) Start nodes")
            print("5) Reload nodes")
            print("6) Exit")
            
            choice = input("Select an option (1-6): ").strip()
            
            if choice == "6":
                break
                
            selected_nodes = select_nodes(nodes)
            
            if choice == "1":
                copy_choice = input("\nExecute 'copy run start' first? (y/n): ").lower()
                save_configs(SERVER_URL, project.project_id, project_name, selected_nodes, copy_choice == "y")
                
            elif choice == "2":
                upload_configs(SERVER_URL, project.project_id, project_name, selected_nodes, False)
                reload_choice = input("\nReload routers after upload? (y/n): ").lower()
                if reload_choice == "y":
                    reload_nodes(selected_nodes)
            
            elif choice == "3":
                stop_nodes(selected_nodes)
            
            elif choice == "4":
                start_nodes(selected_nodes)
            
            elif choice == "5":
                reload_nodes(selected_nodes)
            
            else:
                print("Invalid option!")
    except Exception as e:
        print(f"Error connecting to GNS3 server: {e}")
        print("Ensure GNS3 server is running on localhost:3080")

if __name__ == "__main__":
    main()