"""
Data accessor classes for Renishaw WDF spectral data files.
"""


import struct
from dataclasses import dataclass
from io import BufferedReader, BytesIO
from collections import namedtuple
from enum import IntFlag, Enum
from os import SEEK_SET, SEEK_CUR
from typing import List
from .pset import Pset
from .origin import WdfOriginSet
from . import WdfBlockId


# All of the fields found in the wdf file header
_FIELDS = [
    'signature', 'version', 'size', 'flags',  # 'uuid', 'unused0', 'unused1'
    'ntracks', 'status', 'npoints', 'nspectra', 'ncollected', 'naccum',
    'ylistcount', 'xlistcount', 'origincount', 'appname_',
    'appver_maj', 'appver_min', 'appver_patch', 'appver_build',
    'scantype', 'type', 'time_start', 'time_end', 'units',
    'laser_wavenumber', 'user_', 'title_',
    # padding, free, reserved
]


def _tostr(data):
    """Convert a binary buffer with null terminated utf-8 encoded text to a string."""
    try:
        result = data.decode('utf-8').rstrip('\0')
    except UnicodeDecodeError:
        result = u''
    return result


class InvalidSectionError(Exception):
    """Error raised when an attempt is made to open an invalid section."""
    def __init__(self, message):
        super(InvalidSectionError, self).__init__(message)
        self.message = message


@dataclass
class WdfBlock:
    """Representation of the WDF section header structure."""
    id: int  # block type id (see WdfBlockId)
    uid: int  # unique id for this specific block (withing the id type set)
    size: int  # total size of the block (including the header size) in bytes
    position: int  # offset of this block in the file (start of header)

    _PACKFMT = '<IIQ'  # decoding format for a block header
    _SIZE = 16  # size of the block header in bytes

    @staticmethod
    def fromstream(stream: BytesIO) -> 'WdfBlock':
        position = stream.tell()
        data = stream.read(WdfBlock._SIZE)
        if len(data) != WdfBlock._SIZE:
            raise IOError()
        id, uid, size = struct.unpack(WdfBlock._PACKFMT, data)
        return WdfBlock(id, uid, size, position)


class WdfHeader(namedtuple('WdfHeader', _FIELDS)):
    """Representation of the WDF file header structure."""
    _packstr = '<IIQQ28x IIIQQI III24s4H IIQQI f48x32s160s 48x32x32x'
    _size = 512

    @property
    def appversion(self):
        return "%d.%d.%d.%d" % (self.appver_maj,
                                self.appver_min,
                                self.appver_patch,
                                self.appver_build)

    @property
    def title(self):
        return _tostr(self.title_)

    @property
    def user(self):
        return _tostr(self.user_)

    @property
    def appname(self):
        return _tostr(self.appname_)


class WdfIter:
    """Iterator for spectra in a WDF file."""
    def __init__(self, parent, index=0):
        self.wdf = parent
        self.index = index

    def next(self):
        """Python2 iterator support."""
        return self.__next__()

    def __next__(self):
        if self.index >= self.wdf.hdr.nspectra:
            raise StopIteration
        result = self.wdf[self.index]
        self.index += 1
        return result


class MapData:
    """Represent a map from the file."""

    def __init__(self, fd: BufferedReader, section: WdfBlock):
        self.fd = fd
        self.section = section
        self.fd.seek(section.position + WdfBlock._SIZE)
        self.properties = Pset.fromstream(self.fd)
        self.count = struct.unpack('<Q', self.fd.read(8))[0]
        self.start = self.fd.tell()

    def __len__(self):
        return self.count

    @property
    def label(self):
        return self.properties.items['Label'].value

    @property
    def values(self):
        self.fd.seek(self.start, SEEK_SET)
        return list(struct.unpack(f"<{self.count}f", self.fd.read(self.count * 4)))

    def __getitem__(self, key):
        if isinstance(key, int):
            start, stop, step = slice(key, None, None).indices(self.count)
            stop = start + 1
        elif isinstance(key, slice):
            start, stop, step = key.indices(self.count)
        else:
            raise TypeError("MapData indices must be integers or slices")

        if stop > self.count:
            raise IndexError("MapData index out of range")

        if step == 1:
            # for step 1 use a single read.
            length = stop - start
            self.fd.seek(self.start + (start * 4), SEEK_SET)
            values = struct.unpack(f"<{length}f", self.fd.read(length * 4))
        else:
            values = []
            for index in range(start, stop, step):
                self.fd.seek(self.start + (index * 4), SEEK_SET)
                data = self.fd.read(4)
                values.append(struct.unpack('<f', data)[0])
        return values[0] if len(values) == 1 else tuple(values)


