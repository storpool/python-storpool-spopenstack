Description
===========

This package contains Python helper classes to let the StorPool drivers in
OpenStack use the StorPool API in a common way.

StorPool is distributed data storage software running on standard x86 servers.
StorPool aggregates the performance and capacity of all drives into a shared
pool of storage distributed among the servers.  Within this storage pool the
user creates thin-provisioned volumes that are exposed to the clients as block
devices.  StorPool consists of two parts wrapped in one package - a server and
a client.  The StorPool server allows a hypervisor to act as a storage node,
while the StorPool client allows a hypervisor node to access the storage pool
and act as a compute node.  In OpenStack terms the StorPool solution allows
each hypervisor node to be both a storage and a compute node simultaneously.

Version history
===============

2.2.0
-----

- add unit tests
- reformat the source code using black
- fix some flake8 and pylint nits
- support Python 3

2.1.1
-----

- do not detach volumes with names that do not start with our prefix!
- do not treat snapshot attachment requests as stale
- do not wait quite that long before force-detaching a volume

2.1.0
-----

- add the remove_keys() method to the SPLockedJSONDB class
- remove stale requests from our openstack-attach.json cache file

2.0.0
-----

- instead of raising the AttachmentInUse exception, forcibly detach
  the volume on the last attempt
- remove the now unused AttachmentInUse exception

1.0.3
-----

- ignore nonexistent request IDs upon detaching
- allow the default "os" name prefix for volumes created by the OpenStack tools
  to be overridden by the storpool.conf file's new SP_OPENSTACK_VOLUME_PREFIX
  setting
- raise a specific exception when a volume is still in use and may not be
  detached so that the Nova attachment driver may raise a specific exception in
  its turn

1.0.2
-----

- drop the dependency on oslo_concurrency in setup.py, too

1.0.1
-----

- use our own locking instead of oslo_concurrency, making it much easier
  (or even at all possible) to work with OpenStack Juno
- wait for all consumers of the attached StorPool volume to release it when
  detaching it
- wait a bit longer for a newly-attached volume to appear
- only retry locking on a "file exists" error; any other errors are fatal

1.0.0
-----

- first public release
