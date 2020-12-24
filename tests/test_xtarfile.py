from io import BytesIO
import pytest
import xtarfile


testfiles = dict()
STREAM_OPEN_METHODS = list()
content = b'test content'
filename = 'archived-file.txt'

for method in xtarfile.xtarfile.OPEN_METH.keys():
    if method == 'gz':
        STREAM_OPEN_METHODS.append(pytest.param(method, marks=pytest.mark.xfail(reason="compression GZ doesn't support PathLike objects and thus creates no files", strict=True)))
    else:
        STREAM_OPEN_METHODS.append(method)


@pytest.fixture(params=xtarfile.xtarfile.OPEN_METH)
def _test_xwriting_filedoesntexist(request, tmp_path):
    ofilename = tmp_path.joinpath("test.tar." + request.param)

    with xtarfile.open(name=ofilename, mode="x:" + request.param) as archive:
        buffer1 = BytesIO()
        buffer1.write(content)
        buffer1.seek(0)

        tarinfo = xtarfile.TarInfo()
        tarinfo.size = len(content)
        tarinfo.name = filename
        archive.addfile(tarinfo, buffer1)

    return ofilename, request.param


@pytest.fixture(params=xtarfile.xtarfile.OPEN_METH)
def _test_xwriting_filexists(request):
    try:
        with xtarfile.open(name=testfiles[request.param], mode="x:" + request.param) as archive:
            buffer1 = BytesIO()
            buffer1.write(content)
            buffer1.seek(0)

            tarinfo = xtarfile.TarInfo()
            tarinfo.size = len(content)
            tarinfo.name = filename
            archive.addfile(tarinfo, buffer1)
    except FileExistsError:  # This should always happen
        return

    # If it didn't the test fails
    pytest.fail()


@pytest.fixture(params=xtarfile.xtarfile.OPEN_METH)
def _test_writing(request, tmp_path):
    ofilename = tmp_path.joinpath("test.tar." + request.param)

    with xtarfile.open(name=ofilename, mode="w:" + request.param) as archive:
        buffer1 = BytesIO()
        buffer1.write(content)
        buffer1.seek(0)

        tarinfo = xtarfile.TarInfo()
        tarinfo.size = len(content)
        tarinfo.name = filename
        archive.addfile(tarinfo, buffer1)

    return ofilename, request.param


@pytest.fixture(params=xtarfile.xtarfile.OPEN_METH)
def _test_reading(request):
    try:
        with xtarfile.open(name=testfiles[request.param], mode="r") as archive:
            while True:
                member = archive.next()
                if member is None:
                    pytest.fail('{} not found in archive'.format(filename))
                if member.name == filename:
                    buffer1 = archive.extractfile(member)
                    actual_content = buffer1.read()
                    break

        return actual_content
    except KeyError:
        if request.param == "gz":
            pytest.xfail("gz doesn't support PathLike objects, so no files were created.")


@pytest.fixture(params=STREAM_OPEN_METHODS)
def _test_stream_mode_writing(request, tmp_path):
    ofilename = tmp_path.joinpath("test.tar." + request.param)
    with xtarfile.open(name=ofilename, mode="w|" + request.param) as archive:
        buffer1 = BytesIO()
        buffer1.write(content)
        buffer1.seek(0)

        tarinfo = xtarfile.TarInfo()
        tarinfo.size = len(content)
        tarinfo.name = filename
        archive.addfile(tarinfo, buffer1)

    return ofilename, request.param


@pytest.fixture(params=STREAM_OPEN_METHODS)
def _test_stream_mode_reading(request):
    with xtarfile.open(name=testfiles[request.param], mode="r|" + request.param) as archive:
        while True:
            member = archive.next()
            if member is None:
                pytest.fail('{} not found in archive'.format(filename))
            if member.name == filename:
                buffer1 = archive.extractfile(member)
                actual_content = buffer1.read()
                break

    return actual_content


@pytest.fixture(params=STREAM_OPEN_METHODS)
def _test_stream_mode_reading_auto(request):
    with xtarfile.open(name=testfiles[request.param], mode="r|*") as archive:
        while True:
            member = archive.next()
            if member is None:
                pytest.fail('{} not found in archive'.format(filename))
            if member.name == filename:
                buffer1 = archive.extractfile(member)
                actual_content = buffer1.read()
                break

    return actual_content


@pytest.fixture(params=xtarfile.xtarfile.OPEN_METH)
def _test_import_is_tarfile(request):
    return xtarfile.is_tarfile(testfiles[request.param])


@pytest.fixture(params=STREAM_OPEN_METHODS)
def _test_import_is_tarfile_after_stream(request):
    return xtarfile.is_tarfile(testfiles[request.param])


# Run the tests
def test_stream_mode_writing(_test_stream_mode_writing):
    filename, OPEN_METH = _test_stream_mode_writing
    assert filename.is_file() == True
    testfiles.update({OPEN_METH: filename})


def test_import_is_tarfile_after_stream(_test_import_is_tarfile_after_stream):
    assert _test_import_is_tarfile_after_stream == True


def test_reading_stream_created_files(_test_reading):
    assert content == _test_reading


def test_stream_mode_reading(_test_stream_mode_reading):
    assert content == _test_stream_mode_reading


def test_stream_mode_reading_auto(_test_stream_mode_reading_auto):
    assert content == _test_stream_mode_reading_auto


testfiles.clear()


def test_writing(_test_writing):
    filename, OPEN_METH = _test_writing
    assert filename.is_file() == True
    testfiles.update({OPEN_METH: filename})


def test_import_is_tarfile_after_writing(_test_import_is_tarfile):
    assert _test_import_is_tarfile == True


def test_reading(_test_reading):
    assert content == _test_reading


# Make sure opening with 'x' works as expected
def test_xwriting_filexists(_test_xwriting_filexists):
    pass


testfiles.clear()


def test_xwriting_filedoesntexist(_test_xwriting_filedoesntexist):
    filename, OPEN_METH = _test_xwriting_filedoesntexist
    assert filename.is_file() == True
    testfiles.update({OPEN_METH: filename})


def test_import_is_tarfile_after_xwriting(_test_import_is_tarfile):
    assert _test_import_is_tarfile == True


def test_reading_after_xwrite_2(_test_reading):
    assert content == _test_reading
