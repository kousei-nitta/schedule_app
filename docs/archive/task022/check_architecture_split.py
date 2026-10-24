"""Task 022：docs/architecture.md の分割で、文が失われていないことを確かめる。

使い方（リポジトリのルートで）：
    python docs/archive/task022/check_architecture_split.py

確かめること：
- 分割の前の architecture.md（BASE の版）の空でない行が、決めた移す先の
  資料に、同じ順で、同じ文のまま入っている（見出しは、階層の違いを見ない）
- 例外として変えた行（LINE_CHANGES）は、変えたあとの文で入っている
- 移す先の資料で足した行と、書き直した節（REWRITE）を、一覧で出す

問題があれば、終了コード1で終わる。
"""

import difflib
import re
import subprocess
import sys
from pathlib import Path

# 分割の前の版（Task 022を始めたときの main）
BASE = "396e8b5"
ROOT = Path(__file__).resolve().parents[3]

# 元の行の範囲（1始まり、両端を含む）と、移す先。
# 移す先が None の範囲は、書き直した（REWRITE）か、資料の題名で置き換えた。
SEGMENTS = [
    (1, 4, None, "冒頭の題名と注意。各資料の先頭に、新しい題名と注意を書いた"),
    (5, 48, "docs/architecture/overview.md", ""),
    (49, 54, "docs/open_questions.md", "REWRITE"),
    (55, 55, "docs/archive/migration_before_class_event_generation.md", ""),
    (56, 58, "docs/open_questions.md", "REWRITE"),
    (59, 172, "docs/architecture/data_model.md", ""),
    (173, 279, "docs/architecture/class_events.md", ""),
    (280, 293, "docs/archive/migration_before_class_event_generation.md", ""),
    (294, 361, "docs/architecture/class_events.md", ""),
    (362, 375, "docs/development/database.md", ""),
    (376, 402, "docs/architecture/data_model.md", ""),
    (403, 415, "docs/development/database.md", ""),
    (416, 439, "docs/development/database.md", "REWRITE"),
    (440, 592, "docs/architecture/api.md", ""),
    (593, 930, "docs/architecture/api_endpoints.md", ""),
    (931, 1038, "docs/architecture/frontend.md", ""),
    (1039, 1088, "docs/development/testing.md", ""),
    (1089, 1162, "docs/architecture/overview.md", ""),
    (1163, 1168, "docs/development/workflow.md", "REWRITE"),
    (1169, 1174, "docs/development/database.md", ""),
]

# 例外として変えた行：{元の行番号: (変えたあとの文（None は削除）, 理由)}
LINE_CHANGES = {
    186: (
        "| 曜日の読み替え（振替授業日） | 確定 | 扱わない（読み替えた曜日の授"
        "業の予定を作らない）。現状は必要ない（2026-10-20）。将来の検討事項「"
        "曜日の読み替え（振替授業日）」（`docs/open_questions.md`） |",
        "曜日の読み替え：未決定事項から、将来の検討事項へ移した（ADR 0001 の6"
        "）",
    ),
    190: (
        "例：学期を 2026-04-13（月）〜2026-07-17（金）とすると、期間内で曜日"
        "が一致する日は、月〜金が各14日。休講日を登録していなければ、月曜の授"
        "業の予定は14件作られる。休講日として 5/4（月）を登録してあれば、13件"
        "になる。休講日を正しく登録しても、曜日によって13回にそろわない場合は"
        "、曜日の読み替えが必要かどうかの判断の材料になる（将来の検討事項「曜"
        "日の読み替え（振替授業日）」。`docs/open_questions.md`）。",
        "曜日の読み替え：参照先を、将来の検討事項に変えた",
    ),
    214: (
        None,
        "参照：指していた節（予定の自動生成より前に登録した授業）を、docs/arc"
        "hive/ へ移した",
    ),
    369: (
        "- カラムの追加・変更などのスキーマ変更は、`docs/architecture/data_mo"
        "del.md` の「データ設計」の承認なしに行わない。",
        "参照：移した先（database.md）では、「このファイル」が指すものが変わ"
        "る",
    ),
    370: (
        "- 自動生成されたmigrationファイルはレビュー対象。KomaがPRで内容を確"
        "かめてから、マージする（確かめる前に、開発用DBに適用しない）。生成・"
        "確認・開発用DBへの適用の進め方は、下の「migrationの作成と適用」。",
        "体制の変更：承認ゲート（承認の前は、どのDBにも適用しない）をやめ、PR"
        "でKomaが確かめる形にした",
    ),
    372: (
        "- 制約には一貫した命名規則を付ける（`docs/architecture/data_model.md"
        "` の「制約の命名規則」）。",
        "参照：「制約の命名規則」は data_model.md へ移した（「下記」でなくな"
        "る）",
    ),
    414: (
        "流れは「モデルを変更 → `migrate`（ファイル生成） → 内容を確認 → `upg"
        "rade`（DBに適用）」。このプロジェクトでの進め方（生成に使うDB、Koma"
        "の確認、開発用DBへの適用の担当）は、次の「migrationの作成と適用」。",
        "体制の変更：「承認ゲート」をなくした",
    ),
    1052: (
        "- `pytest` は、`requirements-dev.txt` に、バージョンを固定して書く（"
        "依存するライブラリも、ファイルの形式に合わせる。`requirements.txt` "
        "には、アプリを動かすものだけを書く）",
        "pytestの置き場所を requirements-dev.txt に変えた（設計の推奨案4）",
    ),
    1090: (
        "以下は目標の構成。`.git/`・`.venv/`・`.vscode/` は作成済みで、変更し"
        "ない。",
        "ディレクトリ構成：.gitignore と README.md は、Task 022で変える",
    ),
    1141: (
        "├── docs/                    # 資料（何がどこにあるかは docs/README."
        "md）",
        "ディレクトリ構成：資料の索引を示した",
    ),
    1142: (
        "├── .github/workflows/ci.yml # CI（GitHub Actions。docs/development/"
        "testing.md の「CI」）",
        "ディレクトリ構成：copilot-instructions.md を削除し、CIを足した",
    ),
    1145: (
        "│   ├── test_setup.py        # テスト基盤そのものの確認（migrationで"
        "作られるテーブル・列・制約の確認と、モデルとmigrationのずれの確認を"
        "含む）",
        "ディレクトリ構成：ずれのテストを足した",
    ),
    1154: (
        "├── README.md                # リポジトリの表紙（概要・機能・技術・"
        "起動方法・開発体制）",
        "ディレクトリ構成：README.md を書いた",
    ),
}


