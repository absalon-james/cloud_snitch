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
