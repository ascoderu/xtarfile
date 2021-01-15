import pathlib
import importlib
from tarfile import TarFile, TarInfo, _Stream, _StreamProxy, _LowLevelFile, CompressionError, TarError  # noqa: F401
import inspect


# Replace _Stream.__init__ with custom version to handle our formats
# This is used to dynamically add code to the function

# Get source of _Stream.__init__
streaminitfunction, lines = inspect.getsourcelines(_Stream.__init__)

# Remove indendation, it's a class function but our overload is not.
streaminitfunction = [lines[4:] for lines in streaminitfunction]

# Replace function name with stream_init_overload.
streaminitfunction[0] = "def stream_init_overload(self, name, mode, comptype, fileobj, bufsize):\n"


# Replace _StreamProxy.getcomptype with custom version to handle our formats
# This is used to dynamically add code to the function
# This a copy of the original function from _StreamProxy
comptypefunction = ['def getcomptype(self):',
                    '  if self.buf.startswith(b"\\x1f\\x8b\\x08"):',
                    '    return "gz"',
                    '  elif self.buf[0:3] == b"BZh" and self.buf[4:10] == b"1AY&SY":',
                    '    return "bz2"',
                    '  elif self.buf.startswith((b"\\x5d\\x00\\x00\\x80", b"\\xfd7zXZ")):',
                    '    return "xz"',
                    '  else:',
                    '    return "tar"']


# Make a list of all the compression formats in 'formats/' and add them as subclasses to xtarfile
subclasses = (TarFile,)
cf = {}  # Temporary dictionary for updating OPEN_METH

# Get path of xtarfile.py and add the formats directory to the end
formats_path = pathlib.Path(__file__).parent / 'formats'

for f in formats_path.iterdir():
    if f.is_file() and f.suffix == ".py":  # Make sure it's a python source file
        # Import file with compression format
        compmod = importlib.import_module("." + f.stem, 'xtarfile.formats')

        # Get compdict containin information for OPEN_METH
        cf.update(getattr(compmod, 'compdict'))

        # Get magicbytes for 'getcomptype' function for Stream mode
        magicbytes = getattr(compmod, 'magicbytes')
        comptypefunction.insert(7, magicbytes)

        # Get _Stream.__init__ code and add it to our function
        streaminit = getattr(compmod, 'streaminit')
        streaminitfunction[60:60] = streaminit

        # Add as subclass to xtarfile
        subclasses = subclasses + (getattr(compmod, f.stem),)


# Construct xtarfile class
xtarfile = type("xtarfile", subclasses, dict())

# Add our compression formats to the OPEN_METH dictionary
xtarfile.OPEN_METH.update(cf)


# Compile and overload _StreamProxy.getcomptype
exec("\n".join(comptypefunction))
_StreamProxy.getcomptype = getcomptype  # noqa: F821


# Compile and overload _Stream.__init__
exec("".join(streaminitfunction))
_Stream.__init__ = stream_init_overload  # noqa: F821


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
