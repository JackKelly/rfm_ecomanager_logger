from setuptools import setup, find_packages

setup(
    name = "rfm_ecomanager_logger",
    version = "0.1",
    packages = find_packages(),
    install_requires = [],
    author = "Jack Kelly",
    author_email = "jack-list@xlk.org.uk",
    description = "Log power data from rfm_edf_ecomanager running on a Nanode (or similar)",
    license = "MIT",
    keywords = "power logging python",
    url = "https://github.com/JackKelly/rfm_ecomanager_logger/",
    download_url = "https://github.com/JackKelly/rfm_ecomanager_logger/tarball/master#egg=rfm_ecomanager_logger-dev",
    long_description = open('README.md').read()
)
