# -*- coding: utf-8 -*-
"""配置与数据快照的声明式校验。

为什么需要：`accounts.py` 与 `data/*.json` 是唯一数据源，但此前没有任何
结构约束——漏一个语言的 description、链接写成空串、stats 里混进字符串，
都要等到渲染时才会以 KeyError/TypeError 的形式炸出来，或者更糟：渲染成功
但页面缺一块。

本模块把约束写成**纯数据**（SCHEMA 常量），由一个 60 行的校验器执行，
不依赖任何第三方库；若环境里装了 `jsonschema`，额外用它再校验一遍 JSON
快照（双保险，不是必需）。

错误信息带路径，例如 `ACCOUNTS.gitcode_badhope.works[3] -> 未定义的作品 id
'lens'`，比堆栈直接得多。
"""

import json
import pathlib

import accounts as A

from .paths import ROOT


class SchemaError(ValueError):
    def __init__(self, problems):
        self.problems = problems
        super().__init__("\n".join(problems))


REQUIRED_LANGS = ("md", "zh-CN", "ja")

ACCOUNT_SCHEMA = {
    "platform": {"type": str, "choices": ("github", "gitcode", "gitee")},
    "handle": {"type": str, "nonempty": True},
    "home": {"type": str, "prefix": "http"},
    "home_display": {"type": str, "nonempty": True},
    "repo_path": {"type": str, "nonempty": True},
    "role": {"type": dict, "langs": True},
    "tagline": {"type": dict, "langs": True},
    "about": {"type": dict, "langs": True},
    "now": {"type": dict, "langs": True, "lists": True},
    "skills": {"type": list, "nonempty": True, "items": str},
    "works": {"type": list, "nonempty": True, "items": str},
    "contrib": {"type": str, "choices": ("own", "shared")},
}

WORK_SCHEMA = {
    "title": {"type": str, "nonempty": True},
    "desc": {"type": dict, "langs": True},
    "tags": {"type": dict, "langs": True},
    "links": {"type": dict, "nonempty": True},
}

STATS_BLOCK_SCHEMA = {
    "repos": {"type": int, "optional": True},
    "stars": {"type": int, "optional": True},
    "followers": {"type": int, "optional": True},
    "merged": {"type": int, "optional": True},
}

WRITING_ITEM_SCHEMA = {
    "title": {"type": str, "nonempty": True},
    "url": {"type": str, "prefix": "http"},
    "date": {"type": str, "optional": True},
}


def _check_value(path, value, spec, problems):
    expected = spec["type"]
    if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
        problems.append("%s -> 期望 %s，实际 %s" % (path, expected.__name__, type(value).__name__))
        return
    if spec.get("nonempty"):
        if (expected is str and not value.strip()) or (expected in (list, dict) and not value):
            problems.append("%s -> 不能为空" % path)
    if "choices" in spec and value not in spec["choices"]:
        problems.append("%s -> 取值 %r 不在 %r" % (path, value, spec["choices"]))
    if "prefix" in spec and not str(value).startswith(spec["prefix"]):
        problems.append("%s -> 必须以 %r 开头，实际 %r" % (path, spec["prefix"], value))
    if "items" in spec:
        for i, item in enumerate(value):
            if not isinstance(item, spec["items"]):
                problems.append("%s[%d] -> 期望 %s" % (path, i, spec["items"].__name__))
    if spec.get("langs"):
        for lang in REQUIRED_LANGS:
            if lang not in value:
                problems.append("%s -> 缺少语言 %s" % (path, lang))
            elif spec.get("lists"):
                if not isinstance(value[lang], list) or not value[lang]:
                    problems.append("%s.%s -> 必须是非空数组" % (path, lang))
            elif not str(value.get(lang) or "").strip():
                problems.append("%s.%s -> 不能为空" % (path, lang))


def _check_mapping(path, data, schema, problems):
    for field, spec in schema.items():
        if field not in data:
            if not spec.get("optional"):
                problems.append("%s.%s -> 缺少必填字段" % (path, field))
            continue
        if data[field] is None and spec.get("optional"):
            continue
        _check_value("%s.%s" % (path, field), data[field], spec, problems)


