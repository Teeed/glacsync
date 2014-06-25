from json import JSONEncoder


# allows class which implements to_JSON method to be serializable
def _default(self, obj):
	return getattr(obj.__class__, "to_JSON", _default.default)(obj)

_default.default = JSONEncoder().default
JSONEncoder.default = _default
