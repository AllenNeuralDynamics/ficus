class ConfigNotFoundError(Exception):
    pass


class ConfigExistsError(Exception):
    pass


class ConfigSerializeError(Exception):
    pass


class ConfigDecodeError(Exception):
    pass


class UnsupportedFileTypeError(Exception):
    pass


class PathNotFoundError(Exception):
    pass

class PathIsDirectoryError(Exception):
    pass

class InvalidScopeError(Exception):
    pass

class InvalidScopeIdentifierError(Exception):
    pass

class InvalidNamespaceError(Exception):
    pass

class MultipleScopeIdentifiersError(Exception):
    pass

class NotEmptyError(Exception):
    pass

class BadVersionError(Exception):
    pass