class MapAreaFlags(IntFlag):
    """Set of flags used to defined the layout of map points in a file."""

    NoFlag = 0

    RandomPoints = (1 << 0)
    """File contains random points.
    default (false) is rectangle area, otherwise is random points within a bound"""

    ColumnMajor = (1 << 1)
    """Data collection order. default (false) is X first then Y, otherwise is Y first then X"""

    Alternating = (1 << 2)
    """Data collection order of alternate major axis.
    default (false) is raster, otherwise is snake (alternating)."""

    LineFocusMapping = (1 << 3)
    """Flag marks data collection order using line-focus mapping."""

    # The following two values are deprecated; negative step-size is sufficient information.
    # [Deprecated] InvertedRows = (1 << 4) # True if rows collected right to left
    # [Deprecated] InvertedColumns = (1 << 5) # True if columns collected bottom to top

    SurfaceProfile = (1 << 6)
    """Flag to mark data with irregular Z positions (surface maps)."""

    XYLine = (1 << 7)
    """line or depth slice forming a single line along the XY plane
    length.x contains number of points along line; length.y = 1 """


@dataclass
class FloatVector:
    x: float
    y: float
    z: float

    def __iter__(self):
        yield "x", self.x
        yield "y", self.y
        yield "z", self.z


@dataclass
class IntVector:
    x: int
    y: int
    z: int

    def __iter__(self):
        yield "x", self.x
        yield "y", self.y
        yield "z", self.z


@dataclass
class MapArea:
    start: FloatVector
    step: FloatVector
    count: IntVector
    flags: MapAreaFlags

    def __iter__(self):
        yield "start", dict(self.start)
        yield "step", dict(self.step)
        yield "count", dict(self.count)
        yield "flags", self.flags


