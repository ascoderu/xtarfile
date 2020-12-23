import os
from builtins import open as _builtin_open  # This is needed because otherwise it calls the wrong 'open' function
from tarfile import TarFile, TarInfo, _Stream, _StreamProxy, _LowLevelFile, ReadError, CompressionError, TarError
from types import MethodType


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



def seekable(self):
    return True

_Stream.seekable = MethodType(seekable, _Stream)

class xtarfile(TarFile):
    @classmethod
    def xopen(cls, name=None, mode="r", fileobj=None, bufsize=10240, **kwargs):
        # Special handling for streams
        if "|" in mode:
            filemode, comptype = mode.split("|", 1)
            if comptype in ("zst", "zstd", "lz4"):
                stream = _Stream(name, filemode, "tar", fileobj, bufsize)
                return cls.open(name, filemode + ":" + comptype, stream, bufsize, **kwargs)
            elif comptype == "*":
                if not fileobj:
                    lfileobj = _LowLevelFile(name, filemode)
                    stream_proxy = _StreamProxy(lfileobj)
                    _StreamProxy.getcomptype = MethodType(getcomptype, stream_proxy)
                    if stream_proxy.getcomptype() in ("gz", "bz2", "xz", "tar"):
                        stream_proxy.close()
                        return TarFile.open(str(name), mode, fileobj, bufsize, **kwargs)
                    elif stream_proxy.getcomptype() in ("zst", "zstd"):
                        import zstandard
                        dctx = zstandard.ZstdDecompressor()
                        fileobj = dctx.stream_reader(stream_proxy)
                        return TarFile.open(name, "r|", fileobj, bufsize, **kwargs)
                    elif stream_proxy.getcomptype() == "lz4":
                        import lz4.frame as lz4
                        fileobj = lz4.LZ4FrameFile(stream_proxy, filemode)
                        return TarFile.open(name, "r|", fileobj, bufsize, **kwargs)
                else:
                    return TarFile.open(str(name), mode, fileobj, bufsize, **kwargs)

                stream = _Stream(name, filemode, "tar", fileobj, bufsize)
                return cls.open(name, filemode + ":" + comptype, stream, bufsize, **kwargs)
            else:
                if comptype == "gz":  # gz can't handle Path objects, need a String instead, this should be reported upstream.
                    return TarFile.open(str(name), mode, fileobj, bufsize, **kwargs)
                else:
                    return TarFile.open(name, mode, fileobj, bufsize, **kwargs)

        return cls.open(name, mode, fileobj, bufsize, **kwargs)

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

'''
class _StreamProxy(object):
    """Small proxy class that enables transparent compression
       detection for the Stream interface (mode 'r|*').
    """

    def __init__(self, fileobj):
        self.fileobj = fileobj
        self.buf = self.fileobj.read(10240)

    def read(self, size):
        self.read = self.fileobj.read
        return self.buf

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

    def close(self):
        self.fileobj.close()
'''

# When extending, use lz4open as a base. These are the important things to note.
# Change "import lz4.frame as lz4" to the compression package of your choice. Change the relevant ImportError
# Change compresslevel/error to whatever is supported by your format.
# This is the bit that actually does something useful.
# fileobj = lz4.LZ4FrameFile(fileobj or name, mode, compression_level=compresslevel)
# As long as fileobj is a valid 'file object' when you hit "t = cls.taropen(name, mode, fileobj, **kwargs)", it should Just Work™
# Add the error your format raises when it fails to open a file for reading to "except (OSError, EOFError, RuntimeError):"
# RuntimeError is what lz4 uses and should be removed. Unless that is what your format uses ofcourse :D
# Register the function down below, format is "file extension" : "func".
# You don't have to use the file extension. The 'key' part of the dictionary is used when calling xtarfile.open with mode="w:key" or similar
# See https://docs.python.org/3/library/tarfile.html for more information about modes
# And lastly, add your format to 'if comptype in ("zst", "zstd", "lz4"):' in xopen()
xtarfile.OPEN_METH.update({"zst": "zstopen",
                           "zstd": "zstopen",
                           "lz4": "lz4open"})

xtarfile_open = xtarfile.xopen
