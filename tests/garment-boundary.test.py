"""Source geometry regression without Blender: python tests/garment-boundary.test.py."""
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace as NS
import sys
import unittest

# level_hem only needs graph topology, shape coordinates, and numpy. Stub the
# Blender-only imports so this test can run while Blender builds the real asset.
mathutils = ModuleType('mathutils')
mathutils.Vector = object
bvh = ModuleType('mathutils.bvhtree')
bvh.BVHTree = object
sys.modules['mathutils'] = mathutils
sys.modules['mathutils.bvhtree'] = bvh
spec = importlib.util.spec_from_file_location('fit_garments', Path(__file__).resolve().parents[1] / 'tools/fit-garments.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    # Torso rings, then a sleeve whose lowest tip is LOWER than the hem and whose
    # next row enters the repair height band. Sleeve average height stays higher.
    heights = [.945, .950, .960, .955] + [1.0]*4 + [1.04]*4 + [1.10]*4
    heights += [.93, 1.18, 1.18, 1.18] + [1.02, 1.22, 1.22, 1.22] + [1.25]*4
    faces = []
    for first, rings in [(0, 4), (16, 3)]:
        for ring in range(rings-1):
            for i in range(4):
                a = first+ring*4+i
                b = first+ring*4+(i+1)%4
                faces.append([a, b, b+4, a+4])
    # Join the two tubes above the transition. This is one connected garment,
    # not a disconnected sleeve that would trivially avoid a torso flood-fill.
    faces.append([12, 13, 25, 24])
    polygons = [NS(edge_keys=[tuple(sorted((face[i], face[(i+1)%len(face)]))) for i in range(len(face))]) for face in faces]
    keys = [NS(data=[NS(co=NS(x=i/100, y=-i/200, z=z+shift)) for i, z in enumerate(heights)]) for shift in [0, .002, -.002]]
    data = NS(vertices=[NS(co=NS(x=0,y=0,z=z)) for z in heights], polygons=polygons,
              shape_keys=NS(key_blocks=keys), update=lambda: None)
    return NS(data=data)


class HemBoundaryTest(unittest.TestCase):
    def test_only_whole_lowest_loop_and_its_connected_band_are_changed(self):
        shirt = fixture()
        before = [[(p.co.x,p.co.y,p.co.z) for p in key.data] for key in shirt.data.shape_keys.key_blocks]
        module.level_hem(shirt)
        for key, original in zip(shirt.data.shape_keys.key_blocks, before):
            for i in range(4):
                self.assertAlmostEqual(key.data[i].co.z, .955)
            for i in range(4,12):
                self.assertGreater(key.data[i].co.z, .955)
                self.assertLess(key.data[i].co.z, original[12][2])
            for i in range(12,28):
                self.assertEqual((key.data[i].co.x,key.data[i].co.y,key.data[i].co.z), original[i], f'Upper torso/sleeve vertex {i} changed')
            for i in range(28):
                self.assertEqual((key.data[i].co.x,key.data[i].co.y), original[i][:2])
            for i in range(4):
                self.assertLess(key.data[4+i].co.z, key.data[8+i].co.z)


if __name__ == '__main__':
    unittest.main()
