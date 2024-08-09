from setuptools import setup

setup(
    name='hmse_utils',
    version='1.0.0',
    description="Python package with all HMSE local utilities",
    author="Mateusz Pawlowicz",
    install_requires=[
        'flopy==3.7.0',
        'numpy',
        'phydrus==0.3.0',
        'scipy',
        'StrEnum==0.4.8',
        'Werkzeug==2.2.0',
        'zipp==3.8.1',
    ]
)