class Wdf:
    """Python accessor class for WDF file data."""
    def __init__(self, path='', mode='rb'):
        self.x = MapAreaFlags.RandomPoints
        self.path = path
        self.fd = None
        self.hdr = None
        self.owned = True
        if path != "":
            self.open(path, mode)

    def __enter__(self):
        return self

    def __exit__(self, vtype, value, traceback):
        self.close()

    def __iter__(self):
        return WdfIter(self)

    def __len__(self):
        return self.hdr.nspectra

    def __getitem__(self, index):
        """return the spectrum at specified index.
        if a negtive index is specifified return the spectrum
        index spaces away from the end"""
        if index < 0:
            index = self.hdr.nspectra + index
        if index < 0 or index >= self.hdr.nspectra:
            raise IndexError
        return self.spectrum(index)

    def open(self, path, mode='rb'):
        """open the specified path as a wdf file.
        mode: provide the file access mode: 'rb' for read-only
        or 'r+b' for read-write"""
        self.open_fd(open(path, mode), owned=True)

    def open_fd(self, fd, owned=False):
        """open the provided file-descriptor as a wdf file."""
        self.fd = fd
        self.owned = owned
        data = self.fd.read(WdfHeader._size)
        self.hdr = WdfHeader._make(struct.unpack(WdfHeader._packstr, data))

    def close(self):
        """close the file descriptor (if owned by this object)"""
        if self.owned:
            self.fd.close()
        self.fd = None

    def spectrum(self, index, count=1):
        """Retrieve the unpacked spectrum i-list values.
        If count is set then read count spectra in one go."""
        size = self.hdr.npoints * 4
        _ = self.find_section(WdfBlockId.DATA)
        self.fd.seek(index * size, SEEK_CUR)
        return struct.unpack(f'{self.hdr.npoints * count}f', self.fd.read(size * count))

    def update_spectrum(self, index, data):
        """Update the i-list for a spectrum.
        data: a sequence of npoints values"""
        if not self.fd.writable:
            raise IOError('WDF object not writable')
        self.find_section(WdfBlockId.DATA)
        self.fd.seek(index * (self.hdr.npoints * 4), SEEK_CUR)
        self.fd.write(struct.pack(f'{self.hdr.npoints}f', *data))

    def xlist(self):
        """Get the spectral x-list values."""
        block = self.find_section(WdfBlockId.XLIST)[0]
        _, _ = struct.unpack('<II', self.fd.read(8))
        return struct.unpack('<%df' % self.hdr.xlistcount, self.fd.read(block.size - 24))

    def ylist(self):
        """Get the spectral y-list values."""
        block = self.find_section(WdfBlockId.YLIST)[0]
        _, _ = struct.unpack('<II', self.fd.read(8))
        return struct.unpack('<%df' % self.hdr.ylistcount, self.fd.read(block.size - 24))

    def comment(self):
        """Get the file comment block as text."""
        try:
            block = self.find_section(WdfBlockId.COMMENT)[0]
        except EOFError:
            return ""
        size = block.size - WdfBlock._SIZE
        data = self.fd.read(size)
        try:
            result = _tostr(data)
        except UnicodeDecodeError:
            pass
        return result

    def find_section(self, id: int, uid: int = -1, pos=0):
        """Find a Wdf block using its id and optionally the uid.
        On return, the starting file seek position can be specified
        but is at the start of the block data by default.
        The block structure and the position of the start
        of the block is returned"""
        try:
            while True:
                self.fd.seek(pos, SEEK_SET)
                block = WdfBlock.fromstream(self.fd)
                if block.id == id and (uid == -1 or uid == block.uid):
                    return (block, pos)
                pos += block.size
        except IOError:
            pass
        raise EOFError()

    def sections(self) -> List[WdfBlock]:
        """Return a list of sections as (id,uid,size,pos)"""
        pos = 0
        sections = []
        try:
            while True:
                self.fd.seek(pos, SEEK_SET)
                block = WdfBlock.fromstream(self.fd)
                sections.append(block)
                pos += block.size
        except IOError:
            pass
        return sections

    # Checkout numpy.fromfile for reading whole arrays.
    # def read_all(self):
    #    block = self.find_section(b'DATA') # puts file pointer at start of data
    #    npoints = self.hdr.ncollected * self.hdr.npoints
    #    return np.fromfile(self.fd, dtype=float, count=npoints)
    #
    # eg: data = wdf.read_add()
    #     plt.plot(wdf.xlist(), data[wdf.hdr.npoints])

    def get_map_data(self, uid=-1) -> MapData:
        """Returns a MapData object holding information for a Wdf map.
        The uid parameter selects a specific map. If uid is -1 then the first map is returned.
        If no such map is present an InvalidSectionError exception is raised."""
        map_sections = [section for section in self.sections() if section.id == WdfBlockId.MAP]
        valid = [section.uid for section in map_sections]
        if valid and uid == -1:
            uid = valid[0]
        if uid not in valid:
            raise InvalidSectionError(f"map {uid} not present")
        section = [section for section in map_sections if section.uid == uid][0]
        return MapData(self.fd, section)

    def get_section_properties(self, id, uid) -> Pset:
        """If a section has a property collection, returns it else returns None"""
        _ = self.find_section(id, uid)
        return Pset.fromstream(self.fd)

    @property
    def origins(self) -> WdfOriginSet:
        return WdfOriginSet(self)

    @property
    def map_area(self) -> MapArea:
        """Get the map area definition for this file."""
        try:
            _ = self.find_section(WdfBlockId.MAPAREA)[0]
            flags, _ = struct.unpack('<II', self.fd.read(8))
            startPos = struct.unpack('<fff', self.fd.read(12))
            stepSize = struct.unpack('<fff', self.fd.read(12))
            nSteps = struct.unpack('<LLL', self.fd.read(12))
            return MapArea(FloatVector(*startPos),
                           FloatVector(*stepSize),
                           IntVector(*nSteps),
                           MapAreaFlags(flags))
        except EOFError:
            raise EOFError('No map area data present')
