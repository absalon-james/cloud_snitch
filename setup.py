from setuptools import setup
from cloud_snitch.meta import version
from cloud_snitch.meta import description

setup(
    name="cloud_snitch",
    version=version,
    author="james absalon",
    author_email="james.absalon@rackspace.com",
    packages=[
        'cloud_snitch',
        'cloud_snitch.models',
        'cloud_snitch.snitchers'
    ],
    package_data={'cloud_snitch': ['cloud_snitch/*']},
    long_description=description
)
