import unittest
import os
from tempfile import NamedTemporaryFile
from ..wdf import Wdf, MapData, MapAreaFlags
from ..origin import WdfOrigin, WdfDataType, WdfDataUnit
from ..pset import Pset, PsetItem
from .. import WdfBlockId


class TestWdf(unittest.TestCase):
    testfile = os.path.join(os.path.dirname(__file__), r'Si-map.wdf')

    def test_open(self):
        wdf = Wdf()
        wdf.open(self.testfile)
        wdf.close()

    def test_create(self):
        wdf = Wdf(self.testfile)
        wdf.close()

    def test_with_support(self):
        with Wdf(self.testfile):
            pass

    def test_open_size(self):
        with Wdf(self.testfile) as wdf:
            self.assertEqual(wdf.hdr.signature, WdfBlockId.FILE)
            self.assertEqual(wdf.hdr.nspectra, 88)
            self.assertEqual(wdf.hdr.npoints, 575)
            self.assertEqual(wdf.hdr.size, 512)

    def test_first_spectrum(self):
        with Wdf(self.testfile) as wdf:
            spectrum = wdf.spectrum(0)
            self.assertEqual(wdf.hdr.npoints, len(spectrum))
            self.assertSequenceEqual([1595, 1565, 1590, 1580], [int(x) for x in spectrum[0:4]])

    def test_find_block_hdr(self):
        with Wdf(self.testfile) as wdf:
            block, pos = wdf.find_section(WdfBlockId.FILE)
            self.assertEqual(pos, 0)
            self.assertEqual(block.id, WdfBlockId.FILE)
            self.assertEqual(block.size, 512)

    def test_find_block_xlist(self):
        with Wdf(self.testfile) as wdf:
            block = wdf.find_section(WdfBlockId.XLIST)[0]
            self.assertEqual(block.id, WdfBlockId.XLIST)

    def test_find_block_invalid(self):
        with Wdf(self.testfile) as wdf:
            self.assertRaises(EOFError, wdf.find_section, b'_z_z', 0)

    def test_xlist(self):
        with Wdf(self.testfile) as wdf:
            xlist = wdf.xlist()
            self.assertEqual(wdf.hdr.xlistcount, len(xlist))

    def test_comment(self):
        check = 'This is a mapping measurement created by the map setup wizard'
        with Wdf(self.testfile) as wdf:
            comment = wdf.comment()
            self.assertEqual(comment, check)

    def test_sections(self):
        with Wdf(self.testfile) as wdf:
            sections = [section.id for section in wdf.sections()]
            self.assertIn(WdfBlockId.FILE, sections)
            self.assertIn(WdfBlockId.MAPAREA, sections)
            self.assertIn(WdfBlockId.ORIGIN, sections)

    def test_iterator(self):
        with Wdf(self.testfile) as wdf:
            values = [int(x[0]) for x in wdf]
            self.assertEqual(len(values), wdf.hdr.nspectra)

    def test_indexing(self):
        with Wdf(self.testfile) as wdf:
            self.assertEqual(len(wdf[0]), wdf.hdr.npoints)
            self.assertEqual(len(wdf[1]), wdf.hdr.npoints)
            self.assertEqual(len(wdf[-1]), wdf.hdr.npoints)
            self.assertEqual(len(wdf[-2]), wdf.hdr.npoints)
            self.assertRaises(IndexError, wdf.__getitem__, wdf.hdr.nspectra)

    def test_len(self):
        with Wdf(self.testfile) as wdf:
            self.assertEqual(len(wdf), wdf.hdr.nspectra)

    def test_update_spectrum(self):
        with NamedTemporaryFile(suffix=".wdf") as tmpfd:
            with open(self.testfile, 'rb') as srcfd:
                data = None
                while not data or len(data) == 16384:
                    data = srcfd.read(16384)
                    tmpfd.write(data)
            tmpfd.seek(0, 0)
            with Wdf() as wdf:
                wdf.open_fd(tmpfd)
                expected = [100.0] * wdf.hdr.npoints
                # orig = wdf.spectrum(10)
                wdf.update_spectrum(10, expected)
                new = wdf.spectrum(10)
                self.assertSequenceEqual(new, expected)

    def test_get_map_data(self):
        with Wdf(self.testfile) as wdf:
            testMap = wdf.get_map_data()
            self.assertIsInstance(testMap, MapData)
            self.assertIsInstance(testMap.properties, Pset)
            self.assertEqual(testMap.label, 'Intensity At Point 520')
            self.assertEqual(len(testMap), wdf.hdr.nspectra)
            self.assertIsInstance(testMap[0:-1], tuple)
            # first and last, and 1 in from each end
            self.assertAlmostEqual(testMap[0], 44131.98828125, 6)
            self.assertAlmostEqual(testMap[-1], 44229.421875, 6)
            self.assertAlmostEqual(testMap[1], 43564.88671875, 6)
            self.assertAlmostEqual(testMap[-2], 44257.41796875, 6)
            # check the slice parsing is ok
            self.assertEqual(len(testMap[:]), len(testMap))
            self.assertEqual(len(testMap[0:]), len(testMap))
            self.assertEqual(len(testMap[0::2]), len(testMap) / 2)
            self.assertEqual(len(testMap[-8::2]), 4)

    def test_origins_valid(self):
        with Wdf(self.testfile) as wdf:
            self.assertEqual(len(wdf.origins), 5)
            self.assertIsInstance(wdf.origins[WdfDataType.Spatial_X], WdfOrigin)

    def test_origins_invalid(self):
        with Wdf(self.testfile) as wdf:
            self.assertRaises(KeyError, lambda: wdf.origins[WdfDataType.Pressure])

    def test_map_area(self):
        with Wdf(self.testfile) as wdf:
            area = wdf.map_area
            self.assertAlmostEqual(area.start.x, -7.090, 3)
            self.assertAlmostEqual(area.step.x, 2.0, 3)
            self.assertEqual(area.count.x, 8)
            self.assertEqual(area.flags, MapAreaFlags.NoFlag)

            self.assertEqual(area.count.y, 11)
            self.assertEqual(area.count.z, 0)


if __name__ == '__main__':
    unittest.main()
