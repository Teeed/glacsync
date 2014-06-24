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

import unittest
from datetime import datetime, timedelta
from glacsync import *


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

class FilesystemObject(object):
	def __init__(self, files):
		super(FilesystemObject, self).__init__()

		self.files = files

class DifferForDifferRunnerTest(object):
	def __init__(self, local, remote):
		self.local = local
		self.remote = remote

	@property
	def local_is_modified(self):
		return self.local == 2 and self.remote == 2
	
class TestDifferRunner(unittest.TestCase):
	def setUp(self):
		self.local_filesystem = FilesystemObject([1, 2, 3])
		self.remote_filesystem = FilesystemObject([1, 2, 3])

	def test_simple(self):
		differrunner = DifferRunner(self.local_filesystem, self.remote_filesystem, [])

		self.assertEqual(differrunner.differences, {'new_files': set([]), 'deleted_files': set([]), 'modified_files': set([])})

	def test_differ(self):
		differrunner = DifferRunner(self.local_filesystem, self.remote_filesystem, [DifferForDifferRunnerTest])

		self.assertEqual(differrunner.differences, {'new_files': set([]), 'deleted_files': set([]), 'modified_files': set([(2, 2)])})

class TestLocalFile(unittest.TestCase):
	def setUp(self):
		import tempfile
		self.tempfile = tempfile.NamedTemporaryFile()


	def test_file_timestamp(self):
		lfile = LocalFile(self.tempfile.name)
		self.assertEqual(lfile.last_modified, datetime.fromtimestamp(os.path.getmtime(self.tempfile.name)))

class TestLocalFilesystem(unittest.TestCase):
	def setUp(self):
		import tempfile
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

		self.assertEqual(remote_file.last_modified, datetime.utcfromtimestamp(file_data['last_modified']))
		self.assertEqual(remote_file.uuid, file_data['uuid'])
		self.assertEqual(remote_file.path, file_data['path'])


if __name__ == '__main__':
	unittest.main()