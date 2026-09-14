"""词库导入脚本：从 ECDICT（https://github.com/skywind3000/ECDICT，MIT 协议）CSV 构建系统级词书。

用法（在 backend/ 下）：
    uv run python -m app.scripts.import_vocab --csv path/to/ecdict.csv --book cet4
    uv run python -m app.scripts.import_vocab --csv ecdict.csv --book ky --limit 5000

适合整库大文件导入；页面上还有交互式导入（系统级/用户级）见 /api/vocab/books/import。
- 按 ECDICT 的 tag 列筛词构建词书（tag 以 / 分隔，如 "cet4/cet6/ky"）
- 解析逻辑复用 app/services/vocab_import.py
- 幂等：单词按小写拼写全局去重 upsert，词书重复导入只刷新映射与计数
- 仅支持 SQLite/MySQL/PostgreSQL 中由 DATABASE_URL 指定的库，schema 缺失时先建表
"""

import argparse
import sys
from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import create_database_engine, create_session_factory, init_database
from app.models.vocab import VocabBook, VocabBookWord, VocabWord
from app.services.vocab_import import MAX_WORD_LEN, ParsedWord, parse_translation

# 词书 slug → ECDICT tag 标记（tag 列以 / 分隔）
BOOK_TAGS: dict[str, str] = {
    "cet4": "cet4",
    "cet6": "cet6",
    "kaoyan": "ky",
    "ielts": "ielts",
    "toefl": "toefl",
    "gre": "gre",
    "gaokao": "gk",
    "zhongkao": "zk",
}

BOOK_META: dict[str, dict[str, str]] = {
    "cet4": {"name": "英语四级核心词汇", "emoji": "🎓"},
    "cet6": {"name": "英语六级核心词汇", "emoji": "🎓"},
    "kaoyan": {"name": "考研英语核心词汇", "emoji": "📚"},
    "ielts": {"name": "雅思核心词汇", "emoji": "🌍"},
    "toefl": {"name": "托福核心词汇", "emoji": "🌍"},
    "gre": {"name": "GRE 核心词汇", "emoji": "🧠"},
    "gaokao": {"name": "高考英语核心词汇", "emoji": "✏️"},
    "zhongkao": {"name": "中考英语核心词汇", "emoji": "✏️"},
}

MAX_SENSES = 6  # 每词最多保留的释义条数


def parse_rows(csv_path: str, tag: str) -> Iterator[ParsedWord]:
    """扫描 ECDICT CSV，产出带目标 tag 的单词（按词频升序 = 常用优先）。"""
    buffer: list[ParsedWord] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = (row.get("word") or "").strip().lower()
            tags = (row.get("tag") or "").lower()
            if not word or len(word) > MAX_WORD_LEN or " " in word:
                continue  # 跳过长条目/词组，打字练习以单词为主
            if f"{tag}/" not in f"{tags}/" and tags.split("/") != [tag]:
                continue
            freq = int(row.get("frq") or 0) or int(row.get("bnc") or 0)
            buffer.append(
                ParsedWord(
                    word=word,
                    phonetic=(row.get("phonetic") or "").strip(),
                    translations=parse_translation(row.get("translation") or ""),
                    freq=freq,
                )
            )
    buffer.sort(key=lambda w: (w.freq == 0, w.freq or 1 << 30, w.word))
    yield from buffer


def import_book(csv_path: str, slug: str, limit: int | None) -> None:
    if slug not in BOOK_TAGS:
        print(f"未知词书 slug: {slug}（可选: {', '.join(BOOK_TAGS)}）")
        sys.exit(1)
    tag = BOOK_TAGS[slug]
    now = datetime.now(UTC)

    engine = create_database_engine(get_settings().database_url)
    init_database(engine)  # 全新库兜底建表
    session_factory = create_session_factory(engine)

    words = list(parse_rows(csv_path, tag))
    if limit:
        words = words[:limit]
    if not words:
        print(f"CSV 中未找到 tag={tag} 的单词，请确认文件为 ECDICT 全量 csv")
        sys.exit(1)

    with session_factory() as session:
        book = session.scalar(select(VocabBook).where(VocabBook.slug == slug))
        if book is None:
            meta = BOOK_META.get(slug, {})
            book = VocabBook(slug=slug, name=meta.get("name", slug), emoji=meta.get("emoji", "📖"), sort=0)
            session.add(book)
            session.flush()

        # 旧映射清掉重排（词书内顺序按词频刷新）
        for row in session.query(VocabBookWord).filter(VocabBookWord.book_id == book.id):
            session.delete(row)
        session.flush()

        existing = {w.word: w.id for w in session.query(VocabWord)}
        imported = 0
        for sort, parsed in enumerate(words):
            word_id = existing.get(parsed.word)
            if word_id is None:
                item = VocabWord(
                    word=parsed.word,
                    phonetic_uk=parsed.phonetic,
                    phonetic_us="",
                    translations=parsed.translations,
                    sentences=[],
                    phrases=[],
                    synos=[],
                    rel_words={},
                    freq=parsed.freq,
                    created_at=now,
                    updated_at=now,
                )
                session.add(item)
                session.flush()
                existing[parsed.word] = item.id
                word_id = item.id
            else:  # 词已在库（多词书共享）：补齐词频/音标缺失字段
                session.get(VocabWord, word_id).freq = session.get(VocabWord, word_id).freq or parsed.freq
            session.add(VocabBookWord(book_id=book.id, word_id=word_id, sort=sort, created_at=now))
            imported += 1

        book.word_count = imported
        book.updated_at = now
        session.commit()
        print(f"词书 {slug}（{book.name}）导入完成：{imported} 词")


def main() -> None:
    parser = argparse.ArgumentParser(description="ECDICT 词库导入（见本文件 docstring）")
    parser.add_argument("--csv", required=True, help="ECDICT ecdict.csv 路径")
    parser.add_argument("--book", default="cet4", help=f"词书 slug：{', '.join(BOOK_TAGS)}")
    parser.add_argument("--limit", type=int, default=None, help="最多导入词数（默认全部）")
    args = parser.parse_args()
    import_book(args.csv, args.book, args.limit)


if __name__ == "__main__":
    main()
