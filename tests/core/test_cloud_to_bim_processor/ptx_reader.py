"""
Custom PTX reader for the specific format used in our test data.
"""
import numpy as np
import open3d as o3d
from typing import Tuple, Optional, List
import os

def read_custom_ptx(file_path: str, downsample_steps=1) -> o3d.geometry.PointCloud:
    """
    Read a PTX file in the format used in our test data.
    
    The expected PTX format is:
    - Line 1: Number of rows
    - Line 2: Number of columns
    - Line 3: Scanner position (3 values)
    - Line 4-6: Scanner axes (3 values each)
    - Line 7-10: Transformation matrix (4 values each)
    - Line 11: Additional info
    - Remaining lines: Point data (x, y, z, intensity, r, g, b)
    
    Args:
        file_path: Path to the PTX file
        
    Returns:
        Open3D PointCloud object
    """
    points = []
    colors = []
    
    try:
        with open(file_path, 'r') as f:
            lines = [line.strip() for line in f.readlines()]
            
            # Parse header
            if len(lines) < 11:
                raise ValueError("PTX file too short")
                
            # Read rows and columns
            rows = int(lines[0])
            cols = int(lines[1])
            
            # Skip the scanner position and axes info (lines 3-6)
            # Skip the transformation matrix (lines 7-10)
            
            # Start reading point data from line 11
            data_start = 11
            
            for i in range(data_start, len(lines), downsample_steps):
                line = lines[i]
                if not line:
                    continue
                
                try:
                    values = [float(x) for x in line.split()]
                    if len(values) >= 3:  # At least XYZ coordinates
                        points.append(values[:3])
                        if len(values) >= 7:  # Has RGB values
                            # Normalize RGB values to [0,1] range if they're in [0,255]
                            r, g, b = values[4:7]
                            if max(r, g, b) > 1.0:
                                r, g, b = r/255.0, g/255.0, b/255.0
                            colors.append([r, g, b])
                except (ValueError, IndexError):
                    # Skip invalid lines
                    continue
    except Exception as e:
        raise ValueError(f"Failed to read PTX file {file_path}: {str(e)}")
    
    if not points:
        raise ValueError(f"No valid points found in PTX file: {file_path}")
    
    # Create Open3D point cloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np.array(points))
    
    if colors and len(colors) == len(points):
        pcd.colors = o3d.utility.Vector3dVector(np.array(colors))
    
    return pcd
