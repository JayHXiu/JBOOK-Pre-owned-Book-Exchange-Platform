"""ML 推理服务：价格预测、热度、推荐"""
from pathlib import Path

import joblib
import numpy as np
from django.conf import settings
from django.db.models import Avg

from analytics.models import BehaviorLog
from catalog.models import BookBase
from marketplace.models import Collect, SellBook
from trade.models import OrderInfo

MODEL_DIR = settings.ML_MODEL_DIR
PRICE_MODEL = MODEL_DIR / 'price_model.joblib'
HOT_MODEL = MODEL_DIR / 'hot_model.joblib'


def _fallback_price(features: dict) -> float:
    original = float(features.get('original_price', 50))
    quality = int(features.get('quality', 3))
    year = int(features.get('pub_year', 2020))
    age_factor = max(0.3, 1 - (2026 - year) * 0.03)
    quality_factor = 0.5 + quality * 0.1
    return round(original * 0.45 * age_factor * quality_factor, 2)


def predict_price(features: dict) -> float:
    if PRICE_MODEL.exists():
        bundle = joblib.load(PRICE_MODEL)
        model = bundle['model']
        cols = bundle['feature_cols']
        row = [[
            float(features.get('original_price', 0)),
            int(features.get('pub_year', 2020)),
            int(features.get('cat_id', 1)),
            int(features.get('quality', 3)),
            float(features.get('category_avg', features.get('original_price', 0) * 0.5)),
        ]]
        import pandas as pd
        X = pd.DataFrame(row, columns=cols)
        return round(float(model.predict(X)[0]), 2)
    return _fallback_price(features)


def predict_hot_label(sell: SellBook) -> str:
    if HOT_MODEL.exists():
        bundle = joblib.load(HOT_MODEL)
        model = bundle['model']
        scaler = bundle.get('scaler')
        cols = bundle['feature_cols']
        import pandas as pd
        orders = sell.orders.filter(order_status=OrderInfo.STATUS_DONE).count()
        conv = orders / max(sell.view_count, 1)
        row = [[sell.view_count, sell.collect_count, sell.consult_count, orders, conv]]
        X = pd.DataFrame(row, columns=cols)
        if scaler is not None:
            X = scaler.transform(X)
        label = int(model.predict(X)[0])
        return {0: '冷门', 1: '普通', 2: '热门'}.get(label, '普通')
    if sell.view_count > 50 or sell.collect_count > 10:
        return '热门'
    if sell.view_count < 5:
        return '冷门'
    return '普通'


def get_recommendations(user_id, limit=8, exclude_sell_id=None):
    """协同过滤 + 内容过滤混合推荐"""
    if not user_id:
        return list(SellBook.objects.filter(status=SellBook.STATUS_ON)[:limit])

    user_collects = list(Collect.objects.filter(user_id=user_id).values_list('sell_id', flat=True))
    user_views = list(
        BehaviorLog.objects.filter(user_id=user_id)
        .values_list('sell_id', flat=True)[:50]
    )
    interacted = set(user_collects + user_views)

    cf_candidates = []
    if user_collects:
        similar_users = (
            Collect.objects.filter(sell_id__in=user_collects)
            .exclude(user_id=user_id)
            .values_list('user_id', flat=True)
            .distinct()[:20]
        )
        cf_candidates = list(
            Collect.objects.filter(user_id__in=similar_users)
            .exclude(sell_id__in=interacted)
            .values_list('sell_id', flat=True)[:limit * 2]
        )

    content_candidates = []
    viewed_sells = SellBook.objects.filter(sell_id__in=interacted).select_related('book')
    cat_ids = viewed_sells.values_list('book__category_id', flat=True).distinct()
    if cat_ids:
        content_candidates = list(
            SellBook.objects.filter(
                status=SellBook.STATUS_ON,
                book__category_id__in=cat_ids,
            )
            .exclude(sell_id__in=interacted)
            .order_by('-view_count')
            .values_list('sell_id', flat=True)[:limit * 2]
        )

    ranked_ids = []
    for sid in cf_candidates + content_candidates:
        if sid not in ranked_ids and sid != exclude_sell_id:
            ranked_ids.append(sid)
        if len(ranked_ids) >= limit:
            break

    if not ranked_ids:
        qs = SellBook.objects.filter(status=SellBook.STATUS_ON).order_by('-is_hot', '-view_count')
        if exclude_sell_id:
            qs = qs.exclude(sell_id=exclude_sell_id)
        return list(qs[:limit])

    qs = SellBook.objects.filter(sell_id__in=ranked_ids).select_related('book', 'book__category', 'user')
    order_map = {sid: i for i, sid in enumerate(ranked_ids)}
    return sorted(qs, key=lambda s: order_map.get(s.sell_id, 999))
