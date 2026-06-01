"""
机器学习模型训练脚本
- 价格预测（线性回归 + 随机森林）
- 热度三分类（逻辑回归 + KNN + 随机森林）
运行: python manage.py shell < 或直接 python mlapp/train_models.py (需配置 DJANGO_SETTINGS_MODULE)
"""
import os
import sys
from pathlib import Path

import django

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'booktrade.settings')
django.setup()

import joblib
import numpy as np
import pandas as pd
from django.conf import settings
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler

from marketplace.models import SellBook
from trade.models import OrderInfo

MODEL_DIR = settings.ML_MODEL_DIR
MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = settings.REPORTS_DIR / '机器学习模型报告.md'


def build_price_dataset():
    rows = []
    for s in SellBook.objects.select_related('book').all():
        from django.db.models import Avg
        avg_price = SellBook.objects.filter(book__category=s.book.category).aggregate(
            a=Avg('second_price')
        )['a'] or float(s.book.original_price or 0) * 0.5
        rows.append({
            'original_price': float(s.book.original_price or 0),
            'pub_year': s.book.pub_year or 2020,
            'cat_id': s.book.category_id,
            'quality': s.quality,
            'category_avg': float(avg_price),
            'target': float(s.second_price),
        })
    return pd.DataFrame(rows)


def build_hot_dataset():
    rows = []
    for s in SellBook.objects.all():
        orders = s.orders.filter(order_status=OrderInfo.STATUS_DONE).count()
        conv = orders / max(s.view_count, 1)
        if orders >= 2 or s.view_count >= 80:
            label = 2
        elif s.view_count < 8 and orders == 0:
            label = 0
        else:
            label = 1
        rows.append({
            'view_count': s.view_count,
            'collect_count': s.collect_count,
            'consult_count': s.consult_count,
            'orders': orders,
            'conversion': conv,
            'label': label,
        })
    return pd.DataFrame(rows)


def train_price_model(df):
    if len(df) < 10:
        df = pd.DataFrame([
            {'original_price': 80, 'pub_year': 2020, 'cat_id': 1, 'quality': 4, 'category_avg': 40, 'target': 45},
            {'original_price': 120, 'pub_year': 2015, 'cat_id': 2, 'quality': 3, 'category_avg': 55, 'target': 50},
            {'original_price': 50, 'pub_year': 2018, 'cat_id': 1, 'quality': 5, 'category_avg': 30, 'target': 35},
        ] * 20)
    features = ['original_price', 'pub_year', 'cat_id', 'quality', 'category_avg']
    X = df[features]
    y = df['target']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    models = {
        'linear_regression': LinearRegression(),
        'random_forest': RandomForestRegressor(n_estimators=100, random_state=42),
    }
    report_lines = ['## 价格预测模型\n']
    best_model = None
    best_mae = 1e9
    best_name = ''
    all_metrics = {}

    for name, model in models.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, pred)
        mse = mean_squared_error(y_test, pred)
        r2 = r2_score(y_test, pred)
        all_metrics[name] = {'mae': round(float(mae), 4), 'mse': round(float(mse), 4), 'r2': round(float(r2), 4)}
        report_lines.append(f'### {name}\n- MAE: {mae:.4f}\n- MSE: {mse:.4f}\n- R²: {r2:.4f}\n')
        if mae < best_mae:
            best_mae = mae
            best_model = model
            best_name = name

    joblib.dump({'model': best_model, 'feature_cols': features, 'name': best_name}, MODEL_DIR / 'price_model.joblib')
    report_lines.append(f'**选用模型**: {best_name}\n')
    meta = {
        'selected': best_name,
        'metrics': all_metrics,
        'best': all_metrics.get(best_name, {}),
        'sample_size': len(df),
    }
    return '\n'.join(report_lines), meta


