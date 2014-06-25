# -*- coding: utf-8 -*-

# Application that sync folders to Amazon Glacier.
#
# Copyright (C) 2014 Tadeusz Magura-Witkowski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import json
import os
from calendar import timegm
from datetime import datetime
from boto.glacier.layer2 import Layer2
from boto.utils import parse_ts

class File(object):
	def __init__(self):
		super(File, self).__init__()

	@property
	def last_modified(self):
		raise NotImpleNotImplementedError()

	def __gt__(self, other):
		return self.last_modified > other.last_modified

	def __hash__(self):
		return hash(self.path)

	def __eq__(self, other):
		return self.path == other.path

	def __repr__(self):
		return 'local://%s' % self.path if isinstance(self, LocalFile) else 'cloud://%s' % self.uuid

	__str__ = __repr__

class Filesystem(object):
	def __init__(self):
		super(Filesystem, self).__init__()

	@property
	def files(self):
		raise NotImpleNotImplementedError()

class SimpleDiffer(object):
	def __init__(self, local_files, remote_files):
		super(SimpleDiffer, self).__init__()
		self.local_files = local_files
		self.remote_files = remote_files
		
	@property
	def differences(self):
		new_files = self.local_files - self.remote_files
		deleted_files = self.remote_files - self.local_files

		maybe_modified_files = set([])

		for curr_file in self.local_files:
			for remote_file in self.remote_files:
				if curr_file == remote_file:
					maybe_modified_files.add((curr_file, remote_file))

		return {'new_files': new_files, 'deleted_files': deleted_files, 'maybe_modified_files': maybe_modified_files}

class LastModifiedDiffer(object):
	def __init__(self, local_file, remote_file):
		super(LastModifiedDiffer, self).__init__()
		self.local_file = local_file
		self.remote_file = remote_file

	@property
	def local_is_modified(self):
		return self.local_file > self.remote_file

class DifferRunner(object):
	def __init__(self, local_filesystem, remote_filesystem, differs):
		super(DifferRunner, self).__init__()
		self.local_files = set(local_filesystem.files)
		self.remote_files = set(remote_filesystem.files)
		
		self.differs = differs

	@property
	def differences(self):
		simplediffer = SimpleDiffer(self.local_files, self.remote_files)
		simpleresult = simplediffer.differences
		
		files_differs_decided_to_reupload = set([])

		# we will only process maybe_modified_files
		for currpair in simpleresult['maybe_modified_files']:
			for current_differ in self.differs:
				differ = current_differ(*currpair)

				if differ.local_is_modified:
					files_differs_decided_to_reupload.add(currpair)

		return {'new_files': simpleresult['new_files'], 'deleted_files': simpleresult['deleted_files'], 'modified_files': files_differs_decided_to_reupload}

class LocalFile(File):
	def __init__(self, path):
		super(LocalFile, self).__init__()

		self.path = path

	@property
	def last_modified(self):
		return datetime.fromtimestamp(os.path.getmtime(self.path))

class LocalFilesystem(Filesystem):
	def __init__(self, *dirs):
		super(LocalFilesystem, self).__init__()
		self.dirs = dirs
		
	@property
	def files(self):
		for curr_dir in self.dirs:
			filelist = os.listdir(curr_dir)

			for curr_file in filelist:
				full_file_path = os.path.join(curr_dir, curr_file)

				if not os.path.isfile(full_file_path):
					continue # skip non-normal files

				yield LocalFile(full_file_path)

# TODO: make this class nicer!
class RemoteFile(File):
	def __init__(self, file_json_data):
		super(RemoteFile, self).__init__()		

		self.file_json_data = file_json_data
	@property
	def last_modified(self):
		return datetime.utcfromtimestamp(self.file_json_data['last_modified'])

	@property
	def uuid(self):
		return self.file_json_data['uuid']

	@property
	def path(self):
		return self.file_json_data['path']

	@property
	def uploaded_at(self):
		return datetime.utcfromtimestamp(self.file_json_data['uploaded_at'])
		
class RemoteFilesystem(Filesystem):
	def __init__(self, glacier_local_database, vault):
		super(RemoteFilesystem, self).__init__()
		self.glacier_local_database = glacier_local_database
		self.vault = vault
		
	@property
	def files(self):
		return self.glacier_local_database.files

	def upload_file(self, local_file):
		uuid = self.vault.concurrent_create_archive_from_file(local_file.path, local_file.path)

		# Just for testing
		# import random
		# uuid = '%s%s' % (random.random(), local_file)

		self.glacier_local_database.add_file(local_file, uuid)

	def delete_file(self, remote_file):
		self.vault.delete_archive(remote_file.uuid)

		self.glacier_local_database.delete_file(remote_file)

class InvalidJobTypeException(Exception):
	pass

