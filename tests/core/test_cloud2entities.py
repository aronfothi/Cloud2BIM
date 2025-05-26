import unittest
import os
import tempfile
import numpy as np
import open3d as o3d
import ifcopenshell  # Added import
from app.core.cloud2entities import _read_ptx_as_text, detect_elements  # Added detect_elements
from app.core.aux_functions import load_config_and_variables  # Added import


class TestPtxTextReader(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory to hold test files
        self.test_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.test_dir.cleanup)

    def _create_temp_ptx_file(self, filename: str, content: str) -> str:
        filepath = os.path.join(self.test_dir.name, filename)
        with open(filepath, "w") as f:
            f.write(content)
        return filepath

    def test_read_ptx_xyz_intensity(self):
        """Test reading a PTX file with X, Y, Z, and Intensity."""
        ptx_content = """
10
1
1.0 0.0 0.0 0.0
0.0 1.0 0.0 0.0
0.0 0.0 1.0 0.0
0.0 0.0 0.0 1.0
1.000 2.000 3.000 0.5
4.000 5.000 6.000 0.8
        """
        filepath = self._create_temp_ptx_file("test_xyz_intensity.ptx", ptx_content)
        pcd = _read_ptx_as_text(filepath)

        self.assertIsNotNone(pcd, "Point cloud should not be None for valid PTX.")
        self.assertTrue(pcd.has_points(), "Point cloud should have points.")
        self.assertEqual(len(pcd.points), 2, "Should parse 2 points.")

        expected_points = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        np.testing.assert_array_almost_equal(np.asarray(pcd.points), expected_points, decimal=3)

        self.assertTrue(np.array_equal(pcd.points, expected_points))
        self.assertFalse(pcd.has_colors(), "Point cloud should not have colors for this file.")

    def test_read_ptx_xyz_rgb_only(self):
        """Test reading a PTX file with only X, Y, Z, R, G, B."""
        ptx_content = """
10
1
1.0 0.0 0.0 0.0
0.0 1.0 0.0 0.0
0.0 0.0 1.0 0.0
0.0 0.0 0.0 1.0
1.0 2.0 3.0 0.5 10 20 30
4.0 5.0 6.0 0.8 40 50 60
        """
        filepath = self._create_temp_ptx_file("test_xyz_rgb_only.ptx", ptx_content)
        pcd = _read_ptx_as_text(filepath)

        self.assertIsNotNone(pcd)
        self.assertTrue(pcd.has_points())
        self.assertEqual(len(pcd.points), 2)

        expected_points = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
        np.testing.assert_array_almost_equal(np.asarray(pcd.points), expected_points, decimal=3)

        self.assertTrue(pcd.has_colors())
        expected_colors = np.array(
            [[10 / 255.0, 20 / 255.0, 30 / 255.0], [40 / 255.0, 50 / 255.0, 60 / 255.0]]
        )
        np.testing.assert_array_almost_equal(np.asarray(pcd.colors), expected_colors, decimal=3)

    def test_read_ptx_empty_file(self):
        """Test reading an empty PTX file."""
        ptx_content = """"""
        filepath = self._create_temp_ptx_file("empty.ptx", ptx_content)
        pcd = _read_ptx_as_text(filepath)
        self.assertIsNone(pcd, "Should return None for an empty file.")

    def test_read_ptx_header_only(self):
        """Test reading a PTX file with only a header."""
        ptx_content = """
2
1
0
0
0
0
0
0
0
0
        """
        filepath = self._create_temp_ptx_file("header_only.ptx", ptx_content)
        pcd = _read_ptx_as_text(filepath)
        # The current implementation might return None or an empty point cloud.
        # Expecting None as no valid point data lines are found.
        self.assertIsNone(pcd, "Should return None if no point data lines are found after header.")

    def test_read_ptx_standard_header_format(self):
        """Test with a more standard PTX header (2 lines dims, 4x4 matrix)"""
        ptx_content = """
2
1
1.000000 0.000000 0.000000 0.000000
0.000000 1.000000 0.000000 0.000000
0.000000 0.000000 1.000000 0.000000
0.000000 0.000000 0.000000 1.000000
1.1 2.2 3.3 0.5 10 20 30
4.4 5.5 6.6 0.8 40 50 60
        """
        # Header is 2 (dims) + 4 (matrix) = 6 lines.
        # The parser's heuristic should ideally detect this.
        filepath = self._create_temp_ptx_file("standard_header.ptx", ptx_content)
        pcd = _read_ptx_as_text(filepath)

        self.assertIsNotNone(pcd)
        self.assertTrue(pcd.has_points())
        self.assertEqual(len(pcd.points), 2)
        expected_points = np.array([[1.1, 2.2, 3.3], [4.4, 5.5, 6.6]])
        np.testing.assert_array_almost_equal(np.asarray(pcd.points), expected_points, decimal=3)
        self.assertTrue(pcd.has_colors())
        expected_colors = np.array(
            [[10 / 255.0, 20 / 255.0, 30 / 255.0], [40 / 255.0, 50 / 255.0, 60 / 255.0]]
        )
        np.testing.assert_array_almost_equal(np.asarray(pcd.colors), expected_colors, decimal=3)

    def test_read_ptx_mixed_data_formats(self):
        """Test reading a PTX file with mixed data formats (should ideally handle or warn)."""
        # This case depends on how robust the parser is designed to be.
        # For now, we might expect it to fail or parse only valid lines.
        ptx_content = """
2
2
1.0 0.0 0.0 0.0
0.0 1.0 0.0 0.0
0.0 0.0 1.0 0.0
0.0 0.0 0.0 1.0
0.0 0.0 0.0 0.0
0.0 0.0 0.0 0.0
0.0 0.0 0.0 0.0
0.0 0.0 0.0 0.0
1 2 3 0.5
4 5 6 0.8 10 20 30
"""
        filepath = self._create_temp_ptx_file("mixed_data.ptx", ptx_content)
        pcd = _read_ptx_as_text(filepath)
        self.assertIsNotNone(pcd, "PCD should not be None even with mixed data.")
        self.assertTrue(len(pcd.points) > 0, "Should parse at least some points.")
        # More specific assertions depending on expected behavior (e.g., number of points)

    def test_read_real_scan6_ptx(self):
        """Test reading the real scan6.ptx file and check if points are loaded."""
        # Path to the actual scan6.ptx file.
        # This assumes the test is run from a context where this path is valid.
        # For CI/CD or different environments, this path might need to be relative
        # or managed via environment variables/configuration.
        filepath = "/home/fothar/Cloud2BIM_web/tests/data/scan6.ptx"

        if not os.path.exists(filepath):
            self.skipTest(f"Test file not found: {filepath}. Skipping test.")
            return

        pcd = _read_ptx_as_text(filepath)

        self.assertIsNotNone(pcd, f"Point cloud should not be None for {filepath}.")
        self.assertTrue(pcd.has_points(), f"Point cloud from {filepath} should have points.")
        self.assertTrue(
            len(pcd.points) > 0, f"Number of points in {filepath} should be greater than 0."
        )
        # Optionally, log the number of points found for verification
        print(f"Successfully loaded {len(pcd.points)} points from {filepath}")


