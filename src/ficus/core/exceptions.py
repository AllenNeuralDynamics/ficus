################################################################################
#
#   GET
#
################################################################################


class ConfigNotFoundError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

    def __str__(self):
        return self.message


# ConfigNotFoundError (message is where the error occurred)
# class ConfigNotFoundError(Exception):
#     def __init__(self, hostname: str, namespace: str, filename: str, reason: str):
#         self.hostname = hostname
#         self.namespace = namespace
#         self.filename = filename
#         self.reason = reason
#         super().__init__(reason)

# NOTE: difference between single ConfigNotFoundError vs multiple like InvalidNamespace,InvalidHostname,InvalidFilename.
#   - if validating input (invalid input value would be 400 error)
#   - if config not found in zk (config not found would be 404 error)
#   - Since in the get we aren't validating if input is right or not, group together and do a single 404 handle

################################################################################
#
#   POST/SAVE
#   PUT/REPLACE
#   PATCH/UPDATE
#
################################################################################

# ConfigAlreadyExistsError
# ConfigNotFoundError (already from get)
# DefaultConfigAlreadyExistsError
# UnsupportedFileTypeError

# ConfigDecodingError
# ConfigSerializationError

################################################################################
#
#   DELETE
#
################################################################################

# PathNotEmptyError (if trying to delete a path that still has files in it, or delete a file that doesn't exist)

# Move zookeeper connection error  to here
