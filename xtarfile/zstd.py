from contextlib import contextmanager
from tarfile import open as tarfile_open
from tempfile import NamedTemporaryFile
from os import remove as os_remove

try:
    import zstandard
except ImportError:
    zstandard = None


class ZstandardTarfile:
    def __init__(self, **kwargs):
        self.zstd_kwargs = kwargs

    @contextmanager
    def read(self, path: str, mode: str):
        try:
            with NamedTemporaryFile(delete=False) as decompressed:
                with open(path, 'rb') as compressed:
                    zstd = zstandard.ZstdDecompressor(**self.zstd_kwargs)
                    zstd.copy_stream(compressed, decompressed)
                decompressed.seek(0)
                archive = tarfile_open(mode=mode, fileobj=decompressed)
                try:
                    yield archive
                finally:
                    archive.close()
        finally:
            # We delete it manually because otherwise on Windows
            # it gets deleted before we move it to the output file location.
            # This is because on Windows, file handles with the O_TEMPORARY
            # flag (which is set if we pass `delete=True`) are deleted as
            # soon as they're closed.
            decompressed.close()
            os_remove(decompressed.name)

    @contextmanager
    def write(self, path: str, mode: str):
        try:
            with NamedTemporaryFile(delete=False) as decompressed:
                archive = tarfile_open(decompressed.name, mode=mode)
                try:
                    yield archive
                finally:
                    archive.close()
                decompressed.seek(0)
                with open(path, 'wb') as compressed:
                    zstd = zstandard.ZstdCompressor(**self.zstd_kwargs)
                    zstd.copy_stream(decompressed, compressed)
        finally:
            # We delete it manually because otherwise on Windows
            # it gets deleted before we move it to the output file location.
            # This is because on Windows, file handles with the O_TEMPORARY
            # flag (which is set if we pass `delete=True`) are deleted as
            # soon as they're closed.
            decompressed.close()
            os_remove(decompressed.name)


if zstandard is None:
    ZstandardTarfile = None  # noqa F811
