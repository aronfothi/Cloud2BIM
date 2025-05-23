"""
Core point cloud processing functionality for Cloud2BIM.
This module handles loading, preprocessing, and basic analysis of point clouds.
"""
import numpy as np
import open3d as o3d
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class PointCloudStats:
    """Statistics about a point cloud"""
    num_points: int
    bounds: Tuple[np.ndarray, np.ndarray]  # min_bound, max_bound
    dimensions: np.ndarray  # xyz dimensions
    density: float  # average points per cubic meter
    has_normals: bool
    has_colors: bool

class PointCloudProcessor:
    """Handles point cloud loading and preprocessing"""
    
    def __init__(self, config: Dict):
        """
        Initialize processor with configuration.
        
        Args:
            config: Dictionary containing preprocessing parameters
        """
        self.config = config
        self.pcd = None
        self.stats = None
    
    def load_file(self, filepath: str) -> o3d.geometry.PointCloud:
        """
        Load point cloud from file with format detection.
        
        Args:
            filepath: Path to point cloud file
            
        Returns:
            Loaded point cloud
        """
        try:
            if filepath.endswith('.ptx'):
                self.pcd = o3d.io.read_point_cloud(filepath, format='ptx')
            elif filepath.endswith('.xyz'):
                self.pcd = o3d.io.read_point_cloud(filepath, format='xyz')
            else:
                raise ValueError(f"Unsupported file format: {filepath}")
            
            logger.info(f"Loaded point cloud with {len(self.pcd.points)} points")
            self._compute_stats()
            return self.pcd
            
        except Exception as e:
            logger.error(f"Error loading point cloud: {str(e)}")
            raise
    
    def _compute_stats(self) -> PointCloudStats:
        """
        Compute basic statistics about the point cloud.
        """
        if self.pcd is None:
            raise ValueError("No point cloud loaded")
            
        points = np.asarray(self.pcd.points)
        min_bound = np.min(points, axis=0)
        max_bound = np.max(points, axis=0)
        dimensions = max_bound - min_bound
        volume = np.prod(dimensions)
        density = len(points) / volume if volume > 0 else 0
        
        self.stats = PointCloudStats(
            num_points=len(points),
            bounds=(min_bound, max_bound),
            dimensions=dimensions,
            density=density,
            has_normals=self.pcd.has_normals(),
            has_colors=self.pcd.has_colors()
        )
        
        return self.stats
    
    def preprocess(self) -> o3d.geometry.PointCloud:
        """
        Preprocess point cloud according to configuration.
        - Downsample
        - Remove noise
        - Estimate normals if needed
        """
        if self.pcd is None:
            raise ValueError("No point cloud loaded")
            
        # Downsample
        voxel_size = self.config["preprocessing"]["voxel_size"]
        self.pcd = self.pcd.voxel_down_sample(voxel_size=voxel_size)
        logger.info(f"Downsampled to {len(self.pcd.points)} points")
        
        # Remove noise
        noise_threshold = self.config["preprocessing"]["noise_threshold"]
        self.pcd, _ = self.pcd.remove_statistical_outlier(
            nb_neighbors=20,
            std_ratio=noise_threshold
        )
        logger.info(f"After noise removal: {len(self.pcd.points)} points")
        
        # Estimate normals if not present
        if not self.pcd.has_normals():
            self.pcd.estimate_normals(
                search_param=o3d.geometry.KDTreeSearchParamHybrid(
                    radius=voxel_size * 2,
                    max_nn=30
                )
            )
            logger.info("Normal estimation completed")
        
        self._compute_stats()
        return self.pcd
    
    def segment_by_normal(self, angle_threshold: float = 20.0) -> List[np.ndarray]:
        """
        Segment points into groups based on normal directions.
        Useful for separating walls, floors, etc.
        
        Args:
            angle_threshold: Maximum angle difference in degrees
            
        Returns:
            List of point indices for each segment
        """
        if not self.pcd.has_normals():
            raise ValueError("Point cloud needs normals for segmentation")
            
        normals = np.asarray(self.pcd.normals)
        points = np.asarray(self.pcd.points)
        
        # Convert angle to radians
        angle_rad = np.radians(angle_threshold)
        
        # Find primary directions (vertical and horizontal)
        up_vector = np.array([0, 0, 1])
        horizontal_mask = np.abs(np.dot(normals, up_vector)) < np.cos(angle_rad)
        vertical_mask = np.abs(np.dot(normals, up_vector)) > np.cos(np.pi/2 - angle_rad)
        
        segments = []
        
        # Horizontal surfaces (floors/ceilings)
        if np.any(vertical_mask):
            segments.append(np.where(vertical_mask)[0])
        
        # Vertical surfaces (walls)
        if np.any(horizontal_mask):
            horizontal_points = points[horizontal_mask]
            horizontal_normals = normals[horizontal_mask]
            
            # Group by similar normal directions
            from sklearn.cluster import DBSCAN
            angles = np.arctan2(horizontal_normals[:, 1], horizontal_normals[:, 0])
            clustering = DBSCAN(eps=angle_rad, min_samples=10).fit(angles.reshape(-1, 1))
            
            for label in np.unique(clustering.labels_):
                if label >= 0:  # Skip noise points labeled as -1
                    mask = clustering.labels_ == label
                    original_indices = np.where(horizontal_mask)[0][mask]
                    segments.append(original_indices)
        
        return segments
    
    def get_slice(self, height: float, thickness: float = 0.1) -> o3d.geometry.PointCloud:
        """
        Extract a horizontal slice of the point cloud at given height.
        Useful for creating floor plans.
        
        Args:
            height: Height of the slice in meters
            thickness: Thickness of the slice in meters
            
        Returns:
            Point cloud containing only points in the slice
        """
        points = np.asarray(self.pcd.points)
        mask = np.abs(points[:, 2] - height) < thickness/2
        
        slice_pcd = o3d.geometry.PointCloud()
        slice_pcd.points = o3d.utility.Vector3dVector(points[mask])
        
        if self.pcd.has_normals():
            normals = np.asarray(self.pcd.normals)
            slice_pcd.normals = o3d.utility.Vector3dVector(normals[mask])
        
        if self.pcd.has_colors():
            colors = np.asarray(self.pcd.colors)
            slice_pcd.colors = o3d.utility.Vector3dVector(colors[mask])
        
        return slice_pcd
    
    def visualize(self, segments: Optional[List[np.ndarray]] = None) -> None:
        """
        Visualize the point cloud, optionally with segmentation.
        
        Args:
            segments: Optional list of point indices for different segments
        """
        if segments is None:
            o3d.visualization.draw_geometries([self.pcd])
        else:
            colors = self.get_segment_colors(len(segments))
            vis_pcd = o3d.geometry.PointCloud()
            vis_pcd.points = self.pcd.points
            
            points = np.asarray(self.pcd.points)
            point_colors = np.zeros((len(points), 3))
            
            for i, segment in enumerate(segments):
                point_colors[segment] = colors[i]
            
            vis_pcd.colors = o3d.utility.Vector3dVector(point_colors)
            o3d.visualization.draw_geometries([vis_pcd])
    
    @staticmethod
    def get_segment_colors(num_segments: int) -> np.ndarray:
        """Generate distinct colors for visualization"""
        colors = []
        for i in range(num_segments):
            hue = i / num_segments
            # Convert HSV to RGB (assuming S=V=1)
            if hue < 1/3:
                colors.append([1, 3*hue, 0])
            elif hue < 2/3:
                colors.append([2-3*hue, 1, 0])
            else:
                colors.append([0, 1, 3*hue-2])
        return np.array(colors)

