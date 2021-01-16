from tarfile import ReadError, CompressionError


# If you want to extend with additional formats use this file as an example!


# This variable is used to register new compression functions in the Tarfile class
# Dictionary format: 'file suffix' : 'open function'
compdict = {'lz4': 'lz4open'}


# This variable is used to overload _StreamProxy.getcomptype with additional formats
# Make sure indentation is correct and that the line ends with '\n'
getcomptype = ['    elif self.buf.startswith(b"\\x04\\x22\\x4D\\x18"): return "lz4"\n']


# This variable is used to overload _Stream.__init__ with additional formats
# Make sure indentation is correct and that all lines end with '\n'
streaminit = ['        elif comptype == "lz4":\n',
              '            try:\n',
              '                from lz4.frame import LZ4FrameCompressor, LZ4FrameDecompressor\n',
              '            except ImportError:\n',
              '                raise CompressionError("lz4 module is not available")\n',
              '            if mode == "r":\n',
              '                self.dbuf = b""\n',
              '                self.cmp = LZ4FrameDecompressor()\n',
              '                self.exception = RuntimeError\n',
              '            else:\n',
              '                self.cmp = LZ4FrameCompressor()\n',
              '                self.fileobj.write((self.cmp.begin()))\n']


# This will be used as a subclass in xtarfile
class lz4:
    @classmethod
    def lz4open(cls, name, mode="r", fileobj=None, compresslevel=9, **kwargs):
        """Open lz4 compressed tar archive name for reading or writing.
           Appending is not allowed.
        """
        # If you need to change this code significatly remember to still raise the errors.
        # It is required by the baseclass.
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

        # This error is used for handling automatic decommpression in mode="r" and "r:*"
        # RuntimeError is the error LZ4 uses for this. Change it to whatever your format is using.
        except (OSError, EOFError, RuntimeError):
            fileobj.close()

            if mode == 'r':
                raise ReadError("not a lz4 file")
            raise
        except Exception:
            fileobj.close()
            raise

        t._extfileobj = False
        return t
