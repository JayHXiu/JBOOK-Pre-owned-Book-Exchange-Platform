import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine

# 已填你的Railway PostgreSQL信息
host = "postgres.railway.internal"
port = "5432"
user = "postgres"
pwd = "WxegwuCczchTPKZUXYJolgTgiATbxeGM"
dbname = "railway"

RAW_DIR = Path(__file__).resolve().parent

BOOK_COLS = [
    'ISBN', 'Book-Title', 'Book-Author', 'Year-Of-Publication', 'Publisher',
    'Image-URL-S', 'Image-URL-M', 'Image-URL-L',
]
USER_COLS = ['User-ID', 'Location', 'Age']
RATING_COLS = ['User-ID', 'ISBN', 'Book-Rating']


def read_bx_csv(filename: str, names: list[str]) -> pd.DataFrame:
    """Book-Crossing CSV：无表头、分号分隔；脏行跳过（与项目 book_crossing.py 一致）。"""
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


engine = create_engine(f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{dbname}")

# 1. 导入图书 BX-Books.csv → book 表
df_book = read_bx_csv('BX-Books.csv', BOOK_COLS)
df_book.to_sql('book', con=engine, if_exists='append', index=False)
print(f'BX-Books 导入完成，共 {len(df_book)} 行')

# 2. 导入用户 BX-Users.csv → users 表
df_user = read_bx_csv('BX-Users.csv', USER_COLS)
df_user.to_sql('users', con=engine, if_exists='append', index=False)
print(f'BX-Users 导入完成，共 {len(df_user)} 行')

# 3. 导入评分 BX-Book-Ratings.csv → ratings 表（分块读取，避免内存溢出）
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
    chunks.append(chunk)
df_rate = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
df_rate.to_sql('ratings', con=engine, if_exists='append', index=False)
print(f'BX-Book-Ratings 导入完成，共 {len(df_rate)} 行')