class TestSegmentationAndIFC(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = "/home/fothar/Cloud2BIM_web/tests/data"
        self.ptx_file_path = os.path.join(self.test_data_dir, "scan6.ptx")
        self.config_file_path = os.path.join(self.test_data_dir, "sample_config.yaml")

        if not os.path.exists(self.ptx_file_path):
            # unittest.skip automatically skips the test if this condition is met.
            # However, setUp is called for each test method. Raising an error might be
            # more direct if the file is absolutely essential for all tests in the class.
            # For a single test, self.skipTest in the test method itself is also an option.
            raise FileNotFoundError(
                f"Test PTX file not found: {self.ptx_file_path}. This test requires it."
            )
        if not os.path.exists(self.config_file_path):
            raise FileNotFoundError(
                f"Test config file not found: {self.config_file_path}. This test requires it."
            )

        self.output_dir_context = tempfile.TemporaryDirectory()
        self.output_dir = self.output_dir_context.name
        self.addCleanup(self.output_dir_context.cleanup)

    def test_segmentation_produces_two_slabs_from_scan6(self):
        """
        Tests the full segmentation and IFC generation process using scan6.ptx
        and sample_config.yaml. It verifies that exactly two slabs are created
        in the output IFC file.

        This test is EXPECTED TO FAIL until the 'detect_slabs' functionality
        is properly implemented in the core logic.
        """
        config_params = load_config_and_variables(self.config_file_path)
        self.assertIsNotNone(config_params, "Failed to load configuration.")

        # Ensure the config has the output filename, or handle default in detect_elements
        # Assuming sample_config.yaml contains:
        # General_Parameters:
        #   output_filename: "output.ifc"
        # If not, this part of the config might need adjustment or the test needs to set it.
        # For this test, we rely on the sample_config.yaml to provide it.

        ifc_file_path, point_mapping_path = detect_elements(
            pcd_path=self.ptx_file_path,  # Corrected argument name
            file_type="ptx",  # Added missing file_type argument
            config_params=config_params,
            output_dir=self.output_dir,
        )

        # ---- BEGIN ADDED DEBUG PRINTS ----
        print(f"DEBUG_TEST: Type of ifc_file_path: {type(ifc_file_path)}")
        print(
            f"DEBUG_TEST: Value of ifc_file_path: {ifc_file_path!r}"
        )  # Using !r for unambiguous representation
        print(f"DEBUG_TEST: Type of point_mapping_path: {type(point_mapping_path)}")
        print(f"DEBUG_TEST: Value of point_mapping_path: {point_mapping_path!r}")
        # ---- END ADDED DEBUG PRINTS ----

        self.assertTrue(
            os.path.exists(ifc_file_path), f"IFC file was not generated at {ifc_file_path}."
        )

        try:
            ifc_model = ifcopenshell.open(ifc_file_path)
        except Exception as e:
            self.fail(f"Failed to open generated IFC file '{ifc_file_path}': {e}")

        slabs = ifc_model.by_type("IfcSlab")

        # Log for debugging, especially since it's expected to fail initially
        print(f"Found {len(slabs)} IfcSlab entities in {ifc_file_path}.")
        if len(slabs) != 2 and os.path.exists(point_mapping_path):
            print(f"Point mapping file generated at: {point_mapping_path}")

        self.assertEqual(
            len(slabs),
            2,
            f"Expected 2 IfcSlab entities, but found {len(slabs)} in {ifc_file_path}.",
        )


if __name__ == "__main__":
    unittest.main()
