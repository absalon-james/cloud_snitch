class InvalidLabelError(Exception):
    def __init__(self, label):
        """Init the error.

        :param label: Label
        :type label: str
        """
        msg = 'Invalid label \'{}\'.'.format(label)
        super(InvalidLabelError, self).__init__(msg)


class InvalidPropertyError(Exception):
    def __init__(self, label, prop):
        """Init the error.

        :param label: Label
        :type label: str
        :param prop: Property name
        :type prop: str
        """
        msg = 'Invalid property \'{}\' on \'{}\''.format(label, prop)
        super(InvalidPropertyError, self).__init__(msg)


class JobRunningError(Exception):
    """Error for asynchronous task still running."""
    def __init__(self):
        super(JobRunningError, self).__init__('Job is still running.')


class JobError(Exception):
    """Error for asychronous task failed."""
    def __init__(self):
        super(JobError, self).__init__('Job failed.')
