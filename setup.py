#!/usr/bin/env python

"""The setup script."""

import pathlib
from setuptools import setup, find_packages

here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8")

requirements = [
    'beautifulsoup4==4.12.3',
    'python-dateutil==2.9.0.post0',
    'requests>=2.28.1',
    'soupsieve==2.5',
    'urllib3==1.26.5',
    'cachetools>=5.3.3'
    ]

setup(
    author="carohauta",
    author_email='carosoft.dev@gmail.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    description="Oma Helen API library and CLI",
    entry_points={
        'console_scripts': [
            'oma-helen-cli=helenservice.cli:main',
        ],
    },
    name="oma-helen-cli",
    install_requires=requirements,
    license="MIT license",
    long_description=long_description,
    long_description_content_type='text/markdown',
    include_package_data=True,
    packages=find_packages(include=['helenservice', 'helenservice.*']),
    url='https://github.com/carohauta/oma-helen-cli',
    version='1.3.2',
    zip_safe=False,
)
