"""
将 BX CSV 导入 PostgreSQL 原始表 book / users / ratings。
凭据从环境变量读取（不要把密码写进代码）。

  set BX_PG_HOST=turntable.proxy.rlwy.net
  set BX_PG_PORT=28777
  set BX_PG_USER=postgres
  set BX_PG_PASSWORD=你的密码
  set BX_PG_DB=railway
  python load_bx.py
"""
import os
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine, text

HOST = os.getenv('BX_PG_HOST', 'turntable.proxy.rlwy.net')
PORT = os.getenv('BX_PG_PORT', '28777')
USER = os.getenv('BX_PG_USER', 'postgres')
PWD = os.getenv('BX_PG_PASSWORD', '')
DB = os.getenv('BX_PG_DB', 'railway')

if not PWD:
    raise SystemExit('请设置环境变量 BX_PG_PASSWORD')

RAW_DIR = Path(__file__).resolve().parent
engine = create_engine(f'postgresql+psycopg2://{USER}:{PWD}@{HOST}:{PORT}/{DB}')

BOOK_COLS = [
    'ISBN', 'Book-Title', 'Book-Author', 'Year-Of-Publication', 'Publisher',
    'Image-URL-S', 'Image-URL-M', 'Image-URL-L',
]
USER_COLS = ['User-ID', 'Location', 'Age']
RATING_COLS = ['User-ID', 'ISBN', 'Book-Rating']


def read_bx_csv(filename: str, names: list[str]) -> pd.DataFrame:
    return pd.read_csv(
        RAW_DIR / filename,
        sep=';',
        encoding='latin-1',
        on_bad_lines='skip',
        dtype=str,
        header=None,
        names=names,
        low_memory=False,
    )


def load_books() -> pd.DataFrame:
    df = read_bx_csv('BX-Books.csv', BOOK_COLS)
    df = df.rename(columns={
        'ISBN': 'isbn',
        'Book-Title': 'booktitle',
        'Book-Author': 'bookauthor',
        'Year-Of-Publication': 'yearofpublication',
        'Publisher': 'publisher',
    })
    df['isbn'] = df['isbn'].str.strip().str.strip('"')
    df = df.dropna(subset=['isbn'])
    df = df[df['isbn'].str.len() > 0]
    df['yearofpublication'] = pd.to_numeric(df['yearofpublication'], errors='coerce').astype('Int64')
    return df.drop_duplicates(subset=['isbn'], keep='first')[
        ['isbn', 'booktitle', 'bookauthor', 'yearofpublication', 'publisher']
    ]


def load_users() -> pd.DataFrame:
    df = read_bx_csv('BX-Users.csv', USER_COLS)
    df = df.rename(columns={'User-ID': 'userid', 'Location': 'location', 'Age': 'age'})
    df['userid'] = pd.to_numeric(df['userid'].str.strip().str.strip('"'), errors='coerce')
    df['age'] = pd.to_numeric(df['age'], errors='coerce')
    df = df.dropna(subset=['userid'])
    df['userid'] = df['userid'].astype(int)
    return df.drop_duplicates(subset=['userid'], keep='first')[['userid', 'location', 'age']]


def load_ratings() -> pd.DataFrame:
    chunks = []
    for chunk in pd.read_csv(
        RAW_DIR / 'BX-Book-Ratings.csv',
        sep=';',
        encoding='latin-1',
        on_bad_lines='skip',
        dtype=str,
        header=None,
        names=RATING_COLS,
        chunksize=100_000,
    ):
        chunk = chunk.rename(columns={
            'User-ID': 'userid',
            'ISBN': 'isbn',
            'Book-Rating': 'bookrating',
        })
        chunk['userid'] = pd.to_numeric(
            chunk['userid'].str.strip().str.strip('"'), errors='coerce'
        )
        chunk['isbn'] = chunk['isbn'].str.strip().str.strip('"')
        chunk['bookrating'] = pd.to_numeric(chunk['bookrating'], errors='coerce')
        chunk = chunk.dropna(subset=['userid', 'isbn'])
        chunk['userid'] = chunk['userid'].astype(int)
        chunk['bookrating'] = chunk['bookrating'].astype(int)
        chunks.append(chunk[['userid', 'isbn', 'bookrating']])
    if not chunks:
        return pd.DataFrame()
    return pd.concat(chunks, ignore_index=True).drop_duplicates(
        subset=['userid', 'isbn'], keep='first',
    )


with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS book (
            isbn VARCHAR(20) PRIMARY KEY,
            booktitle TEXT,
            bookauthor VARCHAR(255),
            yearofpublication INT,
            publisher VARCHAR(255)
        );
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            userid INT PRIMARY KEY,
            location TEXT,
            age INT NULL
        );
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS ratings (
            userid INT,
            isbn VARCHAR(20),
            bookrating INT,
            PRIMARY KEY (userid, isbn)
        );
    """))
    conn.execute(text('TRUNCATE TABLE ratings, users, book RESTART IDENTITY CASCADE;'))

print('正在导入 BX-Books.csv...')
df_book = load_books()
df_book.to_sql('book', engine, index=False, if_exists='append', chunksize=5000)
print(f'BX-Books 完成，{len(df_book)} 行')

print('正在导入 BX-Users.csv...')
df_user = load_users()
df_user.to_sql('users', engine, index=False, if_exists='append', chunksize=5000)
print(f'BX-Users 完成，{len(df_user)} 行')

print('正在导入 BX-Book-Ratings.csv...')
df_rate = load_ratings()
df_rate.to_sql('ratings', engine, index=False, if_exists='append', chunksize=5000)
print(f'BX-Book-Ratings 完成，{len(df_rate)} 行')
print('全部导入成功。下一步：在 Django 服务执行 python manage.py bootstrap_jbook --source pg --force')
