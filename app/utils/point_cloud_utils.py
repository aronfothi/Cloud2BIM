"""Point cloud utility functions for Cloud2BIM."""

import numpy as np
import open3d as o3d
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def read_ptx_file(file_path: str, subsample: int = 1) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Read a PTX file and return points and colors (if available).

    Args:
        file_path: Path to the PTX file
        subsample: Read every nth point (default=1, i.e., read all points)

    Returns:
        Tuple containing:
        - numpy array of shape (N, 3) containing point coordinates
        - numpy array of shape (N, 3) containing RGB colors, or None if no colors
    """
    try:
        pcd = o3d.io.read_point_cloud(file_path)
        points = np.asarray(pcd.points)
        colors = np.asarray(pcd.colors) if pcd.has_colors() else None

        if subsample > 1:
            indices = np.arange(0, len(points), subsample)
            points = points[indices]
            if colors is not None:
                colors = colors[indices]

        return points, colors
    except Exception as e:
        logger.error(f"Error reading PTX file {file_path}: {e}")
        raise


def create_point_cloud_data(points: np.ndarray, colors: Optional[np.ndarray] = None) -> dict:
    """
    Create a dictionary containing point cloud data suitable for the Cloud2BIM API.

    Args:
        points: numpy array of shape (N, 3) containing point coordinates
        colors: optional numpy array of shape (N, 3) containing RGB colors

    Returns:
        Dictionary containing point cloud data ready for API submission
    """
    data = {
        "points": points.tolist(),
        "colors": colors.tolist() if colors is not None else None,
        "filename": "input.ptx",
    }
    return data


def process_point_cloud(ptx_file: str, config_file: str, output_dir: str) -> str:
    """
    Process a point cloud file using the Cloud2BIM processor directly.

    Args:
        ptx_file: Path to the PTX file
        config_file: Path to the configuration YAML file
        output_dir: Directory where output files should be saved

    Returns:
        Path to the generated IFC file
    """
    from app.core.cloud2entities import CloudToBimProcessor
    from app.core.aux_functions import load_config_and_variables_new
    from app.core.point_cloud import read_ptx_file
    import os
    import open3d as o3d

    # Load configuration
    config = load_config_and_variables_new(config_path=config_file)

    # Load point cloud using PTX reader with subsampling
    points, colors = read_ptx_file(ptx_file, subsample=10)  # Use every 10th point
    if points is None or len(points) == 0:
        raise ValueError(f"Failed to load point cloud from {ptx_file}")
    logger.info(f"Loaded {len(points)} points from {ptx_file}")

    # Convert to Open3D format
    pcl = o3d.geometry.PointCloud()
    pcl.points = o3d.utility.Vector3dVector(points)
    if colors is not None:
        pcl.colors = o3d.utility.Vector3dVector(colors)

    # Create and run processor
    processor = CloudToBimProcessor(
        job_id="local-job", config_data=config, output_dir=output_dir, point_cloud_data=pcl
    )

    processor.process()

    # Return path to the generated IFC file
    ifc_file = os.path.join(output_dir, "local-job_model.ifc")
    if not os.path.exists(ifc_file):
        raise FileNotFoundError(f"IFC file was not generated at {ifc_file}")

    return ifc_file
