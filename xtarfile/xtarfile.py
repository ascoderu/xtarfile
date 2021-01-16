import pathlib
import importlib
from tarfile import TarFile, TarInfo, _Stream, _StreamProxy, _LowLevelFile, CompressionError, TarError  # noqa: F401
import inspect


# If you want to extend with additional formats use formats/lz4.py as an example!


# We need to replace _Stream.__init__ with a custom version to handle our formats
# This is used to dynamically add code to the function

# Get source of _Stream.__init__()
streaminitfunction, lines = inspect.getsourcelines(_Stream.__init__)

# Remove indendation, it's a class function but our overload is not.
streaminitfunction = [lines[4:] for lines in streaminitfunction]

# Change the name of function just in case
streaminitfunction[0] = "def stream_init_overload(self, name, mode, comptype, fileobj, bufsize):\n"


# We need to replace _StreamProxy.getcomptype with a custom version to handle our formats
# This is used to dynamically add code to the function

# Get source of _StreamProxy.getcomptype()
getcomptypefunction, lines = inspect.getsourcelines(_StreamProxy.getcomptype)

# Remove indendation, it's a class function but our overload is not.
getcomptypefunction = [lines[4:] for lines in getcomptypefunction]

# Change the name of function just in case
getcomptypefunction[0] = "def getcomptype_overload(self):\n"


subclasses = (TarFile,)  # Subclasses of xtarfile
cf = {}  # Temporary dictionary for updating OPEN_METH

# Get path of xtarfile.py and add the formats directory to the end
formats_path = pathlib.Path(__file__).parent / 'formats'

# Add all the compression formats in 'formats/'
for f in formats_path.iterdir():
    if f.is_file() and f.suffix == ".py":  # Make sure it's a python source file
        # Import file with compression format
        compmod = importlib.import_module("." + f.stem, 'xtarfile.formats')

        # Get dictionary containing information for OPEN_METH
        cf.update(getattr(compmod, 'compdict'))

        # Get _Stream.__init__ code and add it to our function
        streaminitfunction[60:60] = getattr(compmod, 'streaminit')

        # Get _StreamProxy.getcomptype code and add it to our function
        getcomptypefunction[7:7] = getattr(compmod, 'getcomptype')

        # Add as subclass to xtarfile
        subclasses = subclasses + (getattr(compmod, f.stem),)


# Construct xtarfile class
xtarfile = type("xtarfile", subclasses, dict())

# Add our compression formats to the OPEN_METH dictionary
xtarfile.OPEN_METH.update(cf)


# Compile and overload _StreamProxy.getcomptype
exec("".join(getcomptypefunction))
_StreamProxy.getcomptype = getcomptype_overload  # noqa: F821


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
