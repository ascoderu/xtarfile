from io import BytesIO
from itertools import product
from os import close
from os import remove
from tarfile import TarInfo
from tempfile import mkstemp
from unittest import TestCase

from xtarfile.xtarfile import get_compression
from xtarfile.xtarfile import xtarfile_open
from xtarfile.xtarfile import HANDLERS


class FileExtensionIdContext:
    def __init__(self, test_case, compressor):
        self.test_case = test_case
        self.extension = '.{}'.format(compressor)

    def __str__(self):
        return self.__class__.__name__

    def given_file(self):
        return self.test_case.given_file(suffix=self.extension)

    @classmethod
    def mode(cls, mode):
        return mode


class ExplicitOpenIdContext:
    def __init__(self, test_case, compressor):
        self.test_case = test_case
        self.compressor = compressor

    def __str__(self):
        return self.__class__.__name__

    def given_file(self):
        return self.test_case.given_file(suffix='')

    def mode(self, mode):
        return '{}|{}'.format(mode, self.compressor)


class GetCompressionTests(TestCase):
    def test_prefers_explicit_open_mode(self):
        compression = get_compression('foo.tar.gz', 'r:bz2')
        self.assertEqual(compression, 'bz2')

    def test_falls_back_to_extension(self):
        compression = get_compression('foo.tar.gz', 'r')
        self.assertEqual(compression, 'gz')


class OpenTests(TestCase):
    def test_roundtrip(self):
        plugins = [key for (key, value) in HANDLERS.items() if value]
        compressors = ['gz', 'bz2', 'xz'] + plugins
        contexts = (ExplicitOpenIdContext, FileExtensionIdContext)

        for compressor, ctx in product(compressors, contexts):
            context = ctx(self, compressor)
            with self.subTest(compressor=compressor, context=str(context)):
                self._test_roundtrip(context)

    def _test_roundtrip(self, context):
        path = context.given_file()
        content = b'test content'
        filename = 'archived-file.txt'

        with xtarfile_open(path, context.mode('w')) as archive:
            buffer = BytesIO()
            buffer.write(content)
            buffer.seek(0)

            tarinfo = TarInfo()
            tarinfo.size = len(content)
            tarinfo.name = filename

            archive.addfile(tarinfo, buffer)

        with xtarfile_open(path, context.mode('r')) as archive:
            while True:
                member = archive.next()
                if member is None:
                    self.fail('{} not found in archive'.format(filename))
                if member.name == filename:
                    buffer = archive.extractfile(member)
                    actual_content = buffer.read()
                    break

        self.assertEqual(actual_content, content)

    def given_file(self, suffix):
        fd, path = mkstemp(suffix)
        close(fd)
        self.tempfiles.append(path)
        return path

    def setUp(self):
        self.tempfiles = []

    def tearDown(self):
        for path in self.tempfiles:
            remove(path)
