"""Test the core processing functionality."""

import pytest
from pathlib import Path
import numpy as np
import open3d as o3d

from app.core.job_processor import process_point_cloud
from app.core.cloud2entities import detect_walls, detect_slabs


def test_point_cloud_processing():
    """Test the point cloud processing pipeline."""
    # TODO: Create sample point cloud data
    points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]])

    # Create Open3D point cloud
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)

    # Test processing
    # TODO: Implement actual test after finalizing process_point_cloud function


def test_wall_detection():
    """Test wall detection algorithm."""
    # TODO: Create sample point cloud with known walls
    # TODO: Implement test after finalizing detect_walls function


def test_slab_detection():
    """Test slab detection algorithm."""
    # TODO: Create sample point cloud with known slabs
    # TODO: Implement test after finalizing detect_slabs function
