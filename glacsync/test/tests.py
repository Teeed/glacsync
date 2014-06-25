# -*- coding: utf-8 -*-
#
# Application that sync folders to Amazon Glacier.
# https://github.com/Teeed/glacsync
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

import unittest
from datetime import datetime, timedelta
import tempfile
import time
import copy

from ..glacsync import *

class Struct:
	def __init__(self, **entries): 
		self.__dict__.update(entries)

class FileTested(File):
	def __init__(self, path='', uuid='', last_modified_timedelta=timedelta()):	
		super(FileTested, self).__init__()

		self._last_modified = datetime.now() + last_modified_timedelta
		self.path = path
		self.uuid = uuid

	@property
	def last_modified(self):
		return self._last_modified

class TestFileGt(unittest.TestCase):
	def setUp(self):
		self.file = FileTested()

	def test_other_file_newer(self):
		# other file is newer
		other_file = FileTested(last_modified_timedelta=timedelta(minutes=5))

		self.assertLess(self.file, other_file)

	def test_other_file_older(self):
		# other file is newer
		other_file = FileTested(last_modified_timedelta=timedelta(minutes=-5))

		self.assertGreater(self.file, other_file)

class TestFileEq(unittest.TestCase):
	def setUp(self):
		self.file1 = FileTested(path='path/1.txt')

	def test_equal(self):
		file2 = FileTested(path='path/1.txt')

		self.assertEqual(self.file1, file2)

	def test_not_equal(self):
		file2 = FileTested(path='path/2.txt')
		
		self.assertNotEqual(self.file1, file2)

class TestFileHash(unittest.TestCase):
	def setUp(self):
		self.file1 = FileTested(path='path/1.txt')

	def test_equal(self):
		file2 = FileTested(path='path/1.txt')

		self.assertEqual(hash(self.file1), hash(file2))

	def test_not_equal(self):
		file2 = FileTested(path='path/2.txt')
		
		self.assertNotEqual(hash(self.file1), hash(file2))

class TestSimpleDiffer(unittest.TestCase):
	def _test(self, local, remote, new_files, deleted_files, maybe_modified_files):
		local_files = set(local)
		remote_files = set(remote)

		differ = SimpleDiffer(local_files, remote_files)
		differences = differ.differences

		self.assertEqual(differences['new_files'], set(new_files))
		self.assertEqual(differences['deleted_files'], set(deleted_files))
		self.assertEqual(differences['maybe_modified_files'], set(maybe_modified_files))

	def test_new_files(self):
		self._test([1, 2, 3], [], [1, 2, 3], [], [])

	def test_only_remote(self):
		self._test([], [1, 2, 3], [], [1, 2, 3], [])

	def test_modified(self):
		self._test([1, 2, 3], [1, 2, 3], [], [], [(1, 1), (2, 2), (3, 3)])

	def test_mixed(self):
		self._test([1, 2, 3], [2, 3, 4], [1], [4], [(2, 2), (3, 3)])


class TestLastModifiedDiffer(unittest.TestCase):
	def test_local_newer(self):
		differ = LastModifiedDiffer(200, 100)

		self.assertTrue(differ.local_is_modified)

	def test_local_older(self):
		differ = LastModifiedDiffer(100, 200)

		self.assertFalse(differ.local_is_modified)
	
class TestDifferRunner(unittest.TestCase):
	class FilesystemObject(object):
		def __init__(self, files):
			super(TestDifferRunner.FilesystemObject, self).__init__()

			self.files = files

	class DifferForDifferRunnerTest(object):
		def __init__(self, local, remote):
			super(TestDifferRunner.DifferForDifferRunnerTest, self).__init__()
			self.local = local
			self.remote = remote

		@property
		def local_is_modified(self):
			return self.local == 2 and self.remote == 2

	def setUp(self):
		self.local_filesystem = TestDifferRunner.FilesystemObject([1, 2, 3])
		self.remote_filesystem = TestDifferRunner.FilesystemObject([1, 2, 3])

	def test_simple(self):
		differrunner = DifferRunner(self.local_filesystem, self.remote_filesystem, [])

		self.assertEqual(differrunner.differences, {'new_files': set([]), 'deleted_files': set([]), 'modified_files': set([])})

	def test_differ(self):
		differrunner = DifferRunner(self.local_filesystem, self.remote_filesystem, [TestDifferRunner.DifferForDifferRunnerTest])

		self.assertEqual(differrunner.differences, {'new_files': set([]), 'deleted_files': set([]), 'modified_files': set([(2, 2)])})

class TestLocalFile(unittest.TestCase):
	def setUp(self):
		self.tempfile = tempfile.NamedTemporaryFile()

	def test_file_timestamp(self):
		lfile = LocalFile(self.tempfile.name)
		self.assertEqual(lfile.last_modified, datetime.fromtimestamp(os.path.getmtime(self.tempfile.name)))

