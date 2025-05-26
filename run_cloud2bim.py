"""
Command-line client for Cloud2BIM processing.
"""
import argparse
import os
from app.utils.point_cloud_utils import process_point_cloud

def main():
    parser = argparse.ArgumentParser(description='Process point cloud files using Cloud2BIM')
    parser.add_argument('ptx_file', help='Path to the PTX file to process')
    parser.add_argument('--config', default='app/config/config.yaml', help='Path to the configuration file')
    parser.add_argument('--output-dir', default='output', help='Directory for output files')
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        # Process the point cloud
        ifc_file = process_point_cloud(
            ptx_file=args.ptx_file,
            config_file=args.config,
            output_dir=args.output_dir
        )
        print(f"Successfully generated IFC file: {ifc_file}")
        
    except Exception as e:
        print(f"Error processing point cloud: {e}")
        exit(1)

if __name__ == '__main__':
    main()
