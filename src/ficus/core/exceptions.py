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


class PathIsDirectoryError(Exception):
    pass
