"""Expose only a bounded numeric retry delay, never a raw upstream header."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import math
import re


def sanitized_retry_after(value):
    if isinstance(value,str) and re.fullmatch(r'[0-9]{1,9}',value):
        return str(min(int(value),31536000))
    try:
        when=parsedate_to_datetime(value)
        if when.tzinfo is None:when=when.replace(tzinfo=timezone.utc)
        seconds=math.ceil((when-datetime.now(timezone.utc)).total_seconds())
        return str(min(31536000,max(0,seconds)))
    except (TypeError,ValueError,OverflowError):
        return '60'
