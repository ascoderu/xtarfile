from itertools import chain
from os import PathLike, fspath
from tarfile import open as tarfile_open
from typing import Union

from xtarfile.zstd import ZstandardTarfile
from xtarfile.lz4 import Lz4Tarfile


_HANDLERS = {
    'zstd': ZstandardTarfile,
    'tzstd': ZstandardTarfile,
    'zst': ZstandardTarfile,
    'tzst': ZstandardTarfile,
    'lz4': Lz4Tarfile,
    'tlz4': Lz4Tarfile,
    'tlz': Lz4Tarfile,
}

_NATIVE_FORMATS = ('gz', 'bz2', 'xz', 'tar')

SUPPORTED_FORMATS = frozenset(chain(_HANDLERS.keys(), _NATIVE_FORMATS))


def get_compression(path: Union[str, PathLike], mode: str) -> str:
    path = fspath(path)
    for delim in (':', '|'):
        delim_index = mode.rfind(delim)
        if delim_index > -1:
            return mode[delim_index + 1:]

    dot_index = path.rfind('.')
    if dot_index > -1:
        return path[dot_index + 1:]

    return ''


def xtarfile_open(path: Union[str, PathLike], mode: str, **kwargs):
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