def normalize(line):
    """見出しは階層を外し、行末の空白を除く。"""
    line = line.rstrip()
    match = re.match(r"^#+ (.*)$", line)
    if match:
        return "# " + match.group(1)
    return line


def content_lines(lines):
    """空でない行を、正規化して返す。

    コードブロックの中の # で始まる行は、見出しとして扱わない。
    """
    result = []
    in_fence = False
    for line in lines:
        if line.startswith("```"):
            in_fence = not in_fence
            result.append(line.rstrip())
            continue
        if not line.strip():
            continue
        result.append(line.rstrip() if in_fence else normalize(line))
    return result


def main():
    original = subprocess.run(
        ["git", "show", f"{BASE}:docs/architecture.md"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("\n")
    if original[-1] == "":
        original = original[:-1]

    problems = []

    # すべての行が、どれか1つの範囲に入っていること
    covered = []
    for start, end, _, _ in SEGMENTS:
        covered.extend(range(start, end + 1))
    if covered != list(range(1, len(original) + 1)):
        problems.append("範囲が、元の行をちょうど1回ずつ覆っていない")

    # 移す先ごとに、元の範囲の一覧を作る
    expected = {}
    rewrites = []
    for start, end, destination, mode in SEGMENTS:
        if destination is None or mode == "REWRITE":
            rewrites.append((start, end, destination, mode))
            continue
        lines = []
        for number in range(start, end + 1):
            line = original[number - 1]
            if number in LINE_CHANGES:
                line = LINE_CHANGES[number][0]
                if line is None:
                    continue
            lines.append(line)
        expected.setdefault(destination, []).append((start, end, lines))

    # 範囲ごとに、移す先の資料の中に、同じ順で、同じ文があるかを確かめる。
    # どの範囲とも一致しなかった行が、足した行。
    for destination, segments in expected.items():
        text = (ROOT / destination).read_text(encoding="utf-8")
        have = content_lines(text.split("\n"))
        matched = set()
        total = 0
        for start, end, lines in segments:
            want = content_lines(lines)
            total += len(want)
            matcher = difflib.SequenceMatcher(
                None, want, have, autojunk=False
            )
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == "equal":
                    matched.update(range(j1, j2))
                elif tag in ("delete", "replace"):
                    problems.append(
                        f"{destination}（元の{start}〜{end}行目）："
                        "元の文と違う／ない"
                    )
                    for line in want[i1:i2]:
                        problems.append(f"  元：{line[:100]}")
        added = [
            line for index, line in enumerate(have) if index not in matched
        ]
        print(f"== {destination}：元の文 {total}行。足した行 "
              f"{len(added)}行")
        for line in added:
            print(f"  ＋ {line[:100]}")

    print("\n== 例外として変えた行")
    for number, (line, reason) in sorted(LINE_CHANGES.items()):
        print(f"  {number}行目：{reason}")
        print(f"    元：{original[number - 1][:100]}")
        print(f"    今：{(line or '（削除）')[:100]}")

    print("\n== 書き直した範囲（中身は、PRの差分で確かめる）")
    for start, end, destination, mode in rewrites:
        label = destination or "（各資料の冒頭）"
        print(f"  {start}〜{end}行目 → {label} {mode}")

    if problems:
        print("\n== 問題")
        for problem in problems:
            print(problem)
        return 1
    print("\n問題なし")
    return 0


if __name__ == "__main__":
    sys.exit(main())
