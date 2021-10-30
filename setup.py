"""Setup file."""
from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as file:
    long_description = file.read()

with open("requirements.txt", encoding="utf-8") as file:
    install_requires = list(val.strip() for val in file)

setup(
    name="deebot-client",
    version="0.0.0",
    url="https://github.com/DeebotUniverse/client.py",
    description="a library for controlling certain deebot vacuums",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="DeebotUniverse",
    author_email="deebotuniverse@knatschig-as-hell.info",
    license="GPL-3.0",
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 4 - Beta",
        # Indicate who your project is intended for
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Home Automation",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3.9",
    ],
    keywords="home automation vacuum robot deebot ecovacs",
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    package_data={"deebot_client": ["py.typed"]},
    install_requires=install_requires,
)
