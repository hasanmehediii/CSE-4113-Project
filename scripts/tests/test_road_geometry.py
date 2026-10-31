"""Offline geometry regressions: no shortcuts through bends or outside a corridor."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "road_geometry", Path(__file__).resolve().parents[1] / "import-road-geometry.py")
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)


class RoadGeometryTests(unittest.TestCase):
    def test_keeps_every_bend_in_a_way(self):
        points = [[1, 1], [2, 1], [2, 2], [3, 2]]
        self.assertEqual(geometry.clipped_paths(points, [0, 0, 4, 4]), [points])

    def test_leaving_and_reentering_box_does_not_draw_shortcut(self):
        points = [[1, 1], [2, 4], [3, 4], [4, 1]]
        paths = geometry.clipped_paths(points, [0, 0, 5, 2])
        self.assertEqual(len(paths), 2)
        self.assertEqual(paths[0][0], points[0])
        self.assertEqual(paths[1][-1], points[-1])
        self.assertEqual(paths[0][-1][1], 2)
        self.assertEqual(paths[1][0][1], 2)

    def test_outside_way_is_excluded(self):
        self.assertEqual(geometry.clipped_paths([[1, 3], [4, 3]], [0, 0, 5, 2]), [])


if __name__ == "__main__":
    unittest.main()
