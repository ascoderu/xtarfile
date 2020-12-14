from contextlib import contextmanager
from tarfile import open as tarfile_open
from tempfile import NamedTemporaryFile
from os import remove as os_remove

try:
    import lz4.frame as lz4
except ImportError:
    lz4 = None


class Lz4Tarfile:
    def __init__(self, **kwargs):
        self.lz4_kwargs = kwargs

    @contextmanager
    def read(self, path: str, mode: str):
        with lz4.LZ4FrameFile(path) as lz4d:
          archive = tarfile_open(mode=mode, fileobj=lz4d)
          try:
              yield archive
          finally:
              archive.close()

    @contextmanager
    def write(self, path: str, mode: str):
        with lz4.LZ4FrameFile(path, mode='w') as lz4c:
            archive = tarfile_open(mode=mode, fileobj=lz4c)
            try:
                yield archive
            finally:
                archive.close()

if lz4 is None:
    Lz4Tarfile = None  # noqa F811
