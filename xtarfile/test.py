from tarfile import TarInfo
from tempfile import mkstemp
from io import BytesIO
import unittest
import xtar

def test():
    path = "test.tar"
    content = b'test content'
    filename = 'archived-file.txt'
    shoe = xtar.xtarfile2
    print(shoe.OPEN_METH)

    with shoe.xtarfile_open("test.tar.zst", mode='w:zst') as archive:
        buffer1 = BytesIO()
        buffer1.write(content)
        buffer1.seek(0)

        tarinfo = TarInfo()
        tarinfo.size = len(content)
        tarinfo.name = filename
        archive.addfile(tarinfo, buffer1)

    with shoe.xtarfile_open("test.tar.zst", 'r:zst') as archive:
        while True:
            member = archive.next()
            if member is None:
                self.fail('{} not found in archive'.format(filename))
            if member.name == filename:
                buffer1 = archive.extractfile(member)
                actual_content = buffer1.read()
                break

    print(actual_content, " : ", content)
    if actual_content == content:
        print("yay!")

if __name__ == '__main__':
    test()