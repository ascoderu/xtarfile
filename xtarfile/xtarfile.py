import os
from builtins import open as _builtin_open  # This is needed because otherwise it calls the wrong 'open' function
from tarfile import TarFile, TarInfo, _Stream, _StreamProxy, _LowLevelFile, ReadError, CompressionError, TarError, RECORDSIZE
import struct


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
                dctx = zstandard.ZstdDecompressor()
                self.cmp = dctx.decompressobj()
                self.exception = zstandard.ZstdError
            else:
                dctx = zstandard.ZstdCompressor()
                self.cmp = dctx.compressobj()

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


class xtarfile(TarFile):
    @classmethod
    def zstopen(cls, name, mode="r", fileobj=None, compresslevel=9, **kwargs):
        """Open zstd compressed tar archive name for reading or writing.
           Appending is not allowed.
        """
        try:
            import zstandard
        except ImportError:
            raise CompressionError("zstandard module is not available")

        if not (1 <= compresslevel <= 22):
            raise ValueError("compresslevel must be between 1 and 22")

        if mode == 'r':
            lmode = "rb"
            zstd = zstandard.ZstdDecompressor()
            zststream = zstd.stream_reader
        elif mode == 'w':
            lmode = "wb"
            zstd = zstandard.ZstdCompressor(level=compresslevel)
            zststream = zstd.stream_writer
        elif mode == 'x':
            lmode = "xb"
            zstd = zstandard.ZstdCompressor(level=compresslevel)
            zststream = zstd.stream_writer
        else:
            raise ValueError("mode must be 'r', 'w' or 'x'")

        if isinstance(name, (str, bytes, os.PathLike)):
            fileobj = _builtin_open(name, lmode)
            zfileobj = zststream(fileobj)
        elif hasattr(fileobj, "read") or hasattr(fileobj, "write"):
            zfileobj = zststream(fileobj)
        else:
            raise TypeError("filename must be a str, bytes, file or PathLike object")

        try:
            t = cls.taropen(name, mode, zfileobj, **kwargs)
        except (OSError, EOFError, zstandard.ZstdError):
            if fileobj:
                fileobj.close()
            # This error is used for handling automatic decommpression handling in mode="r" and "r:*"
            if mode == 'r':
                raise ReadError("not a zst file")
            raise
        except Exception:
            if fileobj:
                fileobj.close()
            raise

        t._extfileobj = False
        return t

    @classmethod
    def lz4open(cls, name, mode="r", fileobj=None, compresslevel=9, **kwargs):
        """Open lz4 compressed tar archive name for reading or writing.
           Appending is not allowed.
        """
        if mode not in ("r", "w", "x"):
            raise ValueError("mode must be 'r', 'w' or 'x'")

        try:
            import lz4.frame as lz4
        except ImportError:
            raise CompressionError("lz4 module is not available")

        if not (1 <= compresslevel <= 16):
            raise ValueError("compresslevel must be between 1 and 16")

        fileobj = lz4.LZ4FrameFile(fileobj or name, mode, compression_level=compresslevel)

        try:
            t = cls.taropen(name, mode, fileobj, **kwargs)
        except (OSError, EOFError, RuntimeError):
            fileobj.close()
            # This error is used for handling automatic decommpression handling in mode="r" and "r:*"
            if mode == 'r':
                raise ReadError("not a lz4 file")
            raise
        except Exception:
            fileobj.close()
            raise

        t._extfileobj = False
        return t


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


xtarfile.OPEN_METH.update({"zst": "zstopen",
                           "zstd": "zstopen",
                           "lz4": "lz4open"})

xtarfile_open = xtarfile.open
