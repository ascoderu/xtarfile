from contextlib import contextmanager
from tarfile import open as tarfile_open
from tempfile import NamedTemporaryFile

try:
    import zstandard
except ImportError:
    zstandard = None


class ZstandardTarfile:
    def __init__(self, **kwargs):
        self.zstd_kwargs = kwargs

    @contextmanager
    def read(self, path: str, mode: str):
        with NamedTemporaryFile() as decompressed:
            with open(path, 'rb') as compressed:
                zstd = zstandard.ZstdDecompressor(**self.zstd_kwargs)
                zstd.copy_stream(compressed, decompressed)
            decompressed.seek(0)
            archive = tarfile_open(mode=mode, fileobj=decompressed)
            try:
                yield archive
            finally:
                archive.close()

    @contextmanager
    def write(self, path: str, mode: str):
        with NamedTemporaryFile() as decompressed:
            archive = tarfile_open(decompressed.name, mode=mode)
            try:
                yield archive
            finally:
                archive.close()
            decompressed.seek(0)
            with open(path, 'wb') as compressed:
                zstd = zstandard.ZstdCompressor(**self.zstd_kwargs)
                zstd.copy_stream(decompressed, compressed)


if zstandard is None:
    ZstandardTarfile = None  # noqa F811
