from catalog.models import Category


def site_context(request):
    return {
        'SITE_NAME': 'JBOOK',
        'user_obj': getattr(request, 'custom_user', None),
        'nav_categories': Category.objects.filter(parent__isnull=True)[:12],
    }
