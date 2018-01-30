# cloud_snitch
Gathers information from an osa cloud

### How to run
```shell
# From the cloud_snitch repo directory
openstack-ansible snitch.yml
```

cloud_snitch.rc.example contains some example environment variables that enable the cloud_snitch plugins and configure where local data is stored.(likely to change)

modules in the modules directory should have symlinks in the osa ansible plugin library directory.

example:
```shell
 ln -s <path to repo>/cloud_snitch/modules/pkg_snitch.py /etc/ansible/roles/plugins/library/pkg_snitch
```

Current modules:
 - pkg_snitch
 - pip_snitch(coming soon)
