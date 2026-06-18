"""Exception types mirroring GoPxLSdk errors."""


class GoPxLError(Exception):
    pass


class GoChannelError(GoPxLError):
    pass


class GoRequestError(GoPxLError):
    def __init__(self, message: str, response=None):
        super().__init__(message)
        self.response = response
        if response is not None:
            self.status = int(getattr(response, "status", 0))
            self.path = str(getattr(response, "path", ""))
        else:
            self.status = 0
            self.path = ""
