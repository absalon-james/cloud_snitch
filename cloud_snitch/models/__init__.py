from .apt import AptPackageEntity # noqa F401
from .configfile import ConfigfileEntity # noqa F401
from .environment import EnvironmentEntity # noqa F401
from .environmentlock import EnvironmentLockEntity # noqa F401
from .gitrepo import GitUntrackedFileEntity # noqa F401
from .gitrepo import GitUrlEntity # noqa F401
from .gitrepo import GitRemoteEntity # noqa F401
from .gitrepo import GitRepoEntity # noqa F401
from .host import NameServerEntity # noqa F401
from .host import PartitionEntity # noqa F401
from .host import DeviceEntity # noqa F401
from .host import InterfaceEntity # noqa F401
from .host import HostEntity # noqa F401
from .host import MountEntity # noqa F401
from .uservar import UservarEntity # noqa F401
from .virtualenv import VirtualenvEntity # noqa F401
from .virtualenv import PythonPackageEntity # noqa F401

from .registry import Registry
registry = Registry()
