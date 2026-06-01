"""
从当前数据库生成数据质量报告（Book-Crossing 导入后的清洗统计）
运行: python data/cleaning/clean_books.py
"""
import os
import sys
from pathlib import Path

import django
import pandas as pd

ROOT = Path(__file__).resolve().parents[2] / 'backend'
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'booktrade.settings')
django.setup()

from accounts.models import User  # noqa: E402
from analytics.models import BehaviorLog  # noqa: E402
from catalog.models import BookBase  # noqa: E402
from marketplace.models import SellBook  # noqa: E402
from trade.models import OrderInfo  # noqa: E402

REPORT = Path(__file__).resolve().parents[2] / 'docs' / 'reports' / '数据清洗报告.md'


def build_report() -> str:
    books = list(BookBase.objects.values(
        'isbn', 'book_name', 'author', 'pub_year', 'original_price', 'category_id',
    ))
    if not books:
        return '# JBOOK 数据清洗报告\n\n> 数据库暂无图书，请先运行 `manage.py seed_demo --force`。\n'

    df = pd.DataFrame(books)
    logs = [
        f'- 图书总数: {len(df)}',
        f'- ISBN 唯一: {df["isbn"].nunique()}',
        f'- 缺作者: {(df["author"] == "").sum()} 条',
        f'- 出版年异常 (<1900 或 >2026): {((df["pub_year"] < 1900) | (df["pub_year"] > 2026)).sum()} 条',
    ]

    price = pd.to_numeric(df['original_price'], errors='coerce')
    logs.append(f'- 原价区间: {price.min():.2f} ~ {price.max():.2f} 元，均值 {price.mean():.2f}')

    sells = SellBook.objects.count()
    users = User.objects.count()
    orders = OrderInfo.objects.count()
    behaviors = BehaviorLog.objects.count()

    body = '# JBOOK 数据清洗报告\n\n'
    body += '数据来源: [Book-Crossing](https://grouplens.org/datasets/book-crossing/) 子集，经 `seed_demo` 清洗入库。\n\n'
    body += '## 质量检查\n' + '\n'.join(logs) + '\n\n'
    body += '## 描述性统计（原价）\n```\n' + price.describe().to_string() + '\n```\n\n'
    body += '## 平台快照\n'
    body += f'- 在售商品: {SellBook.objects.filter(status=SellBook.STATUS_ON).count()}\n'
    body += f'- 用户: {users} · 订单: {orders} · 行为日志: {behaviors}\n'
    body += f'- 总上架记录: {sells}\n'
    return body


def main():
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    report = build_report()
    REPORT.write_text(report, encoding='utf-8')
    print(report)
    print(f'报告已保存: {REPORT}')


if __name__ == '__main__':
    main()
