from struct import unpack
from os import SEEK_SET, SEEK_END, SEEK_CUR
from typing import BinaryIO, Any
from dataclasses import dataclass
from .predefinedKeys import getKeyName
from datetime import datetime, timezone, timedelta


PSET_FLAG_NONE = 0,
PSET_FLAG_COMPRESSED = 0x40,
PSET_FLAG_ARRAY = 0x80

PSET_TYPE_BOOL = ord(b'?')
PSET_TYPE_CHAR = ord(b'c')
PSET_TYPE_SHORT = ord('s')
PSET_TYPE_INT = ord(b'i')
PSET_TYPE_WIDE = ord(b'w')
PSET_TYPE_FLOAT = ord(b'r')
PSET_TYPE_DOUBLE = ord(b'q')
PSET_TYPE_FILETIME = ord(b't')
PSET_TYPE_PSET = ord(b'p')
PSET_TYPE_KEY = ord(b'k')
PSET_TYPE_BINARY = ord(b'b')
PSET_TYPE_STRING = ord(b'u')


class PsetParseError(Exception):
    """Exception raise during pset parsing."""
    def __init__(self, message):
        super(PsetParseError, self).__init__(message)


@dataclass
class PsetItem:
    """Representation of an item from a WDF property set.
    Each item is a name:value pair from a limited set of types."""
    opcode: int
    flags: int
    key: int
    value: Any = None

    @staticmethod
    def fromstream(stream: BinaryIO):
        """Returns an unpacked item from a wdf property set in
        a form appropriate for python.
        An array of data is returned in a tuple."""
        data = stream.read(4)
        item = PsetItem(*unpack('<BBH', data))
        count = 1
        if item.flags & PSET_FLAG_ARRAY:
            count = unpack('<I', stream.read(4))[0]
        if item.opcode == PSET_TYPE_BOOL:
            item.value = unpack(f'<{count}?', stream.read(1 * count))
        elif item.opcode == PSET_TYPE_CHAR:
            item.value = unpack(f'<{count}c', stream.read(1 * count))
        elif item.opcode == PSET_TYPE_SHORT:
            item.value = unpack(f'<{count}h', stream.read(2 * count))
        elif item.opcode == PSET_TYPE_INT:
            item.value = unpack(f'<{count}i', stream.read(4 * count))
        elif item.opcode == PSET_TYPE_WIDE:
            item.value = unpack(f'<{count}q', stream.read(8 * count))
        elif item.opcode == PSET_TYPE_FLOAT:
            item.value = unpack(f'<{count}f', stream.read(4 * count))
        elif item.opcode == PSET_TYPE_DOUBLE:
            item.value = unpack(f'<{count}d', stream.read(8 * count))
        elif item.opcode == PSET_TYPE_FILETIME:
            fileTimes = unpack(f'<{count}Q', stream.read(8 * count))
            item.value = ()
            for fileTime in fileTimes:
                # Convert from windows filetime to python datetime
                epoch = datetime(year=1601, month=1, day=1, tzinfo=timezone.utc)
                item.value = item.value + (epoch + timedelta(microseconds=fileTime / 10),)
        elif item.opcode == PSET_TYPE_STRING or item.opcode == PSET_TYPE_KEY:
            len = unpack('<I', stream.read(4))[0]
            item.value = stream.read(len).decode('utf-8'),
        elif item.opcode == PSET_TYPE_BINARY:
            len = unpack('<I', stream.read(4))[0]
            item.value = stream.read(len),
        elif item.opcode == PSET_TYPE_PSET:
            len = unpack('<I', stream.read(4))[0]
            item.value = stream.read(len),
        else:
            raise PsetParseError(f"invalid pset item type '{item.opcode}'")
        if count == 1:
            item.value = item.value[0]
        return item


class Pset:
    """Renishaw WDF file property collection parser."""
    def __init__(self, parent=None):
        self.parent = parent
        self.items = dict()

    def __getitem__(self, key):
        return self.items[key]

    def __iter__(self):
        for key in self.items.keys():
            yield key, self.items[key]

    @staticmethod
    def is_pset(stream: BinaryIO) -> bool:
        """Test a stream for an embedded property set.
        Reads 4 bytes from the stream. If the result is False it may be necessary
        to reposition the stream seek position"""
        magic = stream.read(4)
        return magic == b'PSET'

    @staticmethod
    def fromstream(stream: BinaryIO):
        """Parse a stream and return the Pset decoded or None"""
        result = None
        if Pset.is_pset(stream):
            size = unpack('<I', stream.read(4))[0]
            final = stream.tell() + size
            result = Pset()
            customKeyNames = {}
            customItems = {}
            while stream.tell() < final:
                item = PsetItem.fromstream(stream)
                # Check for custom keys or use predefined keys to name each PsetItem
                # The first bit of 16 bit custom key value is 1 (hence predefined key values are < 2^15)
                if (item.key >> 15) & 1:
                    if item.opcode == PSET_TYPE_KEY:
                        customKeyNames[item.key] = item.value
                    else:
                        customItems[item.key] = item
                else:
                    keyName = getKeyName(item.key)
                    result.items[keyName] = item
            # Saved custom key names/items construct name:item pairs in the returned dictionary
            for nameKey in customKeyNames:
                for itemKey in customItems:
                    if nameKey == itemKey:
                        result.items[customKeyNames[nameKey]] = customItems[itemKey]
        return result