def validate_accounts(module=A):
    """校验 accounts.py 的四个顶层结构。返回问题列表（空 = 通过）。"""
    p = []
    for key, acct in module.ACCOUNTS.items():
        _check_mapping("ACCOUNTS.%s" % key, acct, ACCOUNT_SCHEMA, p)
        for i, wid in enumerate(acct.get("works") or []):
            if wid not in module.WORKS:
                p.append("ACCOUNTS.%s.works[%d] -> 未定义的作品 id %r" % (key, i, wid))
        for skill in acct.get("skills") or []:
            if skill not in module.SKILL_LABELS:
                p.append("ACCOUNTS.%s.skills -> 未知技能 %r" % (key, skill))
        if acct.get("contrib") == "own" and key not in module.CONTRIB["own"]:
            p.append("ACCOUNTS.%s.contrib=own 但 CONTRIB.own 无该账号" % key)
    for wid, work in module.WORKS.items():
        _check_mapping("WORKS.%s" % wid, work, WORK_SCHEMA, p)
        for plat, link in (work.get("links") or {}).items():
            urls = [link] if isinstance(link, str) else link
            if not urls:
                p.append("WORKS.%s.links.%s -> 空链接列表" % (wid, plat))
            for i, url in enumerate(urls):
                if not str(url).startswith("http"):
                    p.append("WORKS.%s.links.%s[%d] -> 不是 URL: %r" % (wid, plat, i, url))
    for key in module.ACCOUNT_ORDER:
        if key not in module.ACCOUNTS:
            p.append("ACCOUNT_ORDER -> 引用了不存在的账号 %r" % key)
    if set(module.ACCOUNT_ORDER) != set(module.ACCOUNTS):
        p.append("ACCOUNT_ORDER -> 与 ACCOUNTS 的键集合不一致")
    return p


def _load_json(path):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def validate_stats(data):
    p = []
    if not isinstance(data, dict):
        return ["stats.json -> 顶层必须是对象"]
    if not str(data.get("as_of") or "").strip():
        p.append("stats.json.as_of -> 缺少快照日期")
    accounts = data.get("accounts")
    if not isinstance(accounts, dict):
        return p + ["stats.json.accounts -> 必须是对象"]
    for key, block in accounts.items():
        if key not in A.ACCOUNTS:
            p.append("stats.json.accounts.%s -> 未知账号" % key)
            continue
        _check_mapping("stats.json.accounts.%s" % key, block, STATS_BLOCK_SCHEMA, p)
    for key in A.ACCOUNT_ORDER:
        if key not in accounts:
            p.append("stats.json.accounts -> 缺少账号 %s" % key)
    return p


def validate_works(data):
    p = []
    if not isinstance(data, dict):
        return ["works.json -> 顶层必须是对象"]
    accounts = data.get("accounts")
    if not isinstance(accounts, dict):
        return p + ["works.json.accounts -> 必须是对象"]
    for key, block in accounts.items():
        if key not in A.ACCOUNTS:
            p.append("works.json.accounts.%s -> 未知账号" % key)
            continue
        if block.get("platform") != A.ACCOUNTS[key]["platform"]:
            p.append("works.json.accounts.%s.platform -> 与 accounts.py 不一致" % key)
        for i, repo in enumerate(block.get("repos") or []):
            path = "works.json.accounts.%s.repos[%d]" % (key, i)
            for field in ("name", "url"):
                if not str(repo.get(field) or "").strip():
                    p.append("%s.%s -> 不能为空" % (path, field))
            if "|" in str(repo.get("title") or ""):
                p.append("%s.title -> 含竖线会破坏 Markdown 表格" % path)
    return p


def validate_writing(data):
    p = []
    if not isinstance(data, dict):
        return ["writing.json -> 顶层必须是对象"]
    for i, item in enumerate(data.get("items") or []):
        _check_mapping("writing.json.items[%d]" % i, item, WRITING_ITEM_SCHEMA, p)
    return p


def validate_jsonschema(data, name):
    """可选：装了 jsonschema 时做第二遍结构校验。未安装则跳过。"""
    try:
        import jsonschema  # type: ignore
    except ImportError:
        return []
    schema = {
        "type": "object",
        "required": ["accounts"],
        "properties": {"accounts": {"type": "object"}},
    }
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as err:  # pragma: no cover - 依赖可选
        return ["%s -> jsonschema: %s" % (name, err.message)]
    return []


def validate_all(root=None):
    """全量校验：accounts.py + 三份 JSON 快照。返回问题列表。"""
    root = pathlib.Path(root) if root else ROOT
    problems = validate_accounts()
    stats = _load_json(root / "data" / "stats.json")
    works = _load_json(root / "data" / "works.json")
    writing = _load_json(root / "data" / "writing.json")
    if stats is None:
        problems.append("data/stats.json -> 无法读取")
    else:
        problems += validate_stats(stats)
        problems += validate_jsonschema(stats, "stats.json")
    if works is None:
        problems.append("data/works.json -> 无法读取")
    else:
        problems += validate_works(works)
        problems += validate_jsonschema(works, "works.json")
    if writing is None:
        problems.append("data/writing.json -> 无法读取")
    else:
        problems += validate_writing(writing)
    return problems


def assert_valid(root=None):
    problems = validate_all(root)
    if problems:
        raise SchemaError(problems)
