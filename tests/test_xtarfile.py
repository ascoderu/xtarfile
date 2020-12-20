from io import BytesIO
import pytest
import xtarfile


@pytest.fixture(params=xtarfile.xtarfile.OPEN_METH)
def _test_compression_formats(request, tmp_path):
    wmode = "w:" + request.param
    rmode = "r:" + request.param
    content = b'test content'
    filename = 'archived-file.txt'
    ofilename = tmp_path.joinpath("test.tar." + request.param)

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

    assert actual_content == content


def test_a(_test_compression_formats):
    pass
