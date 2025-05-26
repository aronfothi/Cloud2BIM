"""
Tests for point cloud processing functionality.
"""

import pytest
import numpy as np
import open3d as o3d
from pathlib import Path
from app.core.point_cloud import PointCloudProcessor, PointCloudStats


@pytest.fixture
def test_config():
    return {"preprocessing": {"voxel_size": 0.05, "noise_threshold": 2.0}}


@pytest.fixture
def test_room_path():
    return str(Path(__file__).parent.parent / "data" / "test_room.xyz")


def test_load_xyz_file(test_config, test_room_path):
    """Test loading an XYZ file"""
    processor = PointCloudProcessor(test_config)
    pcd = processor.load_file(test_room_path)

    assert pcd is not None
    assert len(pcd.points) > 0
    assert processor.stats is not None
    assert processor.stats.num_points == len(pcd.points)


def test_preprocessing(test_config, test_room_path):
    """Test point cloud preprocessing"""
    processor = PointCloudProcessor(test_config)
    processor.load_file(test_room_path)

    processed_pcd = processor.preprocess()

    assert processed_pcd is not None
    assert processed_pcd.has_normals()
    assert len(processed_pcd.points) <= len(processor.pcd.points)  # Should be downsampled


def test_segmentation(test_config, test_room_path):
    """Test normal-based segmentation"""
    processor = PointCloudProcessor(test_config)
    processor.load_file(test_room_path)
    processor.preprocess()

    segments = processor.segment_by_normal(angle_threshold=20.0)

    assert len(segments) > 0  # Should find at least walls and floor
    assert all(isinstance(seg, np.ndarray) for seg in segments)
    assert all(seg.dtype == np.int64 for seg in segments)


def test_slice_extraction(test_config, test_room_path):
    """Test horizontal slice extraction"""
    processor = PointCloudProcessor(test_config)
    processor.load_file(test_room_path)

    # Extract slice at door height
    slice_pcd = processor.get_slice(height=1.0, thickness=0.2)

    assert slice_pcd is not None
    assert len(slice_pcd.points) > 0
    assert len(slice_pcd.points) < len(processor.pcd.points)


def test_point_cloud_stats(test_config, test_room_path):
    """Test point cloud statistics computation"""
    processor = PointCloudProcessor(test_config)
    processor.load_file(test_room_path)

    stats = processor.stats

    assert isinstance(stats, PointCloudStats)
    assert stats.num_points > 0
    assert stats.dimensions.shape == (3,)
    assert stats.density > 0
    assert isinstance(stats.has_normals, bool)
    assert isinstance(stats.has_colors, bool)


def test_invalid_file():
    """Test error handling for invalid files"""
    processor = PointCloudProcessor({"preprocessing": {"voxel_size": 0.05, "noise_threshold": 2.0}})

    with pytest.raises(ValueError):
        processor.load_file("nonexistent.abc")


def test_processing_without_loading():
    """Test error handling when processing without loading"""
    processor = PointCloudProcessor({"preprocessing": {"voxel_size": 0.05, "noise_threshold": 2.0}})

    with pytest.raises(ValueError):
        processor.preprocess()
