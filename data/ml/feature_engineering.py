"""
描述性统计与特征工程 - Pandas/NumPy
输出 JBOOK 平台统计报告
"""
import os
import sys
from pathlib import Path

import django
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2] / 'backend'
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'booktrade.settings')
django.setup()

from marketplace.models import SellBook  # noqa: E402
from trade.models import OrderInfo  # noqa: E402

REPORT = Path(__file__).resolve().parents[2] / 'docs' / 'reports' / '平台运营数据分析报告.md'


def build_features():
    rows = []
    for s in SellBook.objects.select_related('book').filter(status=SellBook.STATUS_ON):
        days = max((pd.Timestamp.now(tz=None) - pd.Timestamp(s.create_time.replace(tzinfo=None))).days, 1)
        orders = s.orders.filter(order_status=OrderInfo.STATUS_DONE).count()
        rows.append({
            'sell_id': s.sell_id,
            'cat_id': s.book.category_id,
            'pub_year': s.book.pub_year or 2020,
            'original_price': float(s.book.original_price),
            'second_price': float(s.second_price),
            'quality': s.quality,
            'days_online': days,
            'view_count': s.view_count,
            'collect_count': s.collect_count,
            'consult_count': s.consult_count,
            'discount_rate': float(s.discount_rate),
            'exposure_per_day': s.view_count / days,
            'order_count': orders,
            'conversion': orders / max(s.view_count, 1),
        })
    return pd.DataFrame(rows)


def main():
    df = build_features()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    if df.empty:
        REPORT.write_text('# 暂无在售数据\n', encoding='utf-8')
        return

    stats = df[['second_price', 'view_count', 'discount_rate', 'conversion']].describe()
    train, test = np.split(df.sample(frac=1, random_state=42), [int(len(df) * 0.8)]) if len(df) > 5 else (df, df.head(0))

    report = '# JBOOK 平台运营报告\n\n'
    report += '## 基础统计\n```\n' + stats.to_string() + '\n```\n\n'
    report += f'- 在售样本数: {len(df)}\n'
    report += f'- 二手价均值: {df["second_price"].mean():.2f}  中位数: {df["second_price"].median():.2f}\n'
    report += f'- 成交转化率均值: {df["conversion"].mean():.4f}\n\n'
    report += '## 特征工程字段\n'
    report += '- 基础: 类目、出版年、原价、成色、上架天数\n'
    report += '- 行为: 浏览、收藏、咨询\n'
    report += '- 衍生: 折价率、单位时间曝光量\n\n'
    report += '## 数据分层与划分\n'
    by_cat = df.groupby('cat_id').size().to_dict()
    report += f'- 按类目分层: {by_cat}\n'
    report += f'- 训练集 {len(train)} / 测试集 {len(test)}\n\n'
    report += '## 业务建议\n'
    report += '1. 对高折价率+低浏览图书加强首页曝光\n'
    report += '2. 咨询高但转化低类目优化详情页与定价引导\n'
    report += '3. 结合智能定价降低卖家定价偏离\n'
    REPORT.write_text(report, encoding='utf-8')
    out = Path(__file__).parent / 'features.csv'
    df.to_csv(out, index=False, encoding='utf-8-sig')
    print(report)
    print(f'特征文件: {out}')


if __name__ == '__main__':
    main()