class TestLocalFilesystem(unittest.TestCase):
	def setUp(self):
		self.tempdir = tempfile.mkdtemp()

		self.files = set([])
		for i in range(10):
			self.files.add(tempfile.mkstemp(dir=self.tempdir))

		# dir in dir? why not!
		tempfile.mkdtemp(dir=self.tempdir)

	def tearDown(self):
		import shutil
		shutil.rmtree(self.tempdir)

	def runTest(self):
		local_filesystem = LocalFilesystem(self.tempdir)
		files = set(list(local_filesystem.files))

		self.assertEqual(len(files), 10)
		for i in range(10):
			self.assertIsInstance(files.pop(), LocalFile)

class TestRemoteFile(unittest.TestCase):
	def runTest(self):
		file_data = {
			'uuid': 'test uuIDd',
			'path': 'share/test1.txt',
			'last_modified': 1403651231,
		}

		remote_file = RemoteFile(file_data)

		self.assertEqual(remote_file.last_modified, file_data['last_modified'])
		self.assertEqual(remote_file.uuid, file_data['uuid'])
		self.assertEqual(remote_file.path, file_data['path'])

class TestGlacierLocalDatabaseFile(unittest.TestCase):
	def _create_empty_db(self):
		self.dbfile = tempfile.NamedTemporaryFile()
		os.unlink(self.dbfile.name)
		
		self._read_database()
		self.localdatabase.write() # creates empty db file

		self.assertEqual(list(self.localdatabase.files), [])

	def _read_database(self):
		self.localdatabase = GlacierLocalDatabaseFile(self.dbfile.name)

	def _check_files_timestamps(self):
		# check dates on localfiles (should be datetime.now() but we add +- 5s tolerance as tests go...)
		for files_data in self.localdatabase.files:
			self.assertLess(files_data.uploaded_at, datetime.now()+timedelta(seconds=5))
			self.assertGreater(files_data.uploaded_at, datetime.now()-timedelta(seconds=5))

	def _test_if_db_files_is(self, data):
		self._check_files_timestamps()		
		self.assertEqual(list(self.localdatabase.files), data)

		self._read_database()

		self._check_files_timestamps()
		self.assertEqual(list(self.localdatabase.files), data)		

	def _test_if_db_pending_jobs_is(self, data):
		self.assertEqual(set(self.localdatabase.pending_jobs), set(data))
		self._read_database()
		self.assertEqual(set(self.localdatabase.pending_jobs), set(data))

	def test_empty(self):
		self._create_empty_db()
		self._test_if_db_files_is([])

	def _add_two_files(self):
		last_modified_date = datetime.utcfromtimestamp(1403701810)
		fileobj1 = Struct(path='share/1.txt', last_modified=last_modified_date)
		self.localdatabase.add_file(fileobj1, '1234567')

		fileobj2 = Struct(path='share/2.txt', last_modified=last_modified_date)
		self.localdatabase.add_file(fileobj2, '2234567')

		return (fileobj1, fileobj2)

	def test_add_file(self):
		self._create_empty_db()

		fileobj1, fileobj2 = self._add_two_files()

		self._test_if_db_files_is([fileobj1, fileobj2])

	def test_delete_file(self):
		self._create_empty_db()

		fileobj1, fileobj2 = self._add_two_files()

		fileobj = Struct(uuid='1234567')
		self.localdatabase.delete_file(fileobj)

		self._test_if_db_files_is([fileobj2])

		fileobj2 = Struct(uuid='2234567')
		self.localdatabase.delete_file(fileobj2)

		self._test_if_db_files_is([])

	def _add_two_jobs(self):
		job1 = PendingJob('12345')
		self.localdatabase.add_pending_job(job1)

		job2 = PendingJob('123456')
		self.localdatabase.add_pending_job(job2)

		return (job1, job2)
		
	def test_add_job(self):
		self._create_empty_db()

		job1, job2 = self._add_two_jobs()

		self._test_if_db_pending_jobs_is([job1, job2])

	def test_delete_job(self):
		self._create_empty_db()

		job1, job2 = self._add_two_jobs()

		self._test_if_db_pending_jobs_is([job1, job2])

		self.localdatabase.delete_pending_job(job1)
		self._test_if_db_pending_jobs_is([job2])

		self.localdatabase.delete_pending_job(job2)
		self._test_if_db_pending_jobs_is([])

	def test_and_restore_evil_job(self):
		''' Try to make GlacierLocalDatabaseFile instance arbitary class (Struct) '''
		self._create_empty_db()

		eviljob = Struct(uuid='evil')
		self.localdatabase.add_pending_job(eviljob);

		self._read_database()

		# when requesting .pending_jobs it should raise InvalidJobTypeException
		with self.assertRaises(InvalidJobTypeException):
				tmp = set(self.localdatabase.pending_jobs)

if __name__ == '__main__':
	unittest.main()