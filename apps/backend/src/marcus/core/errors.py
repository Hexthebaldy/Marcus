"""业务代码报告失败；HTTP 响应由 main.py 中的异常处理函数生成。"""


class ServiceError(Exception):
    """保存失败原因，供接口或后台任务决定如何向调用方报告。"""

    def __init__(self, status_code: int, code: str, message: str | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message or code
        self.detail = {"code": self.code, "message": self.message, "details": {}}
        super().__init__(self.message)
