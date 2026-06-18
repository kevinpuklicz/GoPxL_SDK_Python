"""Enumerations mirroring the C++ SDK."""

from enum import IntEnum


class GoStatus(IntEnum):
    ERROR_STATE = -1000
    ERROR_NOT_FOUND = -999
    ERROR_COMMAND = -998
    ERROR_PARAMETER = -997
    ERROR_UNIMPLEMENTED = -996
    ERROR_MEMORY = -994
    ERROR_TIMEOUT = -993
    ERROR_INCOMPLETE = -992
    ERROR_STREAM = -991
    ERROR_CLOSED = -990
    ERROR = 0
    OK = 1


class GoRequestMethod(IntEnum):
    CREATE = 0
    READ = 1
    UPDATE = 2
    DELETE = 3
    CALL = 4
    SUB = 5
    UNSUB = 6
    START_STREAM = 7
    STOP_STREAM = 8

    def wire_name(self) -> str:
        names = {
            GoRequestMethod.CREATE: "create",
            GoRequestMethod.READ: "read",
            GoRequestMethod.UPDATE: "update",
            GoRequestMethod.DELETE: "delete",
            GoRequestMethod.CALL: "call",
            GoRequestMethod.SUB: "sub",
            GoRequestMethod.UNSUB: "unsub",
            GoRequestMethod.START_STREAM: "stream",
            GoRequestMethod.STOP_STREAM: "cancelStream",
        }
        return names[self]


class GoResponseType(IntEnum):
    REQUEST = 0
    NOTIFICATION = 1
    STREAM = 2


class GoNotificationType(IntEnum):
    CREATED = 0
    DELETED = 1
    UPDATED = 2
    EMBEDDED_UPDATED = 3


class GoSystemState(IntEnum):
    READY = 0
    RUNNING = 1
    CONFLICT = 2


class MessageType(IntEnum):
    SIGNAL = 1
    NULL_TYPE = 10
    STAMP = 11
    UNIFORM_PROFILE = 12
    PROFILE_POINT_CLOUD = 13
    UNIFORM_SURFACE = 14
    SURFACE_POINT_CLOUD = 15
    IMAGE = 16
    SPOTS = 17
    MESH = 18
    MEASUREMENT = 19
    STRING = 20
    RENDERING = 70
    POINT_FEATURE = 71
    LINE_FEATURE = 72
    PLANE_FEATURE = 73
    CIRCLE_FEATURE = 74
    HEALTH = 100
