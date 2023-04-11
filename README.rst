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

3.2.0
-----

- Do not require `SP_OURID` to be defined in the StorPool configuration
  so that we can support iSCSI-only deployments
- Add the optional `override_config` dictionary to the AttachDB constructor
  to skip reading the StorPool configuration files altogether. This should
  simplify isolated deployments and allow the StorPool OpenStack helper
  tools to be configured with settings read from the OpenStack config
  files only
- Depend on `storpool >= 7.2.0` for `override_config` support in
  the `SPConfig` configuration class
- Depend on `storpool < 8`, since incompatible changes are planned in
  the StorPool API bindings library itself
- Minor refactoring so that stricter type checking can be enabled
- Build and testing infrastructure changes:
    - clamp the versions of some Python build tools and required libraries;
      add both lower and upper version constraints
    - put Tox environment commands on separate lines
    - move the configuration of some static checker tools to
      the pyproject.toml file

3.1.0
-----

- Reraise unexpected StorPool API errors instead of ignoring them
- Handle the StorPool API returning a "busy" error code instead of
  the "invalidParam" one previously
- Fix attempting to lock a file for the second time after the first one
  was unsuccessful
- Use file locking, not a separate lockfile; the attachment JSON file
  must now exist, but it is usually created as part of setting up
  the Cinder and Nova group membership anyway
- Add the year 2021 to the copyright notices
- Reformat the source using version 21 of the black tool
- Disable some more pylint diagnostics because of Python 2 compatibility

3.0.1
-----

- Really implement the "do not detach unrecognized StorPool volumes" bugfix
  from version 3.0.0; the solution there was incomplete
- Recognize the fact that an AttachDB object is never ever instantiated
  without a logger and make the logger parameter non-optional
- Add type hints and fix some minor type mismatches found by the mypy tool
- Refactor the tests for the AttachDB.sync() method
- Apply some minor style improvements

3.0.0
-----

- INCOMPATIBLE CHANGE: do not detach unrecognized StorPool volumes when
  the SPAttachDB.sync() method is invoked to allow for OpenStack services
  running in different containers on the same physical host
- do not use external mock and pathlib libraries for the Python 3.x tests


2.2.1
-----

- do not pass a Unicode string argument as a port "number" to the StorPool
  API bindings object
- use the storpool.spapi.Api.fromConfig() method and consequently bump
  the dependency on the "storpool" module to version 4.0.0 or above


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
