# -*- coding: utf-8 -*-
"""版本单一真源（Single Source of Truth）。

`VERSION` 是全仓唯一的版本号定义：README 徽章、CHANGELOG 校验、打包产物
（`profile.json` 的 `kit_version`）都从这里读取，不再各自硬编码。

语义化版本（SemVer 2.0.0）：
  主版本号 不兼容的产物/配置变更（README 结构或配置键破坏性改动）
  次版本号 向后兼容的新能力（新卡片、新模板、新配置项）
  修订号   向后兼容的修复（渲染错误、文档、性能）

升级时用 `python scripts/release.py --check` 校验 CHANGELOG 与版本一致。
"""

__all__ = ["VERSION", "VERSION_INFO", "KIT_NAME", "REPO_URL"]

KIT_NAME = "profile-kit"
REPO_URL = "https://github.com/badhope/badhope"

VERSION = "3.0.0"

VERSION_INFO = tuple(int(part) for part in VERSION.split("."))
