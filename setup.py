import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages


setup(
    name = "romper",
    version = "0.1",
    packages = find_packages(),
    install_requires = ["clamp>=0.4"],
    clamp = {
        "modules": ["romper.topology"],
    }
)
