import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from mlapp.services import predict_price
from marketplace.services import isbn_lookup, search_suggestions


@require_GET
def api_search_suggest(request):
    q = request.GET.get('q', '')
    return JsonResponse({'items': search_suggestions(q)})


@require_GET
def api_isbn_lookup(request):
    isbn = request.GET.get('isbn', '').strip()
    if not isbn:
        return JsonResponse({'success': False, 'message': 'ISBN required'}, status=400)
    data = isbn_lookup(isbn)
    if not data:
        return JsonResponse({'success': False, 'message': '未找到该ISBN，请手动填写'})
    return JsonResponse({'success': True, 'data': data})


@require_GET
def api_suggest_price(request):
    try:
        original = float(request.GET.get('original_price', 50))
        price = predict_price({
            'original_price': original,
            'pub_year': int(request.GET.get('pub_year', 2020)),
            'cat_id': int(request.GET.get('cat_id', 1)),
            'quality': int(request.GET.get('quality', 3)),
        })
        low = round(price * 0.9, 2)
        high = round(price * 1.1, 2)
        return JsonResponse({
            'success': True,
            'suggested_price': price,
            'range': [low, high],
            'hint': f'AI reference: {low} - {high} yuan (mid {price})',
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
