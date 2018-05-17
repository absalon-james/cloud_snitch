from setuptools import setup
from cloud_snitch.meta import version
from cloud_snitch.meta import description

entry_points = """
    [cloud_snitch_models]
    AptPackage=cloud_snitch.models:AptPackageEntity
    Configfile=cloud_snitch.models:ConfigfileEntity
    Device=cloud_snitch.models:DeviceEntity
    Environment=cloud_snitch.models:EnvironmentEntity
    GitRemote=cloud_snitch.models:GitRemoteEntity
    GitRepo=cloud_snitch.models:GitRepoEntity
    GitUntrackedFile=cloud_snitch.models:GitUntrackedFileEntity
    GitUrl=cloud_snitch.models:GitUrlEntity
    Host=cloud_snitch.models:HostEntity
    Interface=cloud_snitch.models:InterfaceEntity
    Mount=cloud_snitch.models:MountEntity
    NameServer=cloud_snitch.models:NameServerEntity
    Partition=cloud_snitch.models:PartitionEntity
    PythonPackage=cloud_snitch.models:PythonPackageEntity
    Uservar=cloud_snitch.models:UservarEntity
    Virtualenv=cloud_snitch.models:VirtualenvEntity
    [console_scripts]
    cloud-snitch-sync=cloud_snitch.sync:main
    cloud-snitch-fake=cloud_snitch.fake:main
    cloud-snitch-constraints=cloud_snitch.constraints:main
    cloud-snitch-clean=cloud_snitch.clean:main
"""

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
    long_description=description,
    entry_points=entry_points
)
