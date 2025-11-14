# setup_north_twin_project.py
import os
from air import DistillerClient
from dotenv import load_dotenv

# ------------------- LOAD ENV -------------------
load_dotenv()
api_key = str(os.getenv("API_KEY"))

# ------------------- PROJECT CONFIG -------------------
CONFIG_PATH = "north_twin_config.yaml"  # your YAML file
PROJECT_NAME = "NorthTwin_AIRefinery_Challenge_Project_Sep2025"

# ------------------- CREATE PROJECT -------------------
def create_project():
    distiller_client = DistillerClient(api_key=api_key)
    distiller_client.create_project(
        config_path=CONFIG_PATH,
        project=PROJECT_NAME
    )
    print(f"Project '{PROJECT_NAME}' created successfully from {CONFIG_PATH}!")

if __name__ == "__main__":
    create_project()
