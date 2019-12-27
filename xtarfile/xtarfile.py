from itertools import chain
from tarfile import open as tarfile_open

from xtarfile.zstd import ZstandardTarfile


_HANDLERS = {
    'zstd': ZstandardTarfile,
    'zst': ZstandardTarfile,
}

_NATIVE_FORMATS = ('gz', 'bz2', 'xz')

SUPPORTED_FORMATS = frozenset(chain(_HANDLERS.keys(), _NATIVE_FORMATS))


def get_compression(path: str, mode: str) -> str:
    for delim in (':', '|'):
        delim_index = mode.rfind(delim)
        if delim_index > -1:
            return mode[delim_index + 1:]

    dot_index = path.rfind('.')
    if dot_index > -1:
        return path[dot_index + 1:]

    return ''


def xtarfile_open(path: str, mode: str, **kwargs):
    compression = get_compression(path, mode)

    if not compression or compression in _NATIVE_FORMATS:
        return tarfile_open(path, mode, **kwargs)

    handler_class = _HANDLERS.get(compression)
    if handler_class is not None:
        handler = handler_class(**kwargs)
        if mode.startswith('r'):
            return handler.read(path, mode[:2])
        elif mode.startswith('w'):
            return handler.write(path, mode[:2])

    raise NotImplementedError
