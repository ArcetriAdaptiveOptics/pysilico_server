#!/usr/bin/env python
from setuptools import setup


__version__ = "$Id: setup.py 33 2018-01-27 15:03:11Z lbusoni $"



setup(name='pysilico_server',
      description='AVT-Prosilica camera controller with PLICO',
      version='0.9',
      classifiers=['Development Status :: 4 - Beta',
                   'Operating System :: POSIX :: Linux',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3.5',
                   'Programming Language :: Python :: 3.6',
                   ],
      long_description=open('README.md').read(),
      url='',
      author_email='lbusoni@gmail.com',
      author='Lorenzo Busoni',
      license='',
      keywords='plico, prosilica, avt, camera, laboratory, instrumentation control',
      packages=['pysilico_server',
                'pysilico_server.camera_controller',
                'pysilico_server.devices',
                'pysilico_server.process_monitor',
                'pysilico_server.scripts',
                'pysilico_server.utils',
                ],
      entry_points={
          'console_scripts': [
              'pysilico_server_1=pysilico_server.scripts.pysilico_camera_controller_1:main',
              'pysilico_server_2=pysilico_server.scripts.pysilico_camera_controller_2:main',
              'pysilico_kill_all=pysilico_server.scripts.pysilico_kill_processes:main',
              'pysilico_start=pysilico_server.scripts.pysilico_process_monitor:main',
              'pysilico_stop=pysilico_server.scripts.pysilico_stop:main',
          ],
      },
      package_data={
          'pysilico_server': ['conf/pysilico_server.conf', 'calib/*'],
      },
      install_requires=["plico>=0.14",
                        "pysilico>=0.12",
                        "numpy",
                        "psutil",
                        "configparser",
                        "six",
                        "appdirs",
                        "pyfits",
                        "futures",
                        "rebin",
                        "pymba",
                        ],
      include_package_data=True,
      test_suite='test',
      )