def train_hot_model(df):
    if len(df) < 10:
        df = pd.DataFrame({
            'view_count': np.random.randint(0, 100, 60),
            'collect_count': np.random.randint(0, 20, 60),
            'consult_count': np.random.randint(0, 15, 60),
            'orders': np.random.randint(0, 5, 60),
            'conversion': np.random.rand(60) * 0.1,
            'label': np.random.choice([0, 1, 2], 60),
        })
    features = ['view_count', 'collect_count', 'consult_count', 'orders', 'conversion']
    X = df[features]
    y = df['label']
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    models = {
        'logistic_regression': LogisticRegression(max_iter=500),
        'knn': KNeighborsClassifier(n_neighbors=5),
        'random_forest': RandomForestClassifier(n_estimators=100, random_state=42),
    }
    report_lines = ['## 热度分类模型\n']
    best_model = None
    best_f1 = -1
    best_name = ''
    all_metrics = {}

    for name, model in models.items():
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        acc = accuracy_score(y_test, pred)
        f1 = f1_score(y_test, pred, average='weighted')
        all_metrics[name] = {'accuracy': round(float(acc), 4), 'f1': round(float(f1), 4)}
        report_lines.append(f'### {name}\n- 准确率: {acc:.4f}\n- F1: {f1:.4f}\n')
        report_lines.append('```\n' + classification_report(y_test, pred) + '\n```\n')
        if f1 > best_f1:
            best_f1 = f1
            best_model = model
            best_name = name

    joblib.dump({
        'model': best_model,
        'scaler': scaler,
        'feature_cols': features,
        'name': best_name,
    }, MODEL_DIR / 'hot_model.joblib')
    report_lines.append(f'**选用模型**: {best_name}\n')
    meta = {
        'selected': best_name,
        'metrics': all_metrics,
        'best': all_metrics.get(best_name, {}),
        'sample_size': len(df),
    }
    return '\n'.join(report_lines), meta


def update_hot_flags():
    from mlapp.services import predict_hot_label
    for s in SellBook.objects.filter(status=SellBook.STATUS_ON):
        label = predict_hot_label(s)
        s.is_hot = label == '热门'
        s.save(update_fields=['is_hot'])


def _save_model_meta(price_meta, hot_meta):
    import json
    from django.utils import timezone

    meta_path = MODEL_DIR / 'model_meta.json'
    history_path = MODEL_DIR / 'model_history.json'
    now = timezone.now().strftime('%Y-%m-%d %H:%M')
    overall = 0
    if price_meta.get('best', {}).get('r2') is not None:
        overall += price_meta['best']['r2'] * 50
    if hot_meta.get('best', {}).get('accuracy') is not None:
        overall += hot_meta['best']['accuracy'] * 50

    meta = {
        'version': '1.0.0',
        'trained_at': now,
        'price': price_meta,
        'hot': hot_meta,
        'hyperparams': {
            'price': {'test_size': 0.2, 'random_state': 42, 'models': list(price_meta.get('metrics', {}))},
            'hot': {'test_size': 0.2, 'max_iter': 500, 'n_neighbors': 5, 'models': list(hot_meta.get('metrics', {}))},
        },
        'training_log': [
            f'[{now}] 价格模型选用 {price_meta.get("selected")}，样本 {price_meta.get("sample_size")} 条',
            f'[{now}] 热度模型选用 {hot_meta.get("selected")}，样本 {hot_meta.get("sample_size")} 条',
        ],
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')

    history = []
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            history = []
    history.append({
        'time': now,
        'overall_score': round(overall),
        'price_mae': price_meta.get('best', {}).get('mae'),
        'price_r2': price_meta.get('best', {}).get('r2'),
        'hot_accuracy': hot_meta.get('best', {}).get('accuracy'),
        'price_model': price_meta.get('selected'),
        'hot_model': hot_meta.get('selected'),
    })
    history_path.write_text(json.dumps(history[-20:], ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    price_df = build_price_dataset()
    hot_df = build_hot_dataset()
    report = '# JBOOK 模型评估报告\n\n'
    price_report, price_meta = train_price_model(price_df)
    hot_report, hot_meta = train_hot_model(hot_df)
    report += price_report + hot_report
    REPORT_PATH.write_text(report, encoding='utf-8')
    _save_model_meta(price_meta, hot_meta)
    update_hot_flags()
    print(f'模型已保存至 {MODEL_DIR}')
    print(f'报告已写入 {REPORT_PATH}')


if __name__ == '__main__':
    main()
