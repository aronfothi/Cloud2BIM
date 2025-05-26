"""Utility functions for handling PTX files."""

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
    points = []
    colors = []

    try:
        with open(file_path, "r") as f:
            # Skip header (12 lines)
            for _ in range(12):
                next(f)

            # Read point data
            for i, line in enumerate(f):
                if i % subsample != 0:
                    continue

                values = line.strip().split()
                if len(values) >= 3:  # At least x, y, z coordinates
                    points.append([float(v) for v in values[:3]])

                    if len(values) >= 7:  # Has RGB values
                        # Normalize RGB values to [0, 1]
                        colors.append([float(v) / 255.0 for v in values[4:7]])

        points_array = np.array(points, dtype=np.float32)
        colors_array = np.array(colors, dtype=np.float32) if colors else None

        return points_array, colors_array

    except Exception as e:
        logger.error(f"Error reading PTX file {file_path}: {str(e)}")
        raise


def create_open3d_point_cloud(
    points: np.ndarray, colors: Optional[np.ndarray] = None
) -> o3d.geometry.PointCloud:
    """
    Create an Open3D point cloud from numpy arrays.

    Args:
        points: numpy array of shape (N, 3) containing point coordinates
        colors: optional numpy array of shape (N, 3) containing RGB colors

    Returns:
        Open3D PointCloud object
    """
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    if colors is not None:
        pcd.colors = o3d.utility.Vector3dVector(colors)
    return pcd
