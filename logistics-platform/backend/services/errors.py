class ApiError(Exception):
    def __init__(self, message, status=400, code="BAD_REQUEST", **extra):
        super().__init__(message)
        self.message, self.status, self.code, self.extra = message, status, code, extra

    def to_dict(self):
        return {"error": self.message, "code": self.code, **self.extra}
