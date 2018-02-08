#!/usr/bin/python

import glob
from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = '''
---
module: file_snitch

short_description: Gathers configuration files.

version_added: "2.1.6"

description:
    - "Pulls configuration files from a host"
    - "Matches files according to list."

extends_documentation_fragment:
    - azure

author:
    - James Absalon
'''

RETURN = '''
payload:
    description: |
       Dict keyed matching file name. The value of each will be the contents
       of the file.
    type: dict
doctype:
    description: Type of document. Will always be 'file_dict'
    type: str
'''

_FILE_TARGETS = [
    '/etc/aide/aide.conf.d/ZZ_aide_exclusions',
    '/etc/aodh/aodh.conf',
    '/etc/aodh/api_paste.ini',
    '/etc/aodh/policy.json',
    '/etc/apache2/mods-available/mpm_event.conf',
    '/etc/apache2/ports.conf',
    '/etc/apache2/sites-available/aodh-httpd.conf',
    '/etc/apache2/sites-available/ceilometer-httpd.conf',
    '/etc/apache2/sites-available/gnocchi-httpd.conf',
    '/etc/apache2/sites-available/ironic-httpd.conf',
    '/etc/apache2/sites-available/keystone-httpd.conf',
    '/etc/apache2/sites-available/openstack-dashboard.conf',
    '/etc/apparmor.d/lxc/lxc-openstack',
    '/etc/apt-cacher-ng/acng.conf',
    '/etc/apt/preferences.d/openstack_pinned_packages.pref',
    '/etc/apt/preferences.d/projectcalico_pin.pref',
    '/etc/audit/rules.d/osas-auditd.rules',
    '/etc/bird/bird.conf',
    '/etc/bird/bird6.conf',
    '/etc/ceilometer/api_paste.ini',
    '/etc/ceilometer/ceilometer.conf',
    '/etc/ceilometer/event_definitions.yaml',
    '/etc/ceilometer/event_pipeline.yaml',
    '/etc/ceilometer/gnocchi_resources.yaml',
    '/etc/ceilometer/loadbalancer_v2_meter_definitions.yaml',
    '/etc/ceilometer/osprofiler_event_definitions.yaml',
    '/etc/ceilometer/pipeline.yaml',
    '/etc/ceilometer/policy.json',
    '/etc/ceilometer/rootwrap.conf',
    '/etc/ceph/ceph.client.*.keyring',
    '/etc/chrony.conf',
    '/etc/chrony/chrony.conf',
    '/etc/cinder/api-paste.ini',
    '/etc/cinder/cinder.conf',
    '/etc/cinder/policy.json',
    '/etc/cinder/rootwrap.conf',
    '/etc/cron.d/sysstat',
    '/etc/cron.daily/mlocate',
    '/etc/default/irqbalance',
    '/etc/default/lsyncd',
    '/etc/default/lxc-net',
    '/etc/default/mariadb',
    '/etc/default/memcached',
    '/etc/default/mysql',
    '/etc/default/rabbitmq-server',
    '/etc/default/sysstat',
    '/etc/default/tftpd-hpa',
    '/etc/default/unbound',
    '/etc/environment',
    '/etc/etcd/etcd.conf',
    '/etc/glance/glance-api-paste.ini',
    '/etc/glance/glance-api.conf',
    '/etc/glance/glance-cache.conf',
    '/etc/glance/glance-manage.conf',
    '/etc/glance/glance-registry-paste.ini',
    '/etc/glance/glance-registry.conf',
    '/etc/glance/glance-scrubber.conf',
    '/etc/glance/glance-swift-store.conf',
    '/etc/glance/policy.json',
    '/etc/glance/schema-image.json',
    '/etc/glance/schema.json',
    '/etc/gnocchi/api-paste.ini',
    '/etc/gnocchi/gnocchi.conf',
    '/etc/gnocchi/policy.json',
    '/etc/haproxy/conf.d/*',
    '/etc/haproxy/conf.d/00-haproxy',
    '/etc/heat/api-paste.ini',
    '/etc/heat/environment.d/default.yaml',
    '/etc/heat/heat.conf',
    '/etc/heat/policy.json',
    '/etc/heat/templates/AWS_CloudWatch_Alarm.yaml',
    '/etc/heat/templates/AWS_RDS_DBInstance.yaml',
    '/etc/horizon/local_settings.py',
    '/etc/httpd/conf.d/keystone-httpd.conf',
    '/etc/httpd/conf.d/ports.conf',
    '/etc/httpd/conf.modules.d/mpm_event.conf',
    '/etc/init/aodh-*.conf',
    '/etc/init/ceilometer-*.conf',
    '/etc/init/cinder-*.conf',
    '/etc/init/etcd.conf',
    '/etc/init/etcd.override',
    '/etc/init/git-daemon.conf',
    '/etc/init/glance-*.conf',
    '/etc/init/gnocchi-*.conf',
    '/etc/init/heat-*.conf',
    '/etc/init/ironic-conductor.conf',
    '/etc/init/keystone-*.conf',
    '/etc/init/lxc-net.override',
    '/etc/init/magnum-*.conf',
    '/etc/init/neutron-*.conf',
    '/etc/init/nova-*.conf',
    '/etc/init/sahara-*.conf',
    '/etc/init/swift-.conf',
    '/etc/ironic/ironic.conf',
    '/etc/ironic/policy.json',
    '/etc/ironic/rootwrap.conf',
    '/etc/keepalived/keepalived.conf',
    '/etc/keystone/domains/keystone.*.conf',
    '/etc/keystone/keystone-paste.ini',
    '/etc/keystone/keystone.conf',
    '/etc/keystone/policy.json',
    '/etc/libvirt/libvirtd.conf',
    '/etc/libvirt/qemu.conf',
    '/etc/logrotate.d/os_aggregate_storage',
    '/etc/lsyncd/lsyncd.conf.lua',
    '/etc/lvm/lvm.conf',
    '/etc/lxc/default.conf',
    '/etc/lxc/lxc-openstack.conf',
    '/etc/magnum/api-paste.ini',
    '/etc/magnum/magnum.conf',
    '/etc/magnum/policy.json',
    '/etc/memcached.conf',
    '/etc/mysql/conf.d/cluster.cnf',
    '/etc/mysql/debian.cnf',
    '/etc/mysql/my.cnf',
    '/etc/network/interfaces.d/*.cfg',
    '/etc/network/interfaces.d/lxc-net-bridge.cfg',
    '/etc/neutron/api-paste.ini',
    '/etc/neutron/dnsmasq-neutron.conf',
    '/etc/neutron/neutron.conf',
    '/etc/neutron/plugins/plumgrid/pgrc',
    '/etc/neutron/plugins/plumgrid/plumlib.ini',
    '/etc/neutron/policy.json',
    '/etc/neutron/rootwrap.conf',
    '/etc/nginx/conf.d/keystone-*.conf',
    '/etc/nginx/nginx.conf',
    '/etc/nginx/sites-available/keystone-*.conf',
    '/etc/nginx/sites-available/openstack-slushee.vhost',
    '/etc/nova/api-paste.ini',
    '/etc/nova/nova-interfaces-template',
    '/etc/nova/nova.conf',
    '/etc/nova/policy.json',
    '/etc/nova/rootwrap.conf',
    '/etc/openstack-release',
    '/etc/rabbitmq/rabbitmq-env.conf',
    '/etc/rabbitmq/rabbitmq.config',
    '/etc/rally/rally.conf',
    '/etc/resolv.conf',
    '/etc/resolvconf/resolv.conf.d/base',
    '/etc/rsyncd.conf',
    '/etc/rsyslog.conf',
    '/etc/rsyslog.d/49-swift.conf',
    '/etc/rsyslog.d/51-remote-logging.conf',
    '/etc/rsyslog.d/99-rsyslog-client.conf',
    '/etc/sahara/api-paste.ini',
    '/etc/sahara/policy.json',
    '/etc/sahara/rootwrap.conf',
    '/etc/sahara/sahara.conf',
    '/etc/security/limits.d/99-limits.conf',
    '/etc/shibboleth/attribute-map.xml',
    '/etc/shibboleth/shibboleth2.xml',
    '/etc/ssh/sshd_config',
    '/etc/sudoers.d/cinder_sudoers',
    '/etc/sudoers.d/ironic_sudoers',
    '/etc/sudoers.d/neutron_sudoers',
    '/etc/sudoers.d/nova_sudoers',
    '/etc/sudoers.d/openstack-ansible',
    '/etc/sudoers.d/sahara_sudoers',
    '/etc/swift/account-server/account-server-replicator.conf',
    '/etc/swift/account-server/account-server.conf',
    '/etc/swift/container-server/container-reconciler.conf',
    '/etc/swift/container-server/container-server-replicator.conf',
    '/etc/swift/container-server/container-server.conf',
    '/etc/swift/container-sync-realms.conf',
    '/etc/swift/dispersion.conf',
    '/etc/swift/drive-audit.conf',
    '/etc/swift/memcache.conf',
    '/etc/swift/object-server/object-expirer.conf',
    '/etc/swift/object-server/object-server-replicator.conf',
    '/etc/swift/object-server/object-server.conf',
    '/etc/swift/proxy-server/proxy-server.conf',
    '/etc/swift/scripts/account.contents',
    '/etc/swift/scripts/container.contents',
    '/etc/swift/scripts/object-*.contents',
    '/etc/swift/scripts/swift_rings.py',
    '/etc/swift/scripts/swift_rings_check.py',
    '/etc/swift/swift.conf',
    '/etc/sysconfig/irqbalance',
    '/etc/sysconfig/lxc-net',
    '/etc/sysconfig/memcached',
    '/etc/sysconfig/network-scripts/ifcfg-lxcbr0',
    '/etc/sysconfig/network-scripts/route-*',
    '/etc/systemd/system/aodh-*.service',
    '/etc/systemd/system/ceilometer-*.service',
    '/etc/systemd/system/cinder-*.service',
    '/etc/systemd/system/etcd.service.d/override.conf',
    '/etc/systemd/system/glance-*.service',
    '/etc/systemd/system/gnocchi-*.service',
    '/etc/systemd/system/heat-*.service',
    '/etc/systemd/system/ironic-*.service',
    '/etc/systemd/system/keystone-*.service',
    '/etc/systemd/system/magnum-*.service',
    '/etc/systemd/system/mariadb.service.d/limits.conf',
    '/etc/systemd/system/memcached.service.d/limits.conf',
    '/etc/systemd/system/memcached.service.d/systemd-restart-on-failure.conf',
    '/etc/systemd/system/neutron-*.service',
    '/etc/systemd/system/nova-*.service',
    '/etc/systemd/system/rabbitmq-server.service.d/limits.conf',
    '/etc/systemd/system/rabbitmq-server.service.d/systemd-restart-on-failure.conf',  # noqa: E501
    '/etc/systemd/system/sahara-*.service',
    '/etc/systemd/system/swift-*.service',
    '/etc/tmpfiles.d//gnocchi-*.conf',
    '/etc/tmpfiles.d/aodh-*.conf',
    '/etc/tmpfiles.d/ceilometer-*.conf',
    '/etc/tmpfiles.d/cinder-*.conf',
    '/etc/tmpfiles.d/heat-*.conf',
    '/etc/tmpfiles.d/ironic-*.conf',
    '/etc/tmpfiles.d/keystone.conf',
    '/etc/tmpfiles.d/magnum.conf',
    '/etc/tmpfiles.d/openstack-*.conf',
    '/etc/tmpfiles.d/sahara.conf',
    '/etc/tmpfiles.d/swift-*.conf',
    '/etc/unbound/unbound.conf',
    '/etc/uwsgi/keystone-*.ini',
    '/lib/systemd/system/git.socket',
    '/lib/systemd/system/git@.service',
    '/openstack/venvs/horizon-*/bin/horizon-manage.py',
    '/openstack/venvs/horizon-*/lib/python2.7/dist-packages/openstack_dashboard/local/enabled/_80_admin_default_panel.py',  # noqa: E501
    '/openstack/venvs/horizon-*/lib/python2.7/dist-packages/openstack_dashboard/wsgi/django.wsgi',  # noqa: E501
    '/openstack/venvs/tempest-*/etc/tempest.conf',
    '/opt/container-setup.sh',
    '/opt/keystone-credential-rotate.sh',
    '/opt/keystone-fernet-rotate.sh',
    '/opt/neutron-ha-tool.py',
    '/opt/neutron-ha-tool.sh',
    '/opt/op-release-script.sh',
    '/opt/openstack_tempest_gate.sh',
    '/opt/venv-build-script.sh',
    '/root/.config/openstack/clouds.yaml',
    '/root/.my.cnf',
    '/root/.pip/pip.conf',
    '/root/.tempest/etc/tempest.conf',
    '/root/openrc',
    '/tmp/*-secret.xml',
    '/tmp/nova-secret.xml',
    '/usr/local/bin/lxc-system-manage',
    '/var/lib/lxc/*/*.ini',
    '/var/lib/lxc/*/autodev',
    '/var/lib/lxc/*/veth-cleanup.sh',
    '/var/lib/lxc/LXC_NAME/rootfs/etc/sudoers.d/openstack-ansible',
    '/var/lib/nova/lxd-init.sh',
    '/var/tmp/openstack-host-hostfile-setup.sh',
    '/var/tmp/openstack-nova-key.sh',
    '/var/www/cgi-bin/aodh/aodh-api',
    '/var/www/cgi-bin/ceilometer/ceilometer-api',
    '/var/www/cgi-bin/gnocchi/gnocchi-api',
    '/var/www/cgi-bin/ironic/ironic.wsgi',
    '/var/www/repo/os-releases/*/MANIFEST.in',
    '/var/www/repo/os-releases/*/requirements.txt',
    '/var/www/repo/os-releases/*/requirements_absolute_requirements.txt',
    '/var/www/repo/os-releases/*/requirements_constraints.txt',
    '/var/www/repo/os-releases/*/venv-build-options-*.txt',
    '/var/www/repo/repo_prepost_cmd.sh'
]


def get_file(filename):
    """Get contents of a file.

    :param filename: Name of the file
    :type filename: str
    :returns: Contents of file
    :rtype: str
    """
    with open(filename, 'r') as f:
        contents = f.read()
    # @TODO - Mask secure content
    return contents


def run_module():
    module_args = dict()

    result = dict(
        changed=False,
        payload={},
        doctype='file_dict'
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    filenames = []
    for t in _FILE_TARGETS:
        filenames += glob.glob(t)

    for filename in filenames:
        result['payload'][filename] = get_file(filename)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
