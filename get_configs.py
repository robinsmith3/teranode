# project_id = "b9239bf1-5d1d-4f74-88de-c04171ac1e8a"   # Replace with the actual project ID
import requests
import os
from datetime import datetime

# GNS3 server details
server_url = "http://localhost:3080"  # Local GNS3 server
project_id = "b9239bf1-5d1d-4f74-88de-c04171ac1e8a"   # Replace with your actual project ID

# Directory to save configs
output_dir = f"gns3_configs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
os.makedirs(output_dir, exist_ok=True)

# API endpoint for nodes
nodes_endpoint = f"{server_url}/v2/projects/{project_id}/nodes"

def get_nodes_and_ports():
    """Retrieve list of nodes and their console ports from GNS3 API."""
    try:
        response = requests.get(nodes_endpoint)
        if response.status_code != 200:
            print(f"Failed to retrieve nodes. Status code: {response.status_code}")
            return None
        nodes = response.json()
        return nodes
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching nodes: {e}")
        return None

def capture_startup_config(node, instance_num):
    """Capture the startup-config file for a node using the GNS3 API and save it locally."""
    node_id = node["node_id"]
    node_name = node["name"]
    node_type = node["node_type"]

    if node_type != "dynamips":
        print(f"  {node_name}: Only Dynamips nodes support startup-config capture via API.")
        return

    # Use instance number for config file naming (e.g., i1, i2)
    config_file = f"configs/i{instance_num}_startup-config.cfg"
    files_endpoint = f"{server_url}/v2/projects/{project_id}/nodes/{node_id}/files/{config_file}"

    print(f"Capturing startup-config for {node_name} (Type: {node_type})...")

    try:
        response = requests.get(files_endpoint)
        if response.status_code == 200:
            config_content = response.text
            save_config(node_name, config_content)
        else:
            print(f"  No startup-config found for {node_name} or access failed. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"  Error retrieving startup-config for {node_name}: {e}")

def save_config(node_name, config_content):
    """Save the config content to a local file."""
    safe_node_name = "".join(c for c in node_name if c.isalnum() or c in "._-")
    file_path = os.path.join(output_dir, f"{safe_node_name}_startup-config.txt")
    try:
        with open(file_path, "w") as f:
            f.write(config_content)
        print(f"  Startup-config saved to {file_path}")
    except IOError as e:
        print(f"  Failed to save startup-config for {node_name}: {e}")

def main():
    # Get nodes and their ports
    nodes = get_nodes_and_ports()
    if not nodes:
        print("No nodes retrieved. Exiting.")
        return

    # Display nodes with their console ports
    print(f"\nDumping startup-configs for project {project_id}...")
    print(f"Configs will be saved in: {output_dir}\n")
    print("Available nodes and their console ports:")
    for i, node in enumerate(nodes, 1):
        console_port = node.get("console", "N/A")
        print(f"{i}. Name: {node['name']}, ID: {node['node_id']}, Type: {node['node_type']}, "
              f"Status: {node['status']}, Console Port: {console_port}")

    # Prompt for selection mode
    print("\nOptions:")
    print("  1. Capture startup-config for a single node")
    print("  2. Capture startup-config for multiple specific nodes")
    print("  3. Capture startup-config for all nodes")
    choice = input("Enter your choice (1-3): ").strip()

    if choice not in ["1", "2", "3"]:
        print("Invalid choice. Exiting.")
        return

    selected_nodes = []
    if choice == "1":
        # Single node
        node_num = input(f"Enter the number of the node (1-{len(nodes)}): ").strip()
        if not node_num.isdigit() or not (1 <= int(node_num) <= len(nodes)):
            print("Invalid node number. Exiting.")
            return
        selected_nodes.append((int(node_num) - 1, nodes[int(node_num) - 1]))
    elif choice == "2":
        # Multiple nodes
        node_nums = input(f"Enter node numbers (1-{len(nodes)}), separated by spaces: ").strip().split()
        for num in node_nums:
            if not num.isdigit() or not (1 <= int(num) <= len(nodes)):
                print(f"Invalid node number: {num}. Exiting.")
                return
            selected_nodes.append((int(num) - 1, nodes[int(num) - 1]))
    elif choice == "3":
        # All nodes
        selected_nodes = [(i, node) for i, node in enumerate(nodes)]

    # Process selected nodes
    print("\nProcessing selected nodes...")
    for instance_idx, node in selected_nodes:
        # Use instance number based on original index (i+1)
        capture_startup_config(node, instance_idx + 1)

    print("\nStartup-config capture completed.")

if __name__ == "__main__":
    main()
