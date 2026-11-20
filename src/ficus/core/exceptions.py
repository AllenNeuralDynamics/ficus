class ConfigNotFoundError(Exception):
    pass


class ConfigExistsError(Exception):
    pass


class ConfigSerializeError(Exception):
    pass


class ConfigDecodeError(Exception):
    pass

class ConfigMutatedError(Exception):
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

# class NotEmptyError(Exception):
#     pass

class BadVersionError(Exception):
    pass

class StoreUnavailableError(Exception):
    """The data store can't be reached right now; the API answers 503."""
