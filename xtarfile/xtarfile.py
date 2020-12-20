import os
from builtins import open as _builtin_open
from tarfile import TarFile, TarInfo, is_tarfile, ReadError, CompressionError


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
        except (OSError, EOFError, zstandard.ZstdError) as err:
            if fileobj:
                fileobj.close()
            if mode == 'r' and str(err) == "zstd decompress error: Unknown frame descriptor":
                raise ReadError("not a zst file")
            raise
        except Exception as err:
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
        except (OSError, EOFError, RuntimeError) as err:
            fileobj.close()
            if mode == 'r' and str(err) == "LZ4F_decompress failed with code: ERROR_frameType_unknown":
                raise ReadError("not a lz4 file")
            raise
        except Exception as err:
            fileobj.close()
            raise
        t._extfileobj = False
        return t


# When extending register the function here, format is "file extension" : "func"
xtarfile.OPEN_METH.update({"zst": "zstopen",
                           "zstd": "zstopen",
                           "lz4": "lz4open"})

xtarfile_open = xtarfile.open
