import sqlite3

from sqlalchemy import Engine, MetaData, event
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

db = SQLAlchemy(metadata=MetaData(naming_convention=NAMING_CONVENTION))
migrate = Migrate()


@event.listens_for(Engine, "connect")
def configure_sqlite_connection(dbapi_connection, connection_record) -> None:
    """SQLite のDBにつなぐたびに、secure_delete と temp_store を決める。

    - secure_delete = ON：オフ（SQLite の既定）では、消した行（予定の
      メモなど）の中身が、DBのファイルの空き領域に残る。DBのファイルや
      バックアップが漏れたときに、消したはずの個人の情報が読めてしまう
      ため、消すときに0で上書きさせる（docs/architecture/security.md の
      「入力」）
    - temp_store = MEMORY：並べ替えなどの一時的なデータを、ファイル
      （/tmp など。共有のサーバーでは、ほかの利用者と同じ場所かも
      しれない）でなく、メモリーに置く。このアプリのDBは小さい
    SQLite でないDBでは、何もしない。
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA secure_delete = ON")
        cursor.execute("PRAGMA temp_store = MEMORY")
        cursor.close()
