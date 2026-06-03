# -*- coding: utf-8 -*-
"""从 PostgreSQL 中的 BX 原始表 (book/users/ratings) 同步到 Django 业务表。"""
from __future__ import annotations

from decimal import Decimal

import pandas as pd
from django.db import connection

from marketplace.data.book_crossing import (
    BookCrossingImporter,
    _estimate_price,
    _infer_category,
    _norm_isbn,
)


def bx_pg_tables_ready() -> bool:
    """检测当前数据库是否已有 load_bx.py 写入的 BX 表且含数据。"""
    if connection.vendor != 'postgresql':
        return False
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'book'
            )
            """
        )
        if not cur.fetchone()[0]:
            return False
        cur.execute('SELECT COUNT(*) FROM book')
        return cur.fetchone()[0] > 0


class PgBookCrossingImporter(BookCrossingImporter):
    """复用 BookCrossingImporter 入库逻辑，数据源改为 PostgreSQL BX 表。"""

    def run(self):
        from accounts.models import User
        from analytics.models import BehaviorLog, CrawlerLog
        from catalog.models import BookBase, Category
        from marketplace.models import BrowseHistory, Collect, SellBook
        from trade.models import OrderInfo

        self.log('数据源: PostgreSQL 表 book / users / ratings')
        books_df = self._load_books_frame()
        ratings_df = self._load_ratings_frame(books_df)
        users_df = self._load_users_frame()
        active_uids = set(ratings_df['bx_uid'].unique()) if not ratings_df.empty else set()
        users_df = users_df[users_df['bx_uid'].isin(active_uids)]

        cat_map = self._create_categories(Category)
        self._create_demo_users(User)
        self._import_bx_users(users_df, User)
        self._import_books(books_df, cat_map, BookBase)
        self._import_sells(SellBook, User)
        self._import_ratings_as_activity(
            ratings_df, User, SellBook, BehaviorLog, Collect, BrowseHistory, OrderInfo,
        )

        CrawlerLog.objects.create(
            status=CrawlerLog.STATUS_OK,
            message=(
                f'PG BX sync: {self.stats.books} books, {self.stats.ratings_used} ratings'
            ),
            records_count=self.stats.books,
        )
        return self.stats

    def _load_books_frame(self) -> pd.DataFrame:
        sql = """
            WITH top_isbn AS (
                SELECT isbn FROM ratings
                GROUP BY isbn ORDER BY COUNT(*) DESC LIMIT %(limit)s
            )
            SELECT b.isbn, b.booktitle, b.bookauthor, b.yearofpublication, b.publisher
            FROM book b
            INNER JOIN top_isbn t ON b.isbn = t.isbn
        """
        df = pd.read_sql(sql, connection, params={'limit': self.max_books})
        df = df.rename(columns={
            'booktitle': 'title',
            'bookauthor': 'author',
            'yearofpublication': 'year',
        })
        df['isbn'] = df['isbn'].map(_norm_isbn)
        df = df.dropna(subset=['isbn', 'title'])
        df['title'] = df['title'].astype(str).str.strip().str.slice(0, 200)
        df['author'] = df['author'].fillna('Unknown').astype(str).str.strip().str.slice(0, 128)
        df['publisher'] = df.get('publisher', pd.Series([''] * len(df))).fillna('').astype(str).str.slice(0, 128)
        df['year'] = pd.to_numeric(df.get('year', 0), errors='coerce').fillna(2000).astype(int)
        df.loc[(df['year'] < 1900) | (df['year'] > 2026), 'year'] = 2000
        df['cat_name'] = df.apply(lambda r: _infer_category(r['title'], r['author']), axis=1)
        df['original_price'] = df['year'].map(lambda y: float(_estimate_price(int(y))))
        return df.drop_duplicates('isbn').head(self.max_books)

    def _load_users_frame(self) -> pd.DataFrame:
        sql = """
            SELECT userid, location, age FROM users LIMIT %(limit)s
        """
        df = pd.read_sql(sql, connection, params={'limit': self.max_users * 3})
        df = df.rename(columns={'userid': 'bx_uid'})
        df['bx_uid'] = df['bx_uid'].astype(str).str.strip()
        df['age'] = pd.to_numeric(df['age'], errors='coerce')
        return df.drop_duplicates('bx_uid')

    def _load_ratings_frame(self, books_df: pd.DataFrame) -> pd.DataFrame:
        if books_df.empty:
            return pd.DataFrame()
        valid_isbn = set(books_df['isbn'])
        sql = """
            SELECT userid, isbn, bookrating FROM ratings LIMIT %(limit)s
        """
        df = pd.read_sql(sql, connection, params={'limit': self.max_ratings * 5})
        df = df[df['isbn'].map(_norm_isbn).isin(valid_isbn)]
        df = df.rename(columns={
            'userid': 'bx_uid',
            'bookrating': 'rating',
        })
        df['isbn'] = df['isbn'].map(_norm_isbn)
        df['bx_uid'] = df['bx_uid'].astype(str).str.strip()
        df['rating'] = pd.to_numeric(df['rating'], errors='coerce').fillna(0).astype(int)
        df = df.dropna(subset=['isbn', 'bx_uid'])
        active_users = df['bx_uid'].value_counts().head(self.max_users).index
        df = df[df['bx_uid'].isin(active_users)]
        return df.head(self.max_ratings)
