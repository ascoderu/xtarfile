import os
from tarfile import ReadError, CompressionError


# Dictionary format: 'file suffix' : 'open function'
compdict = {'zst': 'zstopen',
            'zstd': 'zstopen'}


magicbytes = '  elif self.buf.startswith(b"\\x28\\xB5\\x2F\\xFD"): return "zst"'


streaminit = [
'        elif comptype in ("zst", "zstd"):\n',
'            try:\n',
'                import zstandard\n',
'            except ImportError:\n',
'                raise CompressionError("lzma module is not available")\n',
'            if mode == "r":\n',
'                self.dbuf = b""\n',
'                self.cmp = zstandard.ZstdDecompressor().decompressobj()\n',
'                self.exception = zstandard.ZstdError\n',
'            else:\n',
'                self.cmp = zstandard.ZstdCompressor().compressobj()\n']


class zst():
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
            fileobj = open(name, lmode)
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
