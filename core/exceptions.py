from django.http import JsonResponse


def ratelimit_handler(request, exception):
    """Возвращает JSON 429 вместо стандартной страницы 403 при превышении лимита."""
    return JsonResponse(
        {"detail": "Слишком много запросов. Попробуйте позже."},
        status=429,
    )