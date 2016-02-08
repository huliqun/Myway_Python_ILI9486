# Workaround for issue in Python 2.7.3
# See http://bugs.python.org/issue15881#msg170215
try:
    import multiprocessing
except ImportError:
    pass

from ez_setup import use_setuptools
use_setuptools()
from setuptools import setup, find_packages

setup(name              = 'Myway_ILI9486',
      version           = '1.0.0',
      author            = 'Liqun Hu',
      author_email      = 'huliquns@126.com',
      description       = 'Library to control an ILI9486 TFT LCD display.',
      license           = 'MIT',
      url               = 'https://github.com/adafruit/Adafruit_Python_ILI9341/',
      dependency_links  = ['https://github.com/adafruit/Adafruit_Python_GPIO/tarball/master#egg=Adafruit-GPIO-0.6.5'],
      install_requires  = ['Adafruit-GPIO>=0.6.5'],
      packages          = find_packages())
