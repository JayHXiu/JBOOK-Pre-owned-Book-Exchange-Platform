from django.http import JsonResponse
from django.urls import path

from mlapp.services import predict_price


def api_predict_price(request):
    try:
        price = predict_price({
            'original_price': float(request.GET.get('original_price', 50)),
            'pub_year': int(request.GET.get('pub_year', 2020)),
            'cat_id': int(request.GET.get('cat_id', 1)),
            'quality': int(request.GET.get('quality', 3)),
        })
        return JsonResponse({'success': True, 'price': price})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


urlpatterns = [
    path('predict-price/', api_predict_price, name='ml_predict_price'),
]
