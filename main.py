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

from configparser import ConfigParser
import argparse
import json

from glacsync import GlacierSync

AUTO_VALUE = '<auto>'

def main():
	parser = argparse.ArgumentParser(description='Synchronizes local dir with amazon glacier')
	parser.add_argument('action', nargs=1, choices=('sync', 'restore', 'restoredb'), default='sync', help='File with job definitions')
	parser.add_argument('config_file', nargs=1, help='File with job definitions')

	args = parser.parse_args()

	config = ConfigParser()
	config.read(args.config_file)

	db_file = config.get('General', 'db_file') if config.get('General', 'db_file') != AUTO_VALUE else '%s.files' % args.config_file[0]
	
	final_config = {
		'aws': {
			'secret_key': config.get('AWS_Access', 'secret_key'),
			'access_key': config.get('AWS_Access', 'access_key'),
			'region': config.get('AWS_Settings', 'region'),
			'vault_name': config.get('AWS_Settings', 'vault_name'),
		},
		'database': db_file,
		'delayed_delete': config.getboolean('General', 'use_delayed_delete'),
		'dirs_to_sync': json.loads(config.get('General', 'dirs_to_sync')),
	}

	glacier_sync = GlacierSync(**final_config)
	glacier_sync.sync(quiet=False)

if __name__ == '__main__':
	main()
