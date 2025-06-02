from .aux_functions import load_config_and_variables_new  # Removed log_message
from .generate_ifc import IFCmodel
from .space_generator import identify_zones  # Keep direct import if it's a standalone function

# Import other necessary functions from aux_functions or other modules if they are not part of a class yet
# e.g., from .aux_functions import read_e57, e57_data_to_xyz, load_xyz_file
# e.g., from .point_cloud import identify_slabs, identify_walls, identify_openings (if these become methods of a PointCloud class later)

import numpy as np
import time
import os
import logging  # Use standard logging
import json
import open3d as o3d
import psutil
from datetime import datetime
from ..models.job import ProcessingStage

logger = logging.getLogger(__name__)


class CloudToBimProcessor:
    """
    Processes a 3D point cloud file and converts it into an IFC BIM model.
    """

    def __init__(self, job_id: str, config_data: dict, output_dir: str, point_cloud_data=None, progress_callback=None):
        """
        Initializes the CloudToBimProcessor.

        Args:
            job_id: The unique identifier for the job.
            config_data: A dictionary containing the job-specific configuration.
            input_dir: The directory containing input files for the job.
            output_dir: The directory where output files will be saved.
            point_cloud_data: Pre-loaded point cloud data (Open3D PointCloud or tuple of numpy arrays).
                             If provided, the processor won't try to load from a file.
            progress_callback: Optional callback function to update progress (stage: str, progress: int)
        """
        self.job_id = job_id
        self.config = config_data
        print(f"Config: {self.config}")
        self.output_dir = output_dir
        self.log_filename = os.path.join(self.output_dir, f"{self.job_id}_processing.log")
        self.progress_callback = progress_callback
        self._setup_logging()

        # Initialize state variables
        self.points_xyz = np.empty((0, 3))
        self.points_rgb = np.empty((0, 3))
        self.slabs = []
        self.walls = []
        self.all_openings = []
        self.zones = []
        self.ifc_model = None
        self.last_time = time.time()
        self.point_cloud_data = point_cloud_data
        self.start_time = time.time()
        self.total_points = 0
        self.processed_points = 0
        self.current_stage = ProcessingStage.INITIALIZING

        # Default IFC file path (can be overridden by config)
        self.ifc_output_file = os.path.join(self.output_dir, f"{self.job_id}_model.ifc")
        self.point_mapping_file = os.path.join(self.output_dir, f"{self.job_id}_point_mapping.json")

        # Assign variables from config
        self._assign_config_variables()

    def _setup_logging(self):
        """Sets up logging for the processor instance."""
        # Using the module-level logger defined as "logger" at the top of the file.
        # If job-specific file logging is needed, it would be configured here.
        # For now, all logs from this processor will go to the handlers configured for the module logger.
        pass

    def _log(self, message: str, level: str = "info"):
        """Logs a message using the module-level logger and updates the last_time."""
        log_func = getattr(
            logger, level.lower(), logger.info
        )  # Default to info if level is invalid
        log_func(f"Job {self.job_id}: {message}")
        current_time = time.time()
        elapsed = current_time - self.last_time
        logger.debug(f"Job {self.job_id}: Time since last log: {elapsed:.2f}s")
        self.last_time = current_time

    def _update_progress(self, stage: str, progress: int):
        """Updates progress via callback if available"""
        if self.progress_callback:
            self.progress_callback(stage, progress)
        self._log(f"Progress: {stage} - {progress}%")

    def _update_detailed_progress(self, stage: ProcessingStage, percentage: int, 
                                current_operation: str = None, 
                                processed_items: int = None,
                                total_items: int = None):
        """Enhanced progress update with detailed information"""
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        
        # Calculate processing speed
        processing_speed = None
        if elapsed_time > 0 and self.processed_points > 0:
            speed = self.processed_points / elapsed_time
            if speed > 1000:
                processing_speed = f"{speed/1000:.1f}k points/sec"
            else:
                processing_speed = f"{speed:.1f} points/sec"
        
        # Estimate remaining time
        estimated_remaining = None
        if percentage > 0 and percentage < 100:
            total_estimated_time = elapsed_time * (100 / percentage)
            estimated_remaining = int(total_estimated_time - elapsed_time)
        
        # Get memory usage
        process = psutil.Process(os.getpid())
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        cpu_usage = process.cpu_percent()
        
        progress_data = {
            "status": "running",
            "stage": stage.value,
            "progress": {
                "percentage": percentage,
                "stage": stage,
                "stage_description": self._get_stage_description(stage),
                "current_operation": current_operation,
                "processed_items": processed_items or self.processed_points,
                "total_items": total_items or self.total_points,
                "estimated_remaining_seconds": estimated_remaining,
                "processing_speed": processing_speed
            },
            "performance": {
                "start_time": datetime.fromtimestamp(self.start_time),
                "last_update_time": datetime.fromtimestamp(current_time),
                "points_processed": self.processed_points,
                "memory_usage_mb": memory_usage,
                "cpu_usage_percent": cpu_usage
            }
        }
        
        if self.progress_callback:
            self.progress_callback(progress_data)
        
        # Add small delay for visibility
        time.sleep(0.1)

    def _get_stage_description(self, stage: ProcessingStage) -> str:
        """Get human-readable description for each stage"""
        descriptions = {
            ProcessingStage.INITIALIZING: "Setting up processing environment...",
            ProcessingStage.LOADING_POINT_CLOUD: "Loading and parsing point cloud data...",
            ProcessingStage.PREPROCESSING: "Cleaning and preparing point cloud...",
            ProcessingStage.DETECTING_SLABS: "Identifying floor and ceiling surfaces...",
            ProcessingStage.DETECTING_WALLS: "Detecting wall structures...",
            ProcessingStage.DETECTING_OPENINGS: "Finding doors and windows...",
            ProcessingStage.DETECTING_ZONES: "Analyzing spatial zones...",
            ProcessingStage.GENERATING_IFC: "Creating BIM model structure...",
            ProcessingStage.FINALIZING: "Saving results and cleanup..."
        }
        return descriptions.get(stage, "Processing...")

    def _assign_config_variables(self):
        """Assigns configuration variables to instance attributes."""
        # Processing parameters
        self.exterior_scan = self.config.get("exterior_scan", False)
        self.dilute_pointcloud = self.config.get("dilute_pointcloud", False)
        self.dilution_factor = self.config.get("dilution_factor", 1)
        self.pc_resolution = self.config.get("preprocessing", {}).get("voxel_size", 0.05)
        self.grid_coefficient = self.config.get("detection", {}).get("grid_coefficient", 3)

        # Detection thresholds
        detection_config = self.config.get("detection", {})
        slab_config = detection_config.get("slab", {})
        wall_config = detection_config.get("wall", {})
        self.bfs_thickness = slab_config.get("thickness", 0.2)
        self.tfs_thickness = self.bfs_thickness  # Use same thickness for top and bottom slabs

        self.min_wall_length = wall_config.get("min_width", 0.5)
        self.min_wall_thickness = wall_config.get("min_thickness", 0.08)
        self.max_wall_thickness = wall_config.get("max_thickness", 0.5)
        self.exterior_walls_thickness = wall_config.get("thickness", 0.3)

        # IFC settings
        ifc_config = self.config.get("ifc", {})
        self.ifc_output_file = os.path.join(self.output_dir, f"{self.job_id}_model.ifc")
        self.ifc_project_name = ifc_config.get("project_name", "Cloud2BIM Project")
        self.ifc_project_long_name = ifc_config.get("project_long_name", "Generated by Cloud2BIM")
        self.ifc_project_version = ifc_config.get("version", "1.0")

        self.ifc_building_name = ifc_config.get("building_name", "Building")
        self.ifc_building_type = ifc_config.get("building_type", "Building")
        self.ifc_building_phase = ifc_config.get("building_phase", "Construction")
        self.ifc_site_latitude = ifc_config.get("site_latitude", 0.0)
        self.ifc_site_longitude = ifc_config.get("site_longitude", 0.0)
        self.ifc_site_elevation = ifc_config.get("site_elevation", 0.0)
        self.material_for_objects = ifc_config.get("material_for_objects", "Concrete")
        self.window_colour_rgb = ifc_config.get("window_colour_rgb", [0.0, 0.0, 1.0])
        self.door_colour_rgb = ifc_config.get("door_colour_rgb", [1.0, 0.0, 0.0])
        self.material_for_objects = ifc_config.get("material_for_objects", "Concrete")
        self.material_for_walls = ifc_config.get("material_for_walls", "Concrete")
        self.material_for_windows = ifc_config.get("material_for_windows", "Glass")
        self.material_for_doors = ifc_config.get("material_for_doors", "Wood")
        self.material_for_roofs = ifc_config.get("material_for_roofs", "Concrete")
        self.material_for_floors = ifc_config.get("material_for_floors", "Concrete")

        # Optional metadata
        self.ifc_author_name = ifc_config.get("author_name", "Cloud2BIM")
        self.ifc_author_surname = ifc_config.get("author_surname", "System")
        self.ifc_author_organization = ifc_config.get("organization", "Cloud2BIM")

    def _load_and_prepare_point_cloud(self):
        """Prepares point cloud data from pre-loaded data."""
        self._log("Starting point cloud preparation")

        if self.point_cloud_data is None:
            raise ValueError(
                "No point cloud data provided. CloudToBimProcessor requires point_cloud_data to be passed during initialization."
            )

        # Handle different input formats
        if hasattr(self.point_cloud_data, "points"):  # Check if it's an Open3D PointCloud
            # It's an Open3D PointCloud object
            pcd = self.point_cloud_data
            # Convert to numpy arrays
            self.points_xyz = np.asarray(pcd.points)
            if pcd.has_colors():
                self.points_rgb = np.asarray(pcd.colors)
            else:
                self.points_rgb = np.empty((len(self.points_xyz), 3))
        elif isinstance(self.point_cloud_data, tuple) and len(self.point_cloud_data) == 2:
            # It's a tuple of (points_array, colors_array)
            points_array, colors_array = self.point_cloud_data
            self.points_xyz = np.asarray(points_array)
            self.points_rgb = (
                np.asarray(colors_array)
                if colors_array is not None
                else np.empty((len(self.points_xyz), 3))
            )
            pcd = None  # We've already processed the arrays
        else:
            raise ValueError(f"Unsupported point_cloud_data format: {type(self.point_cloud_data)}")

        # Apply preprocessing if configured
        if (
            hasattr(self, "dilute_pointcloud")
            and self.dilute_pointcloud
            and hasattr(self, "dilution_factor")
            and self.dilution_factor > 1
        ):
            indices = np.arange(0, len(self.points_xyz), self.dilution_factor)
            self.points_xyz = self.points_xyz[indices]
            self.points_rgb = (
                self.points_rgb[indices] if len(self.points_rgb) > 0 else self.points_rgb
            )

        # Round coordinates for precision consistency
        self.points_xyz = np.round(self.points_xyz, 3)

        self._log(f"Prepared point cloud with {len(self.points_xyz)} points")
        if len(self.points_rgb) > 0:
            self._log("Color data is available")

    def _identify_slabs(self):
        """Identifies slabs from the point cloud."""
        from .aux_functions import identify_slabs  # Function is defined in aux_functions.py

        self._log("Starting slab segmentation...")
        # Ensure points_rgb is passed if your identify_slabs function expects it,
        # otherwise, you might need to pass None or an empty array of the correct shape.
        # If points_rgb is not consistently populated, handle it:
        current_points_rgb = self.points_rgb if self.points_rgb.size > 0 else None

        slabs, horizontal_surface_planes = identify_slabs(
            self.points_xyz,
            current_points_rgb,  # Pass potentially None or empty RGB data
            self.bfs_thickness,
            self.tfs_thickness,
            z_step=0.15,  # Consider making this configurable
            pc_resolution=self.pc_resolution,
            plot_segmented_plane=False,  # Ensure plotting is off
        )
        self.slabs = slabs
        # self.horizontal_surface_planes = horizontal_surface_planes # Store if needed later
        self._log(f"Slab segmentation completed. Found {len(self.slabs)} slabs.")
        if not self.slabs:
            self._log(
                "Warning: No slabs were identified. Subsequent steps might fail or produce empty results."
            )
            # Decide if this is a critical error that should stop processing
            # raise ValueError("No slabs identified, cannot proceed.")

    def _identify_walls_and_openings(self):
        """Identifies walls and openings for each storey."""
        from .aux_functions import (
            identify_walls,
            identify_openings,
            split_pointcloud_to_storeys,
        )  # Functions are defined in aux_functions.py

        self._log("Starting wall and opening segmentation...")
        if not self.slabs:
            self._log("Skipping wall and opening segmentation as no slabs were found.")
            return

        point_cloud_storeys = split_pointcloud_to_storeys(self.points_xyz, self.slabs)

        wall_id_counter = 0
        processed_walls = []
        processed_openings = []

        for i, storey_pointcloud in enumerate(point_cloud_storeys):
            self._log(f"Processing storey {i+1} for walls and openings.")
            if storey_pointcloud is None or len(storey_pointcloud) == 0:
                self._log(f"Storey {i+1} has no points. Skipping.")
                continue

            # Determine z_placement and wall_height based on slab information
            # This logic is copied from the original script and might need refinement
            # based on how slabs are structured and indexed.
            # Ensure slabs list has enough elements for i and i+1 access.
            if i + 1 >= len(self.slabs):  # Check if there's a slab above the current one
                self._log(
                    f"Warning: Not enough slab data to determine wall height for storey {i+1} based on slab {i+1}. Using estimated height or skipping."
                )
                # Potentially estimate height or skip this storey for wall detection
                # For now, let's assume a default or skip if critical info is missing
                if i == len(point_cloud_storeys) - 1:  # Topmost storey
                    if self.exterior_scan:
                        z_placement = (
                            self.slabs[i]["slab_bottom_z_coord"] + self.slabs[i]["thickness"]
                        )
                        # Estimate height for the topmost storey if no slab above
                        # This is a placeholder, actual logic might be more complex
                        wall_height = self.config.get("default_top_storey_height", 3.0)
                    else:
                        z_placement = self.slabs[i]["slab_bottom_z_coord"]
                        wall_height = (
                            self.slabs[i]["thickness"] + self.tfs_thickness
                        )  # Approximation
                else:  # Should not happen if i+1 >= len(self.slabs)
                    continue
            else:  # Normal case with slabs below and above (or top defined by last slab)
                if self.exterior_scan:
                    z_placement = self.slabs[i]["slab_bottom_z_coord"] + self.slabs[i]["thickness"]
                    wall_height = self.slabs[i + 1]["slab_bottom_z_coord"] - z_placement
                else:
                    if i == 0:  # First storey
                        z_placement = self.slabs[i]["slab_bottom_z_coord"]
                        if i == len(point_cloud_storeys) - 1:  # Single storey building
                            wall_height = (
                                self.slabs[i + 1]["slab_bottom_z_coord"]
                                - z_placement
                                + self.tfs_thickness
                                if (i + 1 < len(self.slabs))
                                else self.slabs[i]["thickness"] + self.tfs_thickness
                            )
                        else:  # Multi-storey, first floor
                            wall_height = self.slabs[i + 1]["slab_bottom_z_coord"] - z_placement
                    elif i == len(point_cloud_storeys) - 1:  # Last storey (but not single storey)
                        z_placement = (
                            self.slabs[i]["slab_bottom_z_coord"] + self.slabs[i]["thickness"]
                        )
                        wall_height = (
                            self.slabs[i + 1]["slab_bottom_z_coord"]
                            - z_placement
                            + self.tfs_thickness
                            if (i + 1 < len(self.slabs))
                            else self.slabs[i]["thickness"] + self.tfs_thickness
                        )  # Approx if no slab above
                    else:  # Intermediate storeys
                        z_placement = self.slabs[i]["slab_bottom_z_coord"] + self.slabs[i]["thickness"]
                        wall_height = (
                            self.slabs[i + 1]["slab_bottom_z_coord"]
                            - z_placement
                            + self.slabs[i + 1]["thickness"]
                        )

            top_z_placement = (
                self.slabs[i + 1]["slab_bottom_z_coord"]
                if i + 1 < len(self.slabs)
                else z_placement + wall_height
            )

            # Ensure slab polygon is available for identify_walls
            current_slab_polygon = (
                self.slabs[i + 1]["polygon"]
                if i + 1 < len(self.slabs) and "polygon" in self.slabs[i + 1]
                else None
            )
            if current_slab_polygon is None:
                self._log(
                    f"Warning: Slab polygon for storey {i+1} (slab index {i+1}) not found. Wall detection might be affected."
                )
                # Potentially skip or use a bounding box of the point cloud as a fallback
                # For now, passing None, assuming identify_walls can handle it or it's not critical for all cases

            (
                start_points,
                end_points,
                wall_thicknesses,
                wall_materials,
                translated_filtered_rotated_wall_groups,
                wall_labels,
                wall_groups_indices,
            ) = identify_walls(
                storey_pointcloud,
                self.pc_resolution,
                self.min_wall_length,
                self.min_wall_thickness,
                self.max_wall_thickness,
                z_placement,
                top_z_placement,
                self.grid_coefficient,
                current_slab_polygon,  # Pass the polygon of the slab *above* the walls being detected
                self.exterior_scan,
                exterior_walls_thickness=self.exterior_walls_thickness,
            )
            self._log(f"Storey {i+1}: Identified {len(start_points)} wall segments.")

            for j in range(len(start_points)):
                wall_id_counter += 1
                wall_data = {
                    "wall_id": wall_id_counter,
                    "storey": i + 1,
                    "start_point": start_points[j],
                    "end_point": end_points[j],
                    "thickness": wall_thicknesses[j],
                    "material": wall_materials[j],
                    "z_placement": z_placement,
                    "height": wall_height,
                    "label": wall_labels[j],
                    "point_indices": wall_groups_indices[j],
                }
                processed_walls.append(wall_data)

                (opening_widths, opening_heights, opening_types) = identify_openings(
                    j + 1,  # Wall index within the storey
                    translated_filtered_rotated_wall_groups[j],
                    wall_labels[j],
                    self.pc_resolution,
                    self.grid_coefficient,
                    min_opening_width=self.config.get("min_opening_width", 0.4),
                    min_opening_height=self.config.get("min_opening_height", 0.6),
                    max_opening_aspect_ratio=self.config.get("max_opening_aspect_ratio", 4),
                    door_z_max=self.config.get("door_z_max", 0.1),
                    door_min_height=self.config.get("door_min_height", 1.6),
                    opening_min_z_top=self.config.get("opening_min_z_top", 1.6),
                    plot_histograms_for_openings=False,  # Ensure plotting is off
                )

                for (x_start, x_end), (z_min, z_max), opening_type in zip(
                    opening_widths, opening_heights, opening_types
                ):
                    opening_info = {
                        "opening_wall_id": wall_id_counter,  # Link to the global wall ID
                        "opening_type": opening_type,
                        "x_range_start": x_start,
                        "x_range_end": x_end,
                        "z_range_min": z_min,
                        "z_range_max": z_max,
                    }
                    processed_openings.append(opening_info)
                self._log(
                    f"Storey {i+1}, Wall {j+1} (Global ID {wall_id_counter}): Found {len(opening_widths)} openings."
                )

        self.walls = processed_walls
        self.all_openings = processed_openings
        self._log("Wall and opening segmentation completed for all storeys.")

    def _identify_zones(self):
        """Identifies zones (spaces) within each storey based on walls."""
        # from .space_generator import identify_zones # Already imported at class level
        self._log("Starting zone segmentation...")
        if not self.walls:
            self._log("Skipping zone segmentation as no walls were identified.")
            return

        # Group walls by storey for zone identification
        walls_by_storey = {}
        for wall in self.walls:
            storey_num = wall["storey"]
            if storey_num not in walls_by_storey:
                walls_by_storey[storey_num] = []
            walls_by_storey[storey_num].append(wall)

        processed_zones = []  # This will be a list of dictionaries, one per storey
        for storey_num in sorted(walls_by_storey.keys()):
            storey_walls = walls_by_storey[storey_num]
            self._log(f"Identifying zones for storey {storey_num} with {len(storey_walls)} walls.")
            # The original script appends results from identify_zones directly.
            # identify_zones likely returns a dictionary of zones for *that* storey.
            zones_in_storey = identify_zones(
                storey_walls,
                snapping_distance=self.config.get("zone_snapping_distance", 0.8),
                plot_zones=False,  # Ensure plotting is off
            )
            if zones_in_storey:
                # Store zones with their storey index.
                # The original `zones.append(zones_in_storey)` created a list of these dicts.
                # We need to ensure the structure matches what IFC generation expects.
                # If IFC part expects zones[idx] to be the zones for storey idx+1,
                # we need to pad `processed_zones` if some storeys have no zones.
                # For now, let's assume a direct list is fine, and IFC part handles indexing.
                processed_zones.append(zones_in_storey)  # Appends the dict for the current storey
            else:
                processed_zones.append({})  # Append an empty dict if no zones found for this storey
            self._log(f"Storey {storey_num}: Identified {len(zones_in_storey)} zones.")

        self.zones = (
            processed_zones  # self.zones is now a list of dicts, matching original structure
        )
        self._log("Zone segmentation completed.")

    def _generate_ifc_model(self):
        """Generates the IFC model from the segmented entities."""
        self._log("Starting IFC model generation...")
        if not self.slabs and not self.walls:
            self._log("Skipping IFC generation as no slabs or walls were identified.")
            return

        self.ifc_model = IFCmodel(self.ifc_project_name, self.ifc_output_file)
        self.ifc_model.define_author_information(
            f"{self.ifc_author_name} {self.ifc_author_surname}", self.ifc_author_organization
        )
        self.ifc_model.define_project_data(
            self.ifc_building_name,
            self.ifc_building_type,
            self.ifc_building_phase,
            self.ifc_project_long_name,
            self.ifc_project_version,
            self.ifc_author_organization,
            self.ifc_author_name,
            self.ifc_author_surname,
            self.ifc_site_latitude,
            self.ifc_site_longitude,
            self.ifc_site_elevation,
        )

        storeys_ifc = []
        # Add Slabs and Storeys
        for idx, slab_data in enumerate(self.slabs):
            slab_position = slab_data["slab_bottom_z_coord"] + slab_data["thickness"]
            ifc_storey = self.ifc_model.create_building_storey(
                f"Floor {slab_position:.2f}m", slab_position
            )
            storeys_ifc.append(ifc_storey)

            points = [
                [float(x), float(y)]
                for x, y in zip(slab_data["polygon_x_coords"], slab_data["polygon_y_coords"])
            ]
            points_no_duplicates = [list(pt) for pt in dict.fromkeys(tuple(p) for p in points)]

            slab_entity = self.ifc_model.create_slab(
                slab_name=f"Slab {idx + 1}",
                points=points_no_duplicates,
                slab_z_position=round(slab_data["slab_bottom_z_coord"], 3),
                slab_height=round(slab_data["thickness"], 3),
                material_name=self.material_for_objects,
            )
            self.ifc_model.assign_product_to_storey(slab_entity, ifc_storey)

            # Add Zones (Spaces)
            # self.zones is a list of dictionaries, where each dictionary contains zones for a storey.
            # The index idx corresponds to the current slab/storey.
            if idx < len(self.zones) and self.zones[idx]:  # Check if zones exist for this storey
                ifc_space_placement = self.ifc_model.space_placement(slab_position)
                # Original code: if idx != len(slabs) - 1: # avoid creating zones on the uppermost slab
                # This condition might need re-evaluation. If uppermost slab means roof, then yes.
                # If it's the top floor slab, zones might still be relevant.
                # For now, keeping similar logic:
                if (
                    idx < len(self.slabs) - 1
                ):  # Avoid creating spaces above the last "floor" slab, assuming last slab is roof.
                    # Or, if zones are defined for the top storey, this check might be too restrictive.
                    # Let's assume zones[idx] corresponds to storey created from slabs[idx]
                    zone_number = 1
                    for space_name, space_data in self.zones[idx].items():
                        # Ensure space_data contains "height"
                        space_height = space_data.get("height")
                        if space_height is None:
                            self._log(
                                f"Warning: Space {space_name} in storey {idx+1} is missing 'height'. Skipping space creation."
                            )
                            continue

                        self.ifc_model.create_space(
                            space_data,
                            ifc_space_placement,
                            (idx + 1),  # Storey number
                            zone_number,
                            ifc_storey,  # Assign to current IFC storey
                            space_height,
                        )
                        zone_number += 1
        self._log(f"Added {len(self.slabs)} slabs and associated storeys/zones to IFC.")

        # Add Walls and Openings
        # Counters for opening IDs (may be used in future iterations)
        # window_id_counter = 1
        # door_id_counter = 1

        # Wall definition for IFC
        for wall in self.walls:
            start_point = tuple(float(num) for num in wall["start_point"])
            end_point = tuple(float(num) for num in wall["end_point"])
            if start_point == end_point:
                continue
            wall_thickness = wall["thickness"]
            wall_material = wall["material"]
            wall_z_placement = wall["z_placement"]
            wall_heights = wall["height"]
            wall_label = wall["label"]

            wall_openings = [
                opening
                for opening in self.all_openings
                if opening["opening_wall_id"] == wall["wall_id"]
            ]

            # Create a material layer
            material_layer = self.ifc_model.create_material_layer(wall_thickness, wall_material)
            # Create an IfcMaterialLayerSet using the material layer (in a list)
            print(
                f"Creating material layer for wall {wall['wall_id']} with thickness {wall_thickness} and material '{wall_material}'"
            )
            material_layer_set = self.ifc_model.create_material_layer_set([material_layer])
            # Create an IfcMaterialLayerSetUsage and associate it with the element or product
            material_layer_set_usage = self.ifc_model.create_material_layer_set_usage(
                material_layer_set, wall_thickness
            )
            # Local placement
            wall_placement = self.ifc_model.wall_placement(wall["z_placement"])
            wall_axis_placement = self.ifc_model.wall_axis_placement(start_point, end_point)
            wall_axis_representation = self.ifc_model.wall_axis_representation(wall_axis_placement)
            wall_swept_solid_representation = self.ifc_model.wall_swept_solid_representation(
                start_point, end_point, wall_heights, wall_thickness
            )
            product_definition_shape = self.ifc_model.product_definition_shape(
                wall_axis_representation, wall_swept_solid_representation
            )
            current_story = wall["storey"]
            wall = self.ifc_model.create_wall(wall_placement, product_definition_shape)
            assign_material = self.ifc_model.assign_material(wall, material_layer_set_usage)
            wall_type = self.ifc_model.create_wall_type(wall, wall_thickness)
            assign_material_2 = self.ifc_model.assign_material(wall_type[0], material_layer_set)
            assign_object = self.ifc_model.assign_product_to_storey(
                wall, storeys_ifc[current_story - 1]
            )
            wall_ext_int_parameter = self.ifc_model.create_property_single_value(
                "IsExternal", wall_label == "exterior"
            )
            self.ifc_model.create_property_set(wall, wall_ext_int_parameter, "wall properties")

            # Create materials
            window_material, window_material_def_rep = self.ifc_model.create_material_with_color(
                "Window material", self.window_colour_rgb, transparency=0.7
            )

            door_material, door_material_def_rep = self.ifc_model.create_material_with_color(
                "Door material", self.door_colour_rgb
            )

            # Initialize ID counters
            window_id = 1
            door_id = 1

            for opening in wall_openings:
                # Each 'opening' is a dictionary with the opening data
                opening_type = opening["opening_type"]
                x_range_start = opening["x_range_start"]
                x_range_end = opening["x_range_end"]
                z_range_min = opening["z_range_min"]
                z_range_max = opening["z_range_max"]

                # Assign unique ID based on opening type
                if opening_type == "window":
                    opening_id = f"W{window_id:02d}"  # Format as W01, W02, ...
                    window_id += 1
                elif opening_type == "door":
                    opening_id = f"D{door_id:02d}"  # Format as D01, D02, ...
                    door_id += 1
                else:
                    print(f"Warning: Unknown opening type: {opening_type}, skipping this opening")
                    continue

                # Store the ID in the opening dictionary
                opening["wall_id"] = opening_id

                opening_width = x_range_end - x_range_start
                opening_height = z_range_max - z_range_min
                window_sill_height = z_range_min
                offset_from_start = x_range_start

                opening_closed_profile = self.ifc_model.opening_closed_profile_def(
                    float(opening_width), wall_thickness
                )
                opening_placement = self.ifc_model.opening_placement(start_point, wall_placement)
                opening_extrusion = self.ifc_model.opening_extrusion(
                    opening_closed_profile,
                    float(opening_height),
                    start_point,
                    end_point,
                    float(window_sill_height),
                    float(offset_from_start),
                )
                opening_representation = self.ifc_model.opening_representation(opening_extrusion)
                opening_product_definition = self.ifc_model.product_definition_shape_opening(
                    opening_representation
                )
                wall_opening = self.ifc_model.create_wall_opening(
                    opening_placement[1], opening_product_definition
                )
                rel_voids_element = self.ifc_model.create_rel_voids_element(wall, wall_opening)
                if opening_type == "window":
                    window_closed_profile = self.ifc_model.opening_closed_profile_def(
                        float(opening_width), 0.01
                    )
                    window_extrusion = self.ifc_model.opening_extrusion(
                        window_closed_profile,
                        float(opening_height),
                        start_point,
                        end_point,
                        float(window_sill_height),
                        float(offset_from_start),
                    )
                    window_representation = self.ifc_model.opening_representation(window_extrusion)
                    window_product_definition = self.ifc_model.product_definition_shape_opening(
                        window_representation
                    )
                    window = self.ifc_model.create_window(
                        opening_placement[1], window_product_definition, opening_id
                    )
                    window_type = self.ifc_model.create_window_type()
                    self.ifc_model.create_rel_defines_by_type(window, window_type)
                    self.ifc_model.create_rel_fills_element(wall_opening, window)
                    self.ifc_model.assign_product_to_storey(window, storeys_ifc[current_story - 1])
                    self.ifc_model.assign_material(window, window_material)
                elif opening_type == "door":
                    door_closed_profile = self.ifc_model.opening_closed_profile_def(
                        float(opening_width), 0.01
                    )
                    door_extrusion = self.ifc_model.opening_extrusion(
                        door_closed_profile,
                        float(opening_height),
                        start_point,
                        end_point,
                        float(window_sill_height),
                        float(offset_from_start),
                    )
                    door_representation = self.ifc_model.opening_representation(door_extrusion)
                    door_product_definition = self.ifc_model.product_definition_shape_opening(
                        door_representation
                    )
                    door = self.ifc_model.create_door(
                        opening_placement[1], door_product_definition, opening_id
                    )
                    self.ifc_model.create_rel_fills_element(wall_opening, door)
                    self.ifc_model.assign_product_to_storey(door, storeys_ifc[current_story - 1])
                    self.ifc_model.assign_material(door, door_material)

        self._log(f"Added {len(self.walls)} walls and {len(self.all_openings)} openings to IFC.")

        # Write IFC File
        self.ifc_model.write()
        print(f"IFC model written to {self.ifc_output_file}")
        self._log(f"IFC model saved to {self.ifc_output_file}.")

    def _save_point_mapping(self):
        """
        Save the mapping between point cloud indices and IFC elements.
        This is useful for visualization and validation.
        The JSON is pretty-printed, but all "points" arrays are written in a single line.
        Maps point cloud indices to IFC entities using the actual IFC entity IDs.
        """
        import re
        import numpy as np
        mapping = {"slabs": {}, "walls": {}, "openings": {}}

        # Add mapping for slabs
        for idx, slab in enumerate(self.slabs):
            slab_id = str(slab.get('ifc_id', f'slab_{idx+1}'))  # Use IFC ID if available
            if "point_indices" in slab:
                mapping["slabs"][slab_id] = {
                    "points": slab["point_indices"].tolist()[:300],
                    "height": slab["slab_bottom_z_coord"],
                    "thickness": slab["thickness"],
                    "ifc_type": slab.get("ifc_type", "IfcSlab")
                }

        # Add mapping for walls
        for wall in self.walls:
            wall_id = str(wall.get('ifc_id', f'wall_{wall["wall_id"]}'))  # Use IFC ID if available
            if "point_indices" in wall:
                mapping["walls"][wall_id] = {
                    "points": wall["point_indices"][:300],
                    "storey": wall["storey"],
                    "thickness": wall["thickness"],
                    "label": wall["label"],
                    "ifc_type": wall.get("ifc_type", "IfcWall")
                }

        # Add mapping for openings
        for idx, opening in enumerate(self.all_openings):
            opening_id = str(opening.get('ifc_id', f'{opening["opening_type"]}_{idx+1}'))  # Use IFC ID if available
            if "point_indices" in opening:
                mapping["openings"][opening_id] = {
                    "points": opening["point_indices"].tolist(),
                    "wall_id": opening["opening_wall_id"],
                    "type": opening["opening_type"],
                    "ifc_type": opening.get("ifc_type", "IfcOpeningElement")
                }

        def _convert_numpy_types(obj):
            """Recursively convert numpy types to native Python types for JSON serialization."""
            if isinstance(obj, dict):
                return {k: _convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_convert_numpy_types(i) for i in obj]
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            else:
                return obj

        def _format_json_with_compact_points(obj):
            """Format JSON with pretty-printing but keep points arrays in single lines."""
            points_arrays = {}
            
            def _process_dict(d):
                result = {}
                for k, v in d.items():
                    if k == "points" and isinstance(v, (list, np.ndarray)):
                        placeholder = f"__POINTS_{len(points_arrays)}__"
                        points_arrays[placeholder] = json.dumps(v)
                        result[k] = placeholder
                    elif isinstance(v, dict):
                        result[k] = _process_dict(v)
                    else:
                        result[k] = v
                return result
            
            native_obj = _convert_numpy_types(obj)
            processed = _process_dict(native_obj)
            pretty_json = json.dumps(processed, indent=2)
            
            for placeholder, points_array in points_arrays.items():
                pretty_json = pretty_json.replace(f'"{placeholder}"', points_array)
            
            return pretty_json

        try:
            with open(self.point_mapping_file, "w") as f:
                formatted_json = _format_json_with_compact_points(mapping)
                f.write(formatted_json)
            self._log(f"Point mapping saved to {self.point_mapping_file}")
        except Exception as e:
            self._log(f"Error saving point mapping: {e}", level="error")

    def process(self):
        """
        Executes the full point cloud to IFC conversion process.
        Returns None on success, raises exception on failure.
        """
        try:
            self._log("Processing started.")
            self._update_progress("Processing started", 35)

            # 1. Load and prepare point cloud
            self._log("Loading and preparing point cloud...")
            self._update_progress("Loading and preparing point cloud", 40)
            self._load_and_prepare_point_cloud()
            if self.points_xyz.size == 0:
                raise ValueError("Point cloud is empty after loading")
            self._log(f"Point cloud loaded with {self.points_xyz.shape[0]} points")

            # 2. Identify slabs (floors and ceilings)
            self._log("Identifying slabs...")
            self._update_progress("Identifying slabs (floors and ceilings)", 50)
            self._identify_slabs()
            if not self.slabs:
                raise ValueError("No slabs identified in point cloud")
            self._log(f"{len(self.slabs)} slabs identified")

            # 3. Identify walls and openings
            self._log("Identifying walls and openings...")
            self._update_progress("Identifying walls and openings", 60)
            self._identify_walls_and_openings()
            self._log(f"{len(self.walls)} walls and {len(self.all_openings)} openings identified")

            # 4. Identify zones (rooms/spaces)
            self._log("Identifying zones...")
            self._update_progress("Identifying zones (rooms/spaces)", 70)
            self._identify_zones()
            num_zones = sum(len(zones_dict) for zones_dict in self.zones)
            self._log(f"{num_zones} zones identified across all storeys")

            # 5. Generate IFC model
            self._log("Generating IFC model...")
            self._update_progress("Generating IFC model", 80)
            self._generate_ifc_model()
            self._log(f"IFC model generated at {self.ifc_output_file}")

            # 6. Save point-to-element mapping
            self._log("Saving point-to-element mapping...")
            self._update_progress("Saving point-to-element mapping", 85)
            self._save_point_mapping()

            self._log("Processing completed successfully")

        except Exception as e:
            self._log(f"Error during processing: {str(e)}", level="error")
            logger.exception(f"Job {self.job_id}: Full traceback for error during processing")
            raise


# === Remove the old script execution logic below this line ===
# All the code that was previously global (reading files, calling functions)
# should now be part of the CloudToBimProcessor class methods or
# handled by the job_processor.py which will instantiate and run this class.

# Example of how job_processor.py might use this:
# from .cloud2entities import CloudToBimProcessor
#
# def process_conversion_job(job_id: str, config_data: dict, input_dir: str, output_dir: str):
#     processor = CloudToBimProcessor(job_id, config_data, input_dir, output_dir)
#     success, result_or_error = processor.process()
#     if success:
#         # Update job status to completed, store result_or_error (IFC path)
#         pass
#     else:
#         # Update job status to failed, store result_or_error (error message)
#         pass


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
        with open(file_path, "r") as f:
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
                                r, g, b = r / 255.0, g / 255.0, b / 255.0
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


if __name__ == "__main__":
    # This block is for testing purposes only. In production, this module would be imported and used by job_processor.py.
    import sys

    # Add the app directory to the Python path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    # Example usage of CloudToBimProcessor
    if len(sys.argv) < 2:
        print("Usage: python run_cloud2entities.py <config_file>")
        sys.exit(1)

    config_file = sys.argv[1]

    # Load configuration (assuming a function load_config_and_variables exists)
    config = load_config_and_variables_new(config_path=config_file)

    pcl = read_custom_ptx("/home/fothar/Cloud2BIM_web/tests/data/scan6.ptx")

    processor = CloudToBimProcessor(
        job_id="example-job",
        config_data=config,
        output_dir="/home/fothar/Cloud2BIM_web/tests/data/output_xyz",
        point_cloud_data=pcl,
    )

    processor.process()
