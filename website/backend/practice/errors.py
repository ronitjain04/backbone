"""Shared persistence errors without Store/ClassroomStore circular imports."""
class Unauthorized(Exception):
    pass

class Conflict(Exception):
    pass

class RateLimited(Exception):
    pass
