#
#-
# Copyright (c) 2014  StorPool.
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

"""
A trivial JSON key/value store protected by a lockfile.
"""

from errno import ENOENT
from os.path import dirname

import json
import os
import time

from oslo_concurrency.lockutils import synchronized


class SPLockedFile(object):
	def __init__(self, fname):
		self._fname = fname
		self._lockfname = self._fname + '.splock'
		self._lockfd = None
		self._last = None

	def changed(self):
		last = self._last
		try:
			st = os.stat(self._fname)
		except OSError:
			if last is not None:
				last = None
				return True
			else:
				return False
		if last is None:
			return True
		return st.st_ino != last.st_ino or st.st_mtime != last.st_mtime or st.st_size != last.st_size

	def __enter__(self):
		assert self._lockfd is None
		for x in xrange(10):
			try:
				f = os.open(self._lockfname, os.O_CREAT | os.O_EXCL, 0600)
				break
			except OSError as e:
				time.sleep(0.1)
		else:
			raise Exception('Could not lock the {f} file (using {fl})'.format(f=self._fname, fl=self._lockfname))
		self._lockfd = f

	def __exit__(self, etype, eval, tb):
		os.close(self._lockfd)
		self._lockfd = None

		# If no exceptions have been raised, update the stat(2) cache
		if etype is None:
			try:
				self._last = os.stat(self._fname)
			except OSError:
				self._last = None

		try:
			os.remove(self._lockfname)
		except OSError:
			pass

	def jsload(self):
		with self:
			with open(self._fname, 'r') as f:
				return json.loads(f.read())

	def jsdump(self, obj):
		with self:
			with open(self._fname, 'w') as f:
				f.write(json.dumps(obj))

class SPLockedJSONDB(SPLockedFile):
	def __init__(self, fname):
		super(SPLockedJSONDB, self).__init__(fname)
		self._data = None

	@synchronized('storpool-splocked-get')
	def get(self):
		if self._data is None or self.changed():
			try:
				self._data = self.jsload()
			except IOError as e:
				# No such file or directory?
				if e.errno == ENOENT:
					self._data = {}
				else:
					raise
		return self._data

	@synchronized('storpool-splocked-add-remove')
	def add(self, key, val):
		d = self.get()
		d[key] = val
		self.jsdump(d)

	@synchronized('storpool-splocked-add-remove')
	def remove(self, key):
		d = self.get()
		if key in d:
			del d[key]
			self.jsdump(d)
