#!/usr/bin/env python
import os
import sys
from shutil import rmtree

from setuptools import setup, Command

NAME = 'pysilico-server'
DESCRIPTION = 'AVT-Prosilica camera controller with PLICO'
URL = 'https://github.com/lbusoni/pysilico_server'
EMAIL = 'lorenzo.busoni@inaf.it'
AUTHOR = 'Lorenzo Busoni'
LICENSE = 'MIT'
KEYWORDS = 'plico, Prosilica,  AVT, camera, laboratory, instrumentation control'

here = os.path.abspath(os.path.dirname(__file__))
# Load the package's __version__.py module as a dictionary.
about = {}
with open(os.path.join(here, NAME.replace("-", "_"), '__version__.py')) as f:
    exec(f.read(), about)


class UploadCommand(Command):
    """Support setup.py upload."""

    description = 'Build and publish the package.'
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status('Removing previous builds…')
            rmtree(os.path.join(here, 'dist'))
        except OSError:
            pass

        self.status('Building Source and Wheel (universal) distribution…')
        os.system('{0} setup.py sdist bdist_wheel --universal'.format(sys.executable))

        self.status('Uploading the package to PyPI via Twine…')
        os.system('twine upload dist/*')

        self.status('Pushing git tags…')
        os.system('git tag v{0}'.format(about['__version__']))
        os.system('git push --tags')

        sys.exit()


setup(name=NAME,
      description=DESCRIPTION,
      version=about['__version__'],
      classifiers=['Development Status :: 4 - Beta',
                   'Operating System :: POSIX :: Linux',
                   'Programming Language :: Python :: 3',
                   ],
      long_description=open('README.md').read(),
      url=URL,
      author_email=EMAIL,
      author=AUTHOR,
      license=LICENSE,
      keywords=KEYWORDS,
      packages=['pysilico_server',
                'pysilico_server.camera_controller',
                'pysilico_server.devices',
                'pysilico_server.process_monitor',
                'pysilico_server.scripts',
                'pysilico_server.utils',
                ],
      entry_points={
          'console_scripts': [
              'pysilico_server=pysilico_server.scripts.pysilico_camera_controller:main',
              'pysilico_kill_all=pysilico_server.scripts.pysilico_kill_processes:main',
              'pysilico_start=pysilico_server.scripts.pysilico_process_monitor:main',
              'pysilico_stop=pysilico_server.scripts.pysilico_stop:main',
          ],
      },
      package_data={
          'pysilico_server': ['conf/pysilico_server.conf', 'calib/*'],
      },
      install_requires=["plico>=0.25",
                        "pysilico>=0.19",
                        "numpy",
                        "psutil",
                        "six",
                        "rebin",
                        ],
      include_package_data=True,
      test_suite='test',
      cmdclass={'upload': UploadCommand, },
      )
