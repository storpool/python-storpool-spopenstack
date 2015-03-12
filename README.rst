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
