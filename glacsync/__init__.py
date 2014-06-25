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

from json import JSONEncoder

# allows class which implements to_JSON method to be serializable
def _default(self, obj):
	return getattr(obj.__class__, "to_JSON", _default.default)(obj)

_default.default = JSONEncoder().default
JSONEncoder.default = _default
