from io import BytesIO
from os import remove as os_remove
import pytest
import xtarfile


def test_compression_formats():
    for compressor in xtarfile.xtarfile.OPEN_METH:
        wmode = "w:" + compressor
        rmode = "r:" + compressor
        content = b'test content'
        filename = 'archived-file.txt'
        ofilename = "test.tar." + compressor

        with xtarfile.open(name=ofilename, mode=wmode) as archive:
            buffer1 = BytesIO()
            buffer1.write(content)
            buffer1.seek(0)

            tarinfo = xtarfile.TarInfo()
            tarinfo.size = len(content)
            tarinfo.name = filename
            archive.addfile(tarinfo, buffer1)

        with xtarfile.open(name=ofilename, mode=rmode) as archive:
            while True:
                member = archive.next()
                if member is None:
                    pytest.fail('{} not found in archive'.format(filename))
                if member.name == filename:
                    buffer1 = archive.extractfile(member)
                    actual_content = buffer1.read()
                    break

        os_remove(ofilename)
        assert actual_content == content
