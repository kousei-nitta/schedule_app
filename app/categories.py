"""カテゴリの保存値（DBの category の値）と、APIで受け付ける値の一覧。

カテゴリの保存値は、このファイルの定数だけで持ち、ほかのファイルに
文字列（"class" など）を直接書かない。画面に出す表示名・色・アイコンは、
画面側の対応表（app/static/js/categories.js）で持つ。
"""

# 予定（Event）のカテゴリ。
EVENT_CATEGORY_CLASS = "class"
EVENT_CATEGORY_PART_TIME = "part_time"
EVENT_CATEGORY_OTHER = "other"

# 予定のAPIで category を受け付けるときの許可値（予定の登録・編集を
# 作るタスクで使う）。
EVENT_CATEGORIES = (
    EVENT_CATEGORY_CLASS,
    EVENT_CATEGORY_PART_TIME,
    EVENT_CATEGORY_OTHER,
)

# 課題・タスク（Task）のカテゴリ。
TASK_CATEGORY_ASSIGNMENT = "assignment"
TASK_CATEGORY_OTHER = "other"

# 課題・タスクのAPIで category を受け付けるときの許可値。
TASK_CATEGORIES = (
    TASK_CATEGORY_ASSIGNMENT,
    TASK_CATEGORY_OTHER,
)
