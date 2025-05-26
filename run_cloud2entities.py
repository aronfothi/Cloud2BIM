import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Modify import to use absolute imports
from app.core.aux_functions import *
from app.core.generate_ifc import IFCmodel
from app.core.space_generator import *
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_cloud2entities.py <config_file>")
        sys.exit(1)
        
    config_file = sys.argv[1]
    
    # === Load Configuration ===
    config = load_config_and_variables(config_file)
    
    # === Assign variables ===
    e57_input = config["e57_input"]
    if e57_input:
        e57_file_names = config["e57_file_names"]
    xyz_filenames = config["xyz_filenames"]
    exterior_scan = config["exterior_scan"]
    dilute_pointcloud = config["dilute_pointcloud"]
    dilution_factor = config["dilution_factor"]
    pc_resolution = config["pc_resolution"]
    grid_coefficient = config["grid_coefficient"]

    bfs_thickness = config["bfs_thickness"]
    tfs_thickness = config["tfs_thickness"]
    
    # Continue with the rest of the script logic
    # This will execute the original cloud2entities_ori.py code
    # You may want to add the rest of the code here from cloud2entities_ori.py
    
    print("Configuration loaded successfully from:", config_file)
    print("Script execution would continue here with the loaded configuration.")
