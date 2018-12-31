xtarfile
========

.. image:: https://api.travis-ci.org/ascoderu/xtarfile.svg?branch=master
    :target: https://travis-ci.org/ascoderu/xtarfile

.. image:: https://img.shields.io/pypi/v/xtarfile.svg
    :target: https://pypi.org/project/xtarfile/

Overview
--------

Wrapper around tarfile to add support for more compression formats.

Usage
-----

First, install the library with the tarfile compression formats you wish to support.
The example below shows an install for zstandard tarfile support.

.. sourcecode :: bash

    pip install xtarfile[zstd]

You can now use the xtarfile module in the same way as the standard library tarfile module:

.. sourcecode :: python

    import xtarfile as tarfile

    with tarfile.open('some-archive', 'w:zstd') as archive:
        archive.add('a-file.txt')

    with tarfile.open('some-archive', 'r:zstd') as archive:
        archive.extractall()

Alternatively, detecting the correct compression module based on the file extensions is also supported:

.. sourcecode :: python

    import xtarfile as tarfile

    with tarfile.open('some-archive.tar.zstd', 'w') as archive:
        archive.add('a-file.txt')

    with tarfile.open('some-archive.tar.zstd', 'r') as archive:
        archive.extractall()
