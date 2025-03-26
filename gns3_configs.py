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
                return project, selected["name"]
            print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a number.")

def display_nodes(project: gns3fy.Project) -> List[gns3fy.Node]:
    """Get and display all nodes in project, return node list"""
    project.get