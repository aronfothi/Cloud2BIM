"""Models for point cloud data validation and processing."""

from typing import List, Optional
from pydantic import BaseModel, Field, validator
import numpy as np


class PointCloudData(BaseModel):
    """Model for standardized point cloud data transmission."""

    points: List[List[float]] = Field(..., description="List of [x,y,z] coordinates")
    colors: Optional[List[List[float]]] = Field(None, description="Optional list of [r,g,b] values")
    format: str = Field(..., description="Original format of the point cloud (e.g., 'ptx', 'ply')")
    filename: str = Field(..., description="Original filename")

    @validator("points")
    def validate_points(cls, v):
        """Validate that points are properly formatted."""
        if not v:
            raise ValueError("Points list cannot be empty")
        if not all(len(p) == 3 for p in v):
            raise ValueError("All points must have exactly 3 coordinates (x,y,z)")
        return v

    @validator("colors")
    def validate_colors(cls, v, values):
        """Validate that colors match points and are normalized."""
        if v is not None:
            if "points" not in values:
                raise ValueError("Cannot validate colors without points")
            if len(v) != len(values["points"]):
                raise ValueError("Number of colors must match number of points")
            if not all(len(c) == 3 for c in v):
                raise ValueError("All colors must have exactly 3 values (r,g,b)")
            if not all(all(0 <= val <= 1 for val in c) for c in v):
                raise ValueError("Color values must be normalized between 0 and 1")
        return v

    def to_numpy(self) -> tuple:
        """Convert points and colors to numpy arrays."""
        points_array = np.array(self.points, dtype=np.float32)
        colors_array = np.array(self.colors, dtype=np.float32) if self.colors else None
        return points_array, colors_array
