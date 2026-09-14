"""词书文本解析（导入功能与 CLI 脚本共用）。

支持三种格式，自动识别：
- Anki 导出文本（Notes in Plain Text：`正面<TAB>背面`，支持 #separator/#deck/#html 等元信息头，
  背面 HTML 的 <br> 会拆成多条释义）
- ECDICT CSV（表头含 word/translation 列，如 skywind3000/ECDICT 的 ecdict.csv）
- 简单行格式：每行一个单词，可选释义——`word` / `word,释义` / `word<TAB>释义` / `word 释义`
"""

import csv
import io
import re
from dataclasses import dataclass, field

MAX_WORD_LEN = 40
MAX_SENSES = 6  # 每词最多保留的释义条数
MAX_WORDS = 50000  # 单次导入词数上限
MAX_TEXT_CHARS = 30_000_000  # 单次导入文本上限（约 30MB）

_POS_RE = re.compile(r"^(n|v|vt|vi|adj|adv|prep|conj|pron|art|num|interj|aux)\.\s*(.+)$", re.IGNORECASE)
_WORD_RE = re.compile(r"[a-z]")  # 至少含一个字母，过滤纯符号行
_BRE_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
ANKI_SEPARATORS = {"tab": "\t", "comma": ",", "semicolon": ";", "pipe": "|", "colon": ":", "space": " "}


def _clean_word(raw: str) -> str:
    """规整单词：小写、去首尾标点；无字母或超长视为无效返回空串。"""
    word = raw.strip().lower().strip(".,;:!?'\"()[]{}·、，。；：")
    if not word or len(word) > MAX_WORD_LEN or " " in word or not _WORD_RE.search(word):
        return ""
    return word


@dataclass
class ParsedWord:
    word: str
    phonetic: str = ""
    translations: list[dict] = field(default_factory=list)
    freq: int = 0  # 词频排名（越小越常用，0=未知）


def parse_translation(raw: str) -> list[dict]:
    """ECDICT translation 列：'vt. 取消\\nn. 撤销' → [{pos, cn}]。"""
    senses: list[dict] = []
    for line in (raw or "").replace("\r\n", "\n").replace("\\n", "\n").split("\n"):
        line = line.strip()
        if not line:
            continue
        pos, sep, cn = line.partition(" ")
        if sep and pos.endswith(".") and len(pos) <= 6:
            senses.append({"pos": pos, "cn": cn.strip()})
        else:
            senses.append({"pos": "", "cn": line})
    return senses[:MAX_SENSES]


def _simple_sense(raw: str) -> list[dict]:
    """简单格式的释义：'vt. 取消' 拆词性；否则整句作为一条无词性释义。"""
    raw = (raw or "").strip()
    if not raw:
        return []
    m = _POS_RE.match(raw)
    if m:
        return [{"pos": m.group(1).lower() + ".", "cn": m.group(2).strip()}]
    return [{"pos": "", "cn": raw}]


def _simple_sense_multi(raw: str) -> list[dict]:
    """多行释义（Anki 背面 <br> 拆行后）：逐行解析，最多 MAX_SENSES 条。"""
    senses: list[dict] = []
    for line in (raw or "").replace("\r\n", "\n").split("\n"):
        senses.extend(_simple_sense(line))
        if len(senses) >= MAX_SENSES:
            break
    return senses[:MAX_SENSES]


def parse_anki_text(text: str) -> tuple[list[ParsedWord], str]:
    """解析 Anki 导出文本，返回 (单词列表, #deck 建议词书名)。

    支持 #separator / #html / #deck 元信息头；数据行按分隔符切字段，
    第一列 = 单词，其余列合并为背面释义（HTML 的 <br> 拆为多条释义）。
    """
    separator: str | None = None
    deck_name = ""
    data_lines: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        s = line.strip()
        if s.startswith("#"):
            key, _, value = s.partition(":")
            k = key.lower()
            if k == "#separator":
                separator = ANKI_SEPARATORS.get(value.strip().lower())
            elif k == "#deck":
                deck_name = value.strip()
            continue
        data_lines.append(line)

    if separator is None:  # 未声明分隔符：Tab 优先，其次逗号，最后空格
        if any("\t" in l for l in data_lines):
            separator = "\t"
        elif any("," in l for l in data_lines):
            separator = ","
        else:
            separator = " "

    out: list[ParsedWord] = []
    for line in data_lines:
        if not line.strip():
            continue
        parts = line.split(separator)
        word = _clean_word(parts[0])
        if not word:
            continue
        # Anki Basic 语义：第二列 = 背面（释义），其余列（如标签）忽略
        back = parts[1].strip() if len(parts) > 1 else ""
        if "<" in back:  # Anki 常开 #html:true：<br> 拆行，其余标签剔除
            back = _BRE_RE.sub("\n", back)
            back = _TAG_RE.sub("", back)
        out.append(ParsedWord(word=word, translations=_simple_sense_multi(back)))
    return out, deck_name


def parse_ecdict_text(text: str) -> list[ParsedWord]:
    """解析 ECDICT CSV 文本（word/phonetic/translation/tag/frq/bnc 列）。"""
    out: list[ParsedWord] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        word = _clean_word(row.get("word") or "")
        if not word:
            continue
        try:
            freq = int(row.get("frq") or 0) or int(row.get("bnc") or 0)
        except ValueError:
            freq = 0
        out.append(
            ParsedWord(
                word=word,
                phonetic=(row.get("phonetic") or "").strip(),
                translations=parse_translation(row.get("translation") or ""),
                freq=freq,
            )
        )
    return out


def parse_simple_text(text: str) -> list[ParsedWord]:
    """解析简单行格式：word / word,释义 / word<TAB>释义 / word 释义。# 开头为注释。"""
    out: list[ParsedWord] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # 逗号 / Tab 分隔优先（释义里可能含空格）
        for sep in (",", "\t"):
            if sep in line:
                word, _, trans = line.partition(sep)
                break
        else:
            word, _, trans = line.partition(" ")
        word = _clean_word(word)
        if not word:
            continue
        out.append(ParsedWord(word=word, translations=_simple_sense(trans)))
    return out


def parse_import_text(text: str) -> tuple[str, list[ParsedWord], str]:
    """自动识别格式并解析，返回 (格式名, 单词列表, #deck 建议词书名)。

    词内去重（保留首个），截断到 MAX_WORDS 上限。识别顺序：ECDICT 表头 →
    Anki 元信息头（#separator/#deck/#html…）→ 简单行格式。
    """
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError("导入文本过大（上限约 30MB）")
    head = text.lstrip("﻿").lstrip()[:500]
    lower_head = head.lower()
    first_line = lower_head.split("\n", 1)[0]
    deck_name = ""
    if first_line.startswith("word") and "translation" in first_line:
        fmt, words = "ecdict", parse_ecdict_text(text)
    elif any(line.strip().lower().startswith(("#separator", "#deck", "#html", "#notetype", "#tags")) for line in lower_head.split("\n")):
        fmt, words, deck_name = "anki", *parse_anki_text(text)
    else:
        fmt, words = "simple", parse_simple_text(text)
    # 文本内去重（保留首个），并截断到上限
    seen: set[str] = set()
    unique: list[ParsedWord] = []
    for w in words:
        if w.word in seen:
            continue
        seen.add(w.word)
        unique.append(w)
        if len(unique) >= MAX_WORDS:
            break
    return fmt, unique, deck_name
