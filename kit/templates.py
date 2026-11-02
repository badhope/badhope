# -*- coding: utf-8 -*-
"""README 模板预设：只调整区块顺序与可选区块开关，不改变卡片内容。

默认 `classic` 与历史输出一致；未知模板回退 classic，避免配置错误破坏页面。
"""

DEFAULT_ORDER = (
    "about", "skills", "works", "numbers", "achievements",
    "pinned", "writing", "elsewhere",
)

TEMPLATES = {
    "classic": {
        "order": DEFAULT_ORDER,
        "hide": (),
    },
    "compact": {
        "order": (
            "about", "works", "skills", "numbers", "writing",
            "achievements", "pinned", "elsewhere",
        ),
        "hide": (),
    },
    "minimal": {
        "order": ("about", "works", "writing", "elsewhere"),
        "hide": ("skills", "numbers", "achievements", "pinned"),
    },
    "portfolio": {
        "order": (
            "about", "works", "pinned", "skills", "writing",
            "achievements", "numbers", "elsewhere",
        ),
        "hide": (),
    },
}


def resolve(acct):
    name = str((acct or {}).get("template") or "").strip().lower()
    return {"name": name if name in TEMPLATES else "classic", **TEMPLATES.get(name, TEMPLATES["classic"])}


def section_order(acct):
    return list(resolve(acct)["order"])


def apply(lines, acct, headings):
    """Apply section ordering/hiding to a rendered README line list.

    `headings` maps internal section names to their rendered `## ` heading text.
    Only sections that appear as standalone `## ` blocks are moved; the About/Now
    table stays fixed at the top. Default `classic` returns the input unchanged.
    """
    spec = resolve(acct)
    if spec["name"] == "classic":
        return lines
    prefixes = {"## %s" % text: section for section, text in headings.items()}
    blocks = {}
    order = []
    current = None
    for line in lines:
        section = prefixes.get(line)
        if section:
            current = section
            if section in spec["hide"]:
                continue
            blocks[section] = [line]
            order.append(section)
        elif current is not None and line.startswith("## "):
            current = None
            blocks.setdefault("_tail", []).append(line)
        elif current is not None:
            if current not in spec["hide"]:
                blocks[current].append(line)
        else:
            blocks.setdefault("_head", []).append(line)
    if not order:
        return lines
    tail = blocks.get("_tail", [])
    head = blocks.get("_head", [])
    result = list(head)
    for section in spec["order"]:
        if section in blocks:
            result.extend(blocks[section])
    for section in order:
        if section not in spec["order"]:
            result.extend(blocks[section])
    result.extend(tail)
    return result
