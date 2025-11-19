import os
from air import AsyncAIRefinery
from dotenv import load_dotenv

# ---------------------- LOAD ENV ----------------------
load_dotenv()
API_KEY = str(os.getenv("API_KEY"))

# ------------------- PROJECT CONFIG -------------------
CONFIG_PATH = "" # TODO
PROJECT_NAME = "" # TODO

# ------------------- CREATE PROJECT -------------------
def create_project():
    """
    This creates the project in AI Refinery. Needs to be run upon config/agent change.
    """

    # Validate the config file
    client = AsyncAIRefinery(api_key=API_KEY)
    if client.distiller.validate_config(config_path=CONFIG_PATH):
        print("Configuration validation successful.")

        # Create the project
        if client.distiller.create_project(config_path=CONFIG_PATH, project=PROJECT_NAME):
            print(f"Project '{PROJECT_NAME}' created successfully from {CONFIG_PATH}!")
        else:
            print("Failed to create project.")
    else:
        print("Failed to create project.")

if __name__ == "__main__":
    create_project()