# -*- coding: utf-8 -*-
"""Book-Crossing 数据集解析与 JBOOK 入库逻辑"""
from __future__ import annotations

import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = ROOT / 'data' / 'book_crossing' / 'raw'

BX_BOOKS = RAW_DIR / 'BX-Books.csv'
BX_USERS = RAW_DIR / 'BX-Users.csv'
BX_RATINGS = RAW_DIR / 'BX-Book-Ratings.csv'

BOOK_COLS = [
    'ISBN', 'Book-Title', 'Book-Author', 'Year-Of-Publication', 'Publisher',
    'Image-URL-S', 'Image-URL-M', 'Image-URL-L',
]
USER_COLS = ['User-ID', 'Location', 'Age']
RATING_COLS = ['User-ID', 'ISBN', 'Book-Rating']

CATEGORIES = [
    ('文学', None),
    ('计算机', None),
    ('经管', None),
    ('教材', None),
    ('科幻', '文学'),
    ('传记', '文学'),
    ('少儿', None),
    ('其他', None),
]

CATEGORY_RULES = [
    ('计算机', re.compile(r'computer|programming|software|java\b|python|algorithm|linux|web\b|database', re.I)),
    ('科幻', re.compile(r'science fiction|fantasy|star trek|star wars|dragon|magic\b|wizard', re.I)),
    ('经管', re.compile(r'business|management|finance|marketing|economics|leadership|invest', re.I)),
    ('教材', re.compile(r'textbook|introduction to|principles of|handbook of|guide to|study guide', re.I)),
    ('传记', re.compile(r'biograph|memoir|autobiograph', re.I)),
    ('少儿', re.compile(r'children|juvenile|kids|picture book', re.I)),
]

DEMO_USERS = [
    ('admin', 'admin123', '管理员', 1),
    ('seller1', '123456', '卖家小明', 0),
    ('seller2', '123456', '卖家阿杰', 0),
    ('buyer1', '123456', '买家小红', 0),
    ('buyer2', '123456', '买家阿伟', 0),
]


def ensure_raw_files(stdout_write=None) -> Path:
    """若缺少 CSV，自动调用 download.py"""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    missing = [f for f in (BX_BOOKS, BX_USERS, BX_RATINGS) if not f.exists() or f.stat().st_size < 1000]
    if not missing:
        return RAW_DIR
    if stdout_write:
        stdout_write('正在下载 Book-Crossing 数据集…')
    script = ROOT / 'data' / 'book_crossing' / 'download.py'
    subprocess.run([sys.executable, str(script)], check=True, cwd=str(ROOT))
    still = [f for f in (BX_BOOKS, BX_USERS, BX_RATINGS) if not f.exists()]
    if still:
        raise FileNotFoundError(
            'Book-Crossing 文件缺失: ' + ', '.join(p.name for p in still)
            + '\n请运行: python data/book_crossing/download.py'
        )
    return RAW_DIR


def _read_bx_csv(path: Path, names: list[str], usecols=None) -> pd.DataFrame:
    return pd.read_csv(
        path,
        sep=';',
        encoding='latin-1',
        on_bad_lines='skip',
        dtype=str,
        header=None,
        names=names,
        usecols=usecols,
        low_memory=False,
    )


def _norm_isbn(val) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip().strip('"').replace('-', '')
    if not s or s.lower() in ('0', 'nan', 'null'):
        return None
    if len(s) > 20:
        s = s[:20]
    return s


def _infer_category(title: str, author: str) -> str:
    text = f'{title} {author}'
    for cat, pat in CATEGORY_RULES:
        if pat.search(text):
            return cat
    return '文学'


def _estimate_price(year: int) -> Decimal:
    base = 35.0
    if year >= 2015:
        base = 68.0
    elif year >= 2005:
        base = 48.0
    elif year >= 1990:
        base = 32.0
    else:
        base = 22.0
    return Decimal(str(round(base, 2)))


def _location_nickname(loc: str, uid: str) -> str:
    if not loc or str(loc).lower() == 'nan':
        return f'读者{uid}'
    parts = str(loc).replace('"', '').split(',')
    city = parts[0].strip() if parts else f'读者{uid}'
    return city[:32] if city else f'读者{uid}'


class BookCrossingStats:
    def __init__(self):
        self.books = 0
        self.users = 0
        self.sells = 0
        self.ratings_used = 0
        self.behaviors = 0
        self.collects = 0
        self.orders = 0


class BookCrossingImporter:
    """将 BX 子集导入 Django 模型（由 seed_demo 调用）"""

    def __init__(
        self,
        max_books: int = 1800,
        max_users: int = 280,
        max_ratings: int = 12000,
        stdout=None,
    ):
        self.max_books = max_books
        self.max_users = max_users
        self.max_ratings = max_ratings
        self.stdout = stdout
        self.stats = BookCrossingStats()
        self._bx_to_user: dict[str, int] = {}
        self._isbn_to_book: dict[str, int] = {}
        self._isbn_to_sell: dict[str, int] = {}

    def log(self, msg: str):
        if self.stdout:
            self.stdout(msg)

    def run(self):
        from accounts.models import User
        from analytics.models import BehaviorLog, CrawlerLog
        from catalog.models import BookBase, Category
        from marketplace.models import BrowseHistory, Collect, SellBook
        from trade.models import OrderInfo

        ensure_raw_files(self.log)
        self.log('解析 BX-Books / Users / Ratings…')

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
        self._import_ratings_as_activity(ratings_df, User, SellBook, BehaviorLog, Collect, BrowseHistory, OrderInfo)

        CrawlerLog.objects.create(
            status=CrawlerLog.STATUS_OK,
            message=f'Book-Crossing import: {self.stats.books} books, {self.stats.ratings_used} ratings',
            records_count=self.stats.books,
        )
        return self.stats

    def _load_books_frame(self) -> pd.DataFrame:
        df = _read_bx_csv(BX_BOOKS, BOOK_COLS)
        df = df.rename(columns={
            'ISBN': 'isbn', 'Book-Title': 'title', 'Book-Author': 'author',
            'Year-Of-Publication': 'year', 'Publisher': 'publisher',
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

        ratings_isbn = pd.read_csv(
            BX_RATINGS, sep=';', encoding='latin-1', on_bad_lines='skip',
            header=None, names=RATING_COLS, usecols=[0, 1, 2], dtype=str, nrows=500000,
        )
        ratings_isbn = ratings_isbn.rename(columns={'ISBN': 'isbn', 'Book-Rating': 'rating'})
        ratings_isbn['isbn'] = ratings_isbn['isbn'].map(_norm_isbn)
        ratings_isbn = ratings_isbn.dropna(subset=['isbn'])
        ratings_isbn['rating'] = pd.to_numeric(ratings_isbn['rating'], errors='coerce').fillna(0)
        counts = ratings_isbn.groupby('isbn').size().sort_values(ascending=False)
        top_isbns = set(counts.head(self.max_books * 2).index)
        df = df[df['isbn'].isin(top_isbns)].drop_duplicates('isbn')
        df = df.head(self.max_books)
        return df

    def _load_users_frame(self) -> pd.DataFrame:
        df = _read_bx_csv(BX_USERS, USER_COLS)
        df = df.rename(columns={'User-ID': 'bx_uid', 'Location': 'location', 'Age': 'age'})
        df['bx_uid'] = df['bx_uid'].astype(str).str.strip().str.strip('"')
        df['age'] = pd.to_numeric(df['age'], errors='coerce')
        return df.drop_duplicates('bx_uid')

    def _load_ratings_frame(self, books_df: pd.DataFrame) -> pd.DataFrame:
        valid_isbn = set(books_df['isbn'])
        chunks = []
        total = 0
        for chunk in pd.read_csv(
            BX_RATINGS, sep=';', encoding='latin-1', on_bad_lines='skip',
            dtype=str, header=None, names=RATING_COLS, chunksize=100000,
        ):
            chunk = chunk.rename(columns={'User-ID': 'bx_uid', 'ISBN': 'isbn', 'Book-Rating': 'rating'})
            chunk['isbn'] = chunk['isbn'].map(_norm_isbn)
            chunk['bx_uid'] = chunk['bx_uid'].astype(str).str.strip().str.strip('"')
            chunk['rating'] = pd.to_numeric(chunk['rating'], errors='coerce').fillna(0).astype(int)
            chunk = chunk[chunk['isbn'].isin(valid_isbn)]
            chunks.append(chunk)
            total += len(chunk)
            if total >= self.max_ratings * 3:
                break
        df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
        if df.empty:
            return df
        active_users = df['bx_uid'].value_counts().head(self.max_users).index
        df = df[df['bx_uid'].isin(active_users)]
        return df.head(self.max_ratings)

    def _create_categories(self, Category):
        created = {}
        for name, parent_name in CATEGORIES:
            parent = created.get(parent_name) if parent_name else None
            cat, _ = Category.objects.get_or_create(cat_name=name, defaults={'parent': parent})
            created[name] = cat
        return created

    def _create_demo_users(self, User):
        for username, password, nickname, role in DEMO_USERS:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={'nickname': nickname, 'role': role, 'is_active': True},
            )
            user.set_password(password)
            user.nickname = nickname
            user.role = role
            user.save()

    def _import_bx_users(self, users_df: pd.DataFrame, User):
        count = 0
        for _, row in users_df.iterrows():
            bx_uid = row['bx_uid']
            if count >= self.max_users:
                break
            username = f'bx_{bx_uid}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'nickname': _location_nickname(row.get('location', ''), bx_uid),
                    'role': User.ROLE_USER,
                    'is_active': True,
                },
            )
            if created:
                user.set_password('123456')
                user.save()
            self._bx_to_user[bx_uid] = user.user_id
            count += 1
        self.stats.users = User.objects.count()

    def _import_books(self, books_df: pd.DataFrame, cat_map: dict, BookBase):
        for _, row in books_df.iterrows():
            cat = cat_map.get(row['cat_name']) or cat_map['其他']
            book, _ = BookBase.objects.update_or_create(
                isbn=row['isbn'],
                defaults={
                    'book_name': row['title'],
                    'author': row['author'],
                    'publisher': row.get('publisher', ''),
                    'pub_year': int(row['year']),
                    'original_price': Decimal(str(row['original_price'])),
                    'category': cat,
                    'tags': row['cat_name'],
                    'book_desc': (
                        f"{row['title']} — {row['author']}\n"
                        f"数据来源: Book-Crossing 数据集 (Ziegler et al., WWW 2005)"
                    ),
                },
            )
            self._isbn_to_book[row['isbn']] = book.book_id
            self.stats.books += 1

    def _import_sells(self, SellBook, User):
        import random
        from datetime import timedelta

        from catalog.models import BookBase
        from django.utils import timezone

        sellers = list(User.objects.filter(role=User.ROLE_USER).order_by('user_id'))
        if not sellers:
            return
        books = list(self._isbn_to_book.items())
        random.shuffle(books)
        now = timezone.now()
        for i, (isbn, book_id) in enumerate(books):
            seller = sellers[i % len(sellers)]
            book = BookBase.objects.get(book_id=book_id)
            op = float(book.original_price)
            quality = random.choices([2, 3, 4, 5], weights=[8, 22, 45, 25])[0]
            discount = random.uniform(0.28, 0.65)
            sell = SellBook.objects.create(
                book_id=book_id,
                user_id=seller.user_id,
                second_price=Decimal(str(round(op * discount, 2))),
                quality=quality,
                status=SellBook.STATUS_ON,
                audit_status=1 if i >= 3 else 0,
                create_time=now - timedelta(days=random.randint(0, 90)),
            )
            self._isbn_to_sell[isbn] = sell.sell_id
            self.stats.sells += 1

    def _import_ratings_as_activity(
        self, ratings_df, User, SellBook, BehaviorLog, Collect, BrowseHistory, OrderInfo,
    ):
        import random
        from datetime import timedelta
        from django.utils import timezone

        if ratings_df.empty:
            return

        # 补全 ratings 中出现的用户
        for bx_uid in ratings_df['bx_uid'].unique():
            if bx_uid in self._bx_to_user:
                continue
            username = f'bx_{bx_uid}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'nickname': f'读者{bx_uid}', 'role': User.ROLE_USER, 'is_active': True},
            )
            if created:
                user.set_password('123456')
                user.save()
            self._bx_to_user[bx_uid] = user.user_id

        now = timezone.now()
        logs = []
        for _, row in ratings_df.iterrows():
            isbn = row['isbn']
            bx_uid = row['bx_uid']
            rating = int(row['rating'])
            book_id = self._isbn_to_book.get(isbn)
            sell_id = self._isbn_to_sell.get(isbn)
            user_id = self._bx_to_user.get(bx_uid)
            if not book_id or not sell_id:
                continue
            self.stats.ratings_used += 1
            t = now - timedelta(days=random.randint(0, 60), hours=random.randint(0, 23))
            user = User.objects.filter(user_id=user_id).first() if user_id else None

            if rating == 0:
                action = BehaviorLog.ACTION_VIEW
            elif rating <= 5:
                action = BehaviorLog.ACTION_CLICK
            elif rating <= 7:
                action = BehaviorLog.ACTION_COLLECT
            else:
                action = BehaviorLog.ACTION_CONSULT

            logs.append(BehaviorLog(
                user=user,
                sell_id=sell_id,
                action_type=action,
                stay_time=random.randint(10, 300),
                action_time=t,
            ))

            if rating >= 7 and user:
                Collect.objects.get_or_create(user=user, sell_id=sell_id)
                self.stats.collects += 1
                BrowseHistory.objects.update_or_create(
                    user=user, sell_id=sell_id, defaults={'viewed_at': t},
                )

            if rating >= 9 and user:
                sell = SellBook.objects.get(sell_id=sell_id)
                if sell.user_id != user_id and random.random() < 0.15:
                    if not OrderInfo.objects.filter(buyer_id=user_id, sell_id=sell_id).exists():
                        OrderInfo.objects.create(
                            buyer_id=user_id,
                            seller_id=sell.user_id,
                            sell_id=sell_id,
                            deal_price=sell.second_price,
                            order_status=OrderInfo.STATUS_DONE,
                            finish_time=t + timedelta(days=2),
                            create_time=t,
                        )
                        self.stats.orders += 1

        BehaviorLog.objects.bulk_create(logs, batch_size=500)
        self.stats.behaviors = len(logs)
        self._sync_sell_counters(SellBook)

    def _sync_sell_counters(self, SellBook):
        from analytics.models import BehaviorLog
        from marketplace.models import Collect
        from trade.models import Message

        for sell in SellBook.objects.all():
            sell.view_count = BehaviorLog.objects.filter(
                sell=sell, action_type=BehaviorLog.ACTION_VIEW,
            ).count() + BehaviorLog.objects.filter(sell=sell).count() // 3
            sell.collect_count = Collect.objects.filter(sell=sell).count()
            sell.consult_count = Message.objects.filter(sell=sell).count()
            if sell.view_count > 80:
                sell.is_hot = True
            sell.save(update_fields=['view_count', 'collect_count', 'consult_count', 'is_hot'])
