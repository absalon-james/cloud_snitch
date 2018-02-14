import datetime
import pytz

epoch = datetime.datetime.utcfromtimestamp(0)

EOT = 9223372036854775807


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
    return milliseconds(datetime.datetime.utcnow())


def utcdatetime(milliseconds):
    """Convert milliseconds to UTC datetime.

    :param milliseconds: Milliseconds since epoch
    :type milliseconds: int
    :returns: Converted timestamp
    :rtype: datetime.datetime.
    """
    dt = datetime.datetime.fromtimestamp(milliseconds / 1e3, pytz.UTC)
    return dt