def read_point_cloud(file_path: str, subsample: int = 1) -> Optional[o3d.geometry.PointCloud]:
    """
    Read a point cloud from file in various formats (PTX, XYZ, PLY).
    
    Args:
        file_path: Path to point cloud file
        subsample: Subsampling factor (only applies to PTX files)
        
    Returns:
        PointCloud object or None if loading fails
    """
    try:
        file_ext = file_path.lower().split('.')[-1]
        
        if file_ext == 'ptx':
            points, colors = read_ptx_file(file_path, subsample)
            if points is None:
                return None
                
            pcd = o3d.geometry.PointCloud()
            pcd.points = o3d.utility.Vector3dVector(points)
            if colors is not None:
                pcd.colors = o3d.utility.Vector3dVector(colors)
            return pcd
            
        elif file_ext in ['xyz', 'ply']:
            try:
                return o3d.io.read_point_cloud(file_path)
            except Exception as e:
                logger.error(f"Failed to read {file_ext} file: {e}")
                return None
                
        else:
            logger.error(f"Unsupported file format: {file_ext}")
            return None
            
    except Exception as e:
        logger.error(f"Error reading point cloud file {file_path}: {e}")
        return None

def read_ptx_file(file_path: str, subsample: int = 1) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Read points and colors from a PTX file.
    
    Args:
        file_path: Path to PTX file
        subsample: Take every nth point
        
    Returns:
        Tuple of (points, colors) arrays, or (None, None) if reading fails
    """
    try:
        # Read header
        with open(file_path, 'r') as f:
            # Read scanner and grid params (not used currently)
            rows = int(f.readline().strip())
            cols = int(f.readline().strip())
            
            # Skip transformation matrix
            for _ in range(4):
                f.readline()
                
            # Read points
            points = []
            colors = []
            
            line_count = 0
            for line in f:
                line_count += 1
                if line_count % subsample != 0:
                    continue
                    
                values = line.strip().split()
                if len(values) >= 7:  # x,y,z,i,r,g,b
                    x, y, z = map(float, values[0:3])
                    r, g, b = map(float, values[4:7])
                    points.append([x, y, z])
                    # Normalize RGB values to [0,1]
                    colors.append([r/255.0, g/255.0, b/255.0])
                    
            if not points:
                return None, None
                
            return np.array(points), np.array(colors)
            
    except Exception as e:
        logger.error(f"Error reading PTX file {file_path}: {e}")
        return None, None
