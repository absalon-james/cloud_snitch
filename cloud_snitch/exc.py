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


class RunInvalidError(Exception):
    """Error for a directory in the data directory that isn't a run."""
    def __init__(self, path):
        """Init the error.

        :param path: Path of invalid directory
        :type path: str
        """
        msg = 'Directory {} is not a valid run.'.format(path)
        super(RunInvalidError, self).__init__(msg)


class RunAlreadySyncedError(Exception):
    """Error for a run that is already synced."""
    def __init__(self, run):
        """Init the error.

        :param run: Run instance
        :type run: cloud_snitch.runs.Run
        """
        msg = 'Run at path {} is already synced.'.format(run.path)
        super(RunAlreadySyncedError, self).__init__(msg)


class RunInvalidStatusError(Exception):
    """Error for trying to slurp a run that is not in finished status."""
    def __init__(self, run):
        """Init the error.

        :param run: Run instance
        :type run: cloud_snitch.runs.Run
        """
        msg = 'Run at path {} is in {} status'.format(run.path, run.status)
        super(RunInvalidStatusError, self).__init__(msg)