class GlacierLocalDatabaseFile(object):
	def __init__(self, filename):
		super(GlacierLocalDatabaseFile, self).__init__()
		self.filename = filename

		try:
			with file(self.filename, 'r') as db_file:
				self._filedata = json.load(db_file)
		except IOError: # we do not have database file yet
			self._filedata = {'files': [], 'pending_jobs': []}

	@property
	def files(self):
		for curr_file in self._filedata['files']:
			yield RemoteFile(curr_file)

	@property
	def pending_jobs(self):
		for entry in self._filedata['pending_jobs']:
			if entry['__job_type'] in (RetreiveInvetoryJob.__name__, PendingJob.__name__):
				yield globals()[entry['__job_type']](entry)
			else:
				raise InvalidJobTypeException('Invalid class name in __job_type')

	def write(self):
		with file(self.filename, 'w') as db_file:
			json.dump(self._filedata, db_file)

	def add_file(self, local_file, uuid):
		file_entry = {
			'path': local_file.path,
			'last_modified': timegm(local_file.last_modified.timetuple()),
			'uploaded_at': timegm(datetime.now().timetuple()),
			'uuid': uuid
		}

		self._filedata['files'].append(file_entry)

		self.write()
	def restore_from_amazon(self, amaozn_data):
		self._filedata['files'] = []
		for archive in amaozn_data:
			file_entry = {
				'path': archive['ArchiveDescription'],
				'last_modified' parse_ts(archive['CreationDate']),
				'uploaded_at': parse_ts(archive['CreationDate']),
				'uuid': archive['ArchiveId']
			}
			self._filedata['files'].append(file_entry)

		self.write()

	def delete_file(self, remote_file):
		self._filedata['files'] = [entry for entry in self._filedata['files'] if entry['uuid'] != remote_file.uuid]

		self.write()

	def add_pending_job(self, job):
		job_entry = {
			'__job_type': job.__class__.__name__
		}
		job_entry.update(job.__dict__)
		self._filedata['pending_jobs'].append(job_entry)

		self.write()
	def delete_pending_job(self, job):
		self._filedata['pending_jobs'] = [entry for entry in self._filedata['pending_jobs'] if entry['uuid'] != job.uuid]

		self.write()

class PendingJob(object):
	def __init__(self, uuid_or_jsondata):
		super(PendingJob, self).__init__()

		if isinstance(uuid_or_jsondata, dict):
			self.__dict__.update(uuid_or_jsondata)
		else:
			self.uuid = uuid_or_jsondata

	def to_JSON(self):
		return json.dumps(self, default=lambda o: o.__dict__)

	def __hash__(self):
		return hash(self.uuid)

	def __eq__(self, other):
		return self.uuid == other.uuid

class RetreiveInvetoryJob(PendingJob):
	pass

class GlacierSync(object):
	def __init__(self, aws, database, delayed_delete, dirs_to_sync, print_status=False):
		super(GlacierSync, self).__init__()
		self.aws = aws
		self.delayed_delete = delayed_delete

		self._database = GlacierLocalDatabaseFile(database)
		self._aws_connection = Layer2(aws_access_key_id=self.aws['access_key'], aws_secret_access_key=self.aws['secret_key'], region_name=self.aws['region'])
		self._vault = self._aws_connection.get_vault(self.aws['vault_name'])

		self._local_filesystem = LocalFilesystem(*dirs_to_sync)
		self._remote_filesystem = RemoteFilesystem(self._database, self._vault)

		self.print_status = print_status

	def sync(self):
		differ_runner = DifferRunner(self._local_filesystem, self._remote_filesystem, [LastModifiedDiffer])
		
		differences = differ_runner.differences

		for curr_file in differences['new_files']:
			if self.print_status:
				print 'New file uploading: %s' % curr_file
			self._remote_filesystem.upload_file(curr_file)

		for curr_file in differences['deleted_files']:
			if self.print_status:
				print 'Removing file: %s' % curr_file
			self._remote_filesystem.delete_file(curr_file)

		for curr_file in differences['modified_files']:
			if self.print_status:
				print 'File has changed: %s' % curr_file[0]
			self._remote_filesystem.upload_file(curr_file[0]) # upload local
			self._remote_filesystem.delete_file(curr_file[1]) # remove remote

	def restoredb(self):
		# check if we are running some job for it
		for job in self._database.pending_jobs:
			if isinstance(job, RetreiveInvetoryJob): # yes, we are...
				aws_job = self._vault.get_job(inventory_job)
				
				if not aws_job.completed:
					if self.print_status:
						print 'AWS haven\'t completed job yet. Run this command again after some time.'
					return False

				aws_job_data = json.loads(aws_job.get_output().read())

				self._remote_filesystem.restore_from_amazon(aws_job_data['ArchiveList'])

				if self.print_status:
					print 'Local AWS File database is now synced to file list on glacier.'

				return True
