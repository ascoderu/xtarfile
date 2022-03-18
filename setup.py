import io

from setuptools import find_packages
from setuptools import setup

with io.open('README.rst', encoding='utf-8') as fobj:
    long_description = fobj.read().strip()

try:
    with io.open('version.txt', encoding='utf-8') as fobj:
        version = fobj.read().strip()
except FileNotFoundError:
    version = 'dev'

setup(
    name='xtarfile',
    version=version,
    author='Clemens Wolff',
    author_email='clemens.wolff+pypi@gmail.com',
    packages=find_packages(exclude=['tests']),
    url='https://github.com/ascoderu/xtarfile',
    download_url='https://pypi.python.org/pypi/xtarfile',
    license='Apache Software License',
    description='Wrapper around tarfile with support for more '
                'compression formats.',
    long_description=long_description,
    extras_require={
        'lz4': ['lz4 >= 2.2.1'],
        'zstd': ['zstandard >= 0.10.2']
    },
    python_requires='>=3.4',
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Utilities'
    ])
