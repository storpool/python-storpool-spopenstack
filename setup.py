#
#-
# Copyright (c) 2014, 2015  StorPool.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from setuptools import setup, find_packages

setup(
	name = 'storpool.spopenstack',
	version = '2.0.0',
	packages = ('storpool', 'storpool.spopenstack',),
	namespace_packages = ('storpool',),

	install_requires = ('storpool>=1.0.0',),

	author = 'Peter Pentchev',
	author_email = 'openstack-dev@storpool.com',
	description = 'OpenStack helpers for the StorPool API',
	license = 'Apache 2.0 License',
	keywords = 'storpool StorPool openstack OpenStack',
	url = 'http://www.storpool.com/',

	zip_safe = True,
)
