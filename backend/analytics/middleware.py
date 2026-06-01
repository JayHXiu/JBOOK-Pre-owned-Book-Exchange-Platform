class BehaviorLogMiddleware:
    """记录页面点击行为（简化版）"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response
