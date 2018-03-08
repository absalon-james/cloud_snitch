import datetime
import pytz

epoch = datetime.datetime.utcfromtimestamp(0)
epoch = epoch.replace(tzinfo=pytz.UTC)

EOT = 9223372036854775807


def utcdatetimenow():
    """Get utc now as datetime.

    :returns: Now as a utc datetime object
    :rtype: datetime.datetime
    """
    dt = datetime.datetime.utcnow()
    dt = dt.replace(tzinfo=pytz.UTC)
    return dt


def milliseconds(dt):
    """Convert datetime object to milliseconds since epoch

    :param dt: Datetime object
    :type dt: datetime.datetime
    :returns: Converted datetime
    :rtype: int
    """
    return int((dt - epoch).total_seconds() * 1000)


def milliseconds_now():
    """Get utc milliseconds of now

    :returns: Number of utc milliseconds since epoch
    :rtype: int
    """
    return milliseconds(utcdatetimenow())


def utcdatetime(milliseconds):
    """Convert milliseconds to UTC datetime.

    :param milliseconds: Milliseconds since epoch
    :type milliseconds: int
    :returns: Converted timestamp
    :rtype: datetime.datetime.
    """
    dt = datetime.datetime.fromtimestamp(milliseconds / 1e3, pytz.UTC)
    return dt


def strtodatetime(isostr):
    """Convert a utc isoformat datetime string into a datetime obj.

    :param isostr: Isoformatted datetime str
    :type isostr: str
    :returns: Converted datetime object
    :rtype datetime.datetime
    """
    left, dot, fraction = isostr.partition('.')
    dt = datetime.datetime.strptime(left, "%Y-%m-%dT%H:%M:%S")
    dt = dt.replace(tzinfo=pytz.UTC)
    return dt


def complex_get(complexkey, data, default=None, keydelimiter=':'):
    """Get a value from a dict via a complex key.

    A complex key is a key where a delimiter within the key
    indicates a path through a nested dict structure.

    :param complexkey: Complex key to find a value for.
    :type complexkey: str
    :param data: Data to search
    :type data: dict
    :param keydelimiter: Delimiter to indicate a path
    :type keydelimiter: str
    :returns: Returns the value if it exists or default otherwise.
    :rtype: object|type(default)
    """
    keys = complexkey.split(keydelimiter)
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data
