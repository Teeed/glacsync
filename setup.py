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

from distutils.core import setup

setup(
	name='GlacSync',
	version='0.1.0',
	author='Tadeusz Magura-Witkowski',
	author_email='teeed@na1noc.pl',
	packages=['glacsync', 'glacsync.test'],
	scripts=['bin/glacsync'],
	url='https://github.com/Teeed/glacsync',
	license='LICENSE',
	description='Application that sync folders to Amazon Glacier.',
	long_description=open('README.md').read(),
	install_requires=[
		'boto >= 2.27.0',
		'configparser'
	],
)
