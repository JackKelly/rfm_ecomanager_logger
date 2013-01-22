from setuptools import setup, find_packages

setup(
    name = "rfm-ecomanager-logger",
    version = "0.1dev",
    packages = find_packages(),
    install_requires = ['pickle'],
    author = "Jack Kelly",
    author_email = "jack-list@xlk.org.uk",
    description = "Log power data from rfm_edf_ecomanager running on a Nanode (or similar)",
    license = "MIT",
    keywords = "power logging python",
    url = "https://github.com/JackKelly/rfm_ecomanager_logger/",
    download_url = "https://github.com/JackKelly/rfm_ecomanager_logger/archive/master.tar.gz",
    long_description = open('README.md').read()
)
