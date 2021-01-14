import os
import pathlib
import importlib
from tarfile import TarFile, TarInfo, _Stream, _StreamProxy, _LowLevelFile, ReadError, CompressionError, TarError, RECORDSIZE


# Replace _StreamProxy.getcomptype with custom version to handle our formats
def getcomptype(self):
    if self.buf.startswith(b"\x1f\x8b\x08"):
        return "gz"
    elif self.buf[0:3] == b"BZh" and self.buf[4:10] == b"1AY&SY":
        return "bz2"
    elif self.buf.startswith((b"\x5d\x00\x00\x80", b"\xfd7zXZ")):
        return "xz"
    elif self.buf.startswith(b"\x28\xB5\x2F\xFD"):
        return "zst"
    elif self.buf.startswith(b"\x04\x22\x4D\x18"):
        return "lz4"
    else:
        return "tar"


_StreamProxy.getcomptype = getcomptype


# Replace _Stream.__init__ with custom version to handle our formats
def stream_init_overload(self, name, mode, comptype, fileobj, bufsize):
    """Construct a _Stream object.
    """
    self._extfileobj = True
    if fileobj is None:
        fileobj = _LowLevelFile(name, mode)
        self._extfileobj = False

    if comptype == '*':
        # Enable transparent compression detection for the
        # stream interface
        fileobj = _StreamProxy(fileobj)
        comptype = fileobj.getcomptype()

    self.name     = name or ""
    self.mode     = mode
    self.comptype = comptype
    self.fileobj  = fileobj
    self.bufsize  = bufsize
    self.buf      = b""
    self.pos      = 0
    self.closed   = False

    try:
        if comptype == "gz":
            try:
                import zlib
            except ImportError:
                raise CompressionError("zlib module is not available")
            self.zlib = zlib
            self.crc = zlib.crc32(b"")
            if mode == "r":
                self._init_read_gz()
                self.exception = zlib.error
            else:
                self._init_write_gz()

        elif comptype == "bz2":
            try:
                import bz2
            except ImportError:
                raise CompressionError("bz2 module is not available")
            if mode == "r":
                self.dbuf = b""
                self.cmp = bz2.BZ2Decompressor()
                self.exception = OSError
            else:
                self.cmp = bz2.BZ2Compressor()

        elif comptype == "xz":
            try:
                import lzma
            except ImportError:
                raise CompressionError("lzma module is not available")
            if mode == "r":
                self.dbuf = b""
                self.cmp = lzma.LZMADecompressor()
                self.exception = lzma.LZMAError
            else:
                self.cmp = lzma.LZMACompressor()

        elif comptype in ("zst", "zstd"):
            try:
                import zstandard
            except ImportError:
                raise CompressionError("lzma module is not available")
            if mode == "r":
                self.dbuf = b""
                self.cmp = zstandard.ZstdDecompressor().decompressobj()
                self.exception = zstandard.ZstdError
            else:
                self.cmp = zstandard.ZstdCompressor().compressobj()

        elif comptype == "lz4":
            try:
                from lz4.frame import LZ4FrameCompressor, LZ4FrameDecompressor
            except ImportError:
                raise CompressionError("lz4 module is not available")
            if mode == "r":
                self.dbuf = b""
                self.cmp = LZ4FrameDecompressor()
                self.exception = RuntimeError
            else:
                self.cmp = LZ4FrameCompressor()
                self.fileobj.write((self.cmp.begin()))

        elif comptype != "tar":
            raise CompressionError("unknown compression type %r" % comptype)

    except:
        if not self._extfileobj:
            self.fileobj.close()
        self.closed = True
        raise


_Stream.__init__ = stream_init_overload


# Make a list of all the compression formats in 'formats/' and add them as subclasses to xtarfile
subclasses = (TarFile,)
cf = {}  # Dictionary for filename : compress_function pairs
formats_path = pathlib.Path(__file__).parent / 'formats'  # Get path of xtarfile.py and add the formats directory to the end
for f in formats_path.iterdir():
    if f.is_file() and f.suffix == ".py":  # Make sure it's a python source file
        # Import the file, get compdict from it, add class to subclasses.
        compmod = importlib.import_module("." + f.stem, 'xtarfile.formats')
        cf.update(getattr(compmod, 'compdict'))
        subclasses = subclasses + (getattr(compmod, f.stem),)


# Construct xtarfile class
xtarfile = type("xtarfile", subclasses, dict())

# Add our compression formats to the OPEN_METH dictionary
xtarfile.OPEN_METH.update(cf)

# Reimplementation of is_tarfile to use xtarfile instead of tarfile.
def is_tarfile(name):
    """Return True if name points to a tar archive that we
       are able to handle, else return False.
       'name' should be a string, file, or file-like object.
    """
    try:
        if hasattr(name, "read"):
            t = xtarfile.open(fileobj=name)
        else:
            t = xtarfile.open(name)
        t.close()
        return True
    except TarError:
        return False


xtarfile_open = xtarfile.open
