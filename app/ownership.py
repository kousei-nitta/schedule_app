"""認可：ログインした利用者の、自分のデータだけを扱う。

仕様は docs/architecture/api.md の「利用者ごとのデータ（認可）」。
- 他人のデータは、「存在しない」と同じに扱う（URLのIDなら404、本文で
  参照したIDなら「指定された…が存在しません」）。他人のデータがあること
  も、知らせない
- routeでは、IDでデータを取るときに db.session.get を使わず、
  get_owned を使う（tests/test_authorization.py が確かめる）。一覧・件数・
  一括の削除などの文には、Model.user_id == current_user_id() の条件を
  付ける
"""
from app.auth import current_user_id
from app.extensions import db


def get_owned(model, object_id: int):
    """ログインした利用者のものなら、そのデータを返す（なければ None）。

    他人のデータも、存在しないデータも、同じく None。
    """
    return db.session.scalar(
        db.select(model).where(
            model.id == object_id,
            model.user_id == current_user_id(),
        )
    )
