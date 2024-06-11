import unittest
from io import BytesIO
from ..pset import (
    Pset, PsetItem,
    PSET_TYPE_BOOL, PSET_TYPE_CHAR, PSET_TYPE_SHORT, PSET_TYPE_INT,
    PSET_TYPE_WIDE, PSET_TYPE_FILETIME, PSET_TYPE_FLOAT, PSET_TYPE_DOUBLE,
    PSET_TYPE_STRING, PSET_TYPE_BINARY, PSET_TYPE_KEY, PSET_TYPE_PSET)


class TestPsetItem(unittest.TestCase):

    def test_bool_zero_is_false(self):
        data = BytesIO(b'?\x00\x01\x80\x00')
        item = PsetItem.fromstream(data)
        self.assertEqual(item.opcode, PSET_TYPE_BOOL)
        self.assertEqual(item.key, 0x8001)
        self.assertFalse(item.value)

    def test_bool_is_true(self):
        data = BytesIO(b'?\x00\x01\x80\x01')
        item = PsetItem.fromstream(data)
        self.assertTrue(item.value)

    def test_bool_non_zero_is_true(self):
        data = BytesIO(b'?\x00\x01\x80\xff')
        item = PsetItem.fromstream(data)
        self.assertTrue(item.value)

    def test_bool_array(self):
        data = BytesIO(b'?\x80\x01\x80\x04\x00\x00\x00\xff\x00\x00\x01')
        item = PsetItem.fromstream(data)
        self.assertEqual(len(item.value), 4)
        self.assertSequenceEqual(item.value, (True, False, False, True))

    def test_short(self):
        item = PsetItem.fromstream(BytesIO(b's\x00\x01\x80\x0d\xf0'))
        self.assertEqual(item.opcode, PSET_TYPE_SHORT)
        self.assertEqual(item.value, -4083)

    def test_int(self):
        item = PsetItem.fromstream(BytesIO(b'i\x00\x01\x80\x04\x03\x02\x01'))
        self.assertEqual(item.opcode, PSET_TYPE_INT)
        self.assertEqual(item.value, 0x01020304)

    def test_float(self):
        item = PsetItem.fromstream(BytesIO(b'r\x00\x01\x80\x00\x00\x80?'))
        self.assertEqual(item.opcode, PSET_TYPE_FLOAT)
        self.assertEqual(item.value, 1.0)

    def test_double(self):
        item = PsetItem.fromstream(BytesIO(b'q\x00\x01\x80\0\0\0\0\0\0\xf0?'))
        self.assertEqual(item.opcode, PSET_TYPE_DOUBLE)
        self.assertEqual(item.value, 1.0)

    def test_string(self):
        item = PsetItem.fromstream(BytesIO(b'u\x00\x01\x80\5\0\0\0hello'))
        self.assertEqual(item.opcode, PSET_TYPE_STRING)
        self.assertEqual(item.value, "hello")

    def test_string_unicode(self):
        data = b'u\x00\x01\x80\x13\0\0\0\xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82'
        data = data + b' \xd0\xbc\xd0\xb8\xd1\x80'
        item = PsetItem.fromstream(BytesIO(data))
        self.assertEqual(item.opcode, PSET_TYPE_STRING)
        self.assertEqual(item.value, "привет мир")

    def test_key(self):
        item = PsetItem.fromstream(BytesIO(b'k\x00\x01\x80\6\0\0\0\xd0\xbc\xd0\xb8\xd1\x80'))
        self.assertEqual(item.opcode, PSET_TYPE_KEY)
        self.assertEqual(item.value, "мир")

    def test_pset(self):
        item = PsetItem.fromstream(BytesIO(b'p\x00\x01\x80\x0d\x00\x00\x00?\0\2\x80\1i\0\3\x80\x0a\0\0\0'))
        self.assertEqual(item.opcode, PSET_TYPE_PSET)
        self.assertEqual(len(item.value), 13)
        stream = BytesIO(item.value)
        subitem1 = PsetItem.fromstream(stream)
        subitem2 = PsetItem.fromstream(stream)
        self.assertEqual(subitem1.opcode, PSET_TYPE_BOOL)
        self.assertEqual(subitem2.opcode, PSET_TYPE_INT)
        self.assertEqual(subitem2.key, 0x8003)
        self.assertEqual(subitem2.value, 10)


class TestPset(unittest.TestCase):
    def test_simple_pset(self):
        """Check Pset.fromstream with a simple set that has predefined and custom defined items"""
        stream = BytesIO(b'PSET\x1D\0\0\0u\0\x9B\1\4\0\0\0name?\0\1\x80\1k\0\1\x80\4\0\0\0test')
        pset = Pset.fromstream(stream)
        self.assertEqual(len(pset.items), 2)
        self.assertEqual(pset.items['test'].key, 0x8001)
        self.assertEqual(pset.items['test'].value, True)
        self.assertEqual(pset.items['Label'].value, 'name')

    def test_simple_pset_key_before(self):
        """Check a PSET where a custom key name is defined before the value that uses it."""
        stream = BytesIO(b'PSET\x1D\0\0\0u\0\x9B\1\4\0\0\0namek\0\1\x80\4\0\0\0test?\0\1\x80\xff')
        pset = Pset.fromstream(stream)
        self.assertEqual(len(pset.items), 2)
        self.assertEqual(pset.items['test'].key, 0x8001)
        self.assertEqual(pset.items['test'].value, True)
        self.assertEqual(pset.items['Label'].value, 'name')

    def test_pset_get_item(self):
        stream = BytesIO(b'PSET\x1D\0\0\0u\0\x9B\1\4\0\0\0namek\0\1\x80\4\0\0\0test?\0\1\x80\xff')
        pset = Pset.fromstream(stream)
        self.assertEqual(pset['test'].value, True)
        self.assertEqual(pset['Label'].value, 'name')

    def test_pset_iter(self):
        stream = BytesIO(b'PSET\x1D\0\0\0u\0\x9B\1\4\0\0\0namek\0\1\x80\4\0\0\0test?\0\1\x80\xff')
        pset = Pset.fromstream(stream)
        asdict = dict(pset)
        self.assertIn('test', asdict)


if __name__ == '__main__':
    unittest.main()
