class PropertyAlreadyExistsError(Exception):
    """Error for duplicate properties on the same model."""
    def __init__(self, label, prop):
        """Init the error.

        :param label: Name of the model
        :type label: str
        :param prop: Name of the property
        :type prop: str
        """
        msg = (
            'Cannot create property {} as it already exists on model {}'
            .format(prop, label)
        )
        super(PropertyAlreadyExistsError, self).__init__(msg)


class InvalidCollectionError(Exception):
    """Error for a directory in the data directory that isn't a run."""
    def __init__(self, path):
        """Init the error.

        :param path: Path of invalid directory
        :type path: str
        """
        msg = 'Directory {} is not a valid run.'.format(path)
        super(InvalidCollectionError, self).__init__(msg)
