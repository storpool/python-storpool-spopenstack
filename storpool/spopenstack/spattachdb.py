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

"""
Helper routines for the StorPool drivers in the OpenStack codebase.
"""

import os
import time

from itertools import ifilter

from storpool.spconfig import SPConfig
from storpool.spapi import Api, ApiError

from splocked import SPLockedJSONDB


class AttachDB(SPLockedJSONDB):
	def __init__(self, fname='/var/spool/openstack-storpool/openstack-attach.json', log=None):
		super(AttachDB, self).__init__(fname)
		self._api = None
		self._config = None
		self._ourId = None
		self.LOG = log

	def config(self):
		if self._config is None:
			self._config = SPConfig()
			self._ourId = int(self._config['SP_OURID'])
		return self._config

	def api(self):
		if self._api is None:
			cfg = self.config()
			self._api = Api(host=cfg['SP_API_HTTP_HOST'], port=cfg['SP_API_HTTP_PORT'], auth=cfg['SP_AUTH_TOKEN'])
		return self._api

	def volumeName(self, id):
		return 'os--volume-{id}'.format(id=id)

	def volsnapName(self, id, req_id):
		return 'os--volsnap-{id}--req-{req_id}'.format(id=id, req_id=req_id)

	def snapshotName(self, type, id, more=None):
		return 'os--{t}--{m}--snapshot-{id}'.format(t=type, m='none' if more is None else more, id=id)

	# TODO: cache at least the API attachments data
	def _get_attachments_data(self):
		return (self.get(), self.api().attachmentsList())

	def sync(self, req_id, detached):
		with self:
			(attach_req, apiatt) = self._get_attachments_data()

			attach = attach_req.get(req_id, None)
			if attach is None:
				raise Exception('StorPoolDriver._attach_sync() invoked for unknown request {req}'.format(req=req_id))

			# OK, let's first see what *should be* attached
			vols = {}
			if detached is None:
				attach_req = attach_req.itervalues()
			else:
				# Detaching this particular volume in this request?
				attach_req = ifilter(lambda att: att['volume'] != detached or att['id'] != req_id, attach_req.itervalues())
			for att in attach_req:
				v = att['volume']
				if v not in vols or vols[v]['rights'] < att['rights']:
					vols[v] = { 'volume': v, 'volsnap': att.get('volsnap', False), 'rights': att['rights'] }

			# OK, let's see what *is* attached
			apiatt = filter(lambda att: att.client == self._ourId, apiatt)
			attached = dict(map(lambda att: (att.volume, {'volume': att.volume, 'rights': 2 if att.rights == "rw" else 1, 'snapshot': att.snapshot}), apiatt))

			# Right, do we need to do anything now?
			for v in vols.itervalues():
				n = v['volume']
				if n in attached and attached[n]['rights'] >= v['rights']:
					continue
				volsnap = v['volsnap']
				self._attach_and_wait(client=self._ourId, volume=n, volsnap=volsnap, rights=v['rights'])

			for v in attached.itervalues():
				n = v['volume']
				if n in vols:
					volsnap = vols[n]['volsnap']
					type = 'snapshot' if volsnap else 'volume'
					if vols[n]['rights'] < v['rights']:
						self._attach_and_wait(client=self._ourId, volume=n, volsnap=volsnap, rights=vols[n]['rights'])
				else:
					self._detach_and_wait(client=self._ourId, volume=n, volsnap=v['snapshot'])

	def _attach_and_wait(self, client, volume, volsnap, rights):
		if volsnap:
			if rights > 1:
				raise ApiError('StorPool: cannot attach a snapshot in read/write mode')
			self.api().volumesReassign(json=[{ 'snapshot': volume, 'ro': [client] }])
		else:
			mode = 'rw' if rights == 2 else 'ro'
			self.api().volumesReassign(json=[{ 'volume': volume, mode: [client] }])
		devpath = '/dev/storpool/' + volume
		for i in xrange(10):
			if os.path.exists(devpath):
				break
			time.sleep(1)

	def _detach_and_wait(self, client, volume, volsnap):
		count = 10
		while True:
			try:
				if volsnap:
					self.api().volumesReassign(json=[{ 'snapshot': volume, 'detach': [client] }])
				else:
					self.api().volumesReassign(json=[{ 'volume': volume, 'detach': [client] }])
				break
			except ApiError as e:
				if e.name == 'invalidParam' and 'is open at' in e.desc:
					if count < 1:
						raise
					time.sleep(0.3)
					count -= 1
