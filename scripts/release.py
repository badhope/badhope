#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发版校验与打 tag 辅助。

`--check` 校验三件事，任一不满足即非零退出（可直接作为 CI 门禁）：
  1. `kit/version.py` 的 VERSION 在 CHANGELOG 里有对应的 `## [x.y.z]` 条目；
  2. 该条目的日期存在且格式为 YYYY-MM-DD；
  3. 工作树干净（发版提交必须自洽，不能带着未提交改动打 tag）。

`--tag` 在 --check 通过后创建附注 tag（默认 v<VERSION>）。
不推送——推送由调用方决定，避免脚本隐式改动远端。
"""

import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from kit.version import VERSION  # noqa: E402

CHANGELOG = ROOT / "CHANGELOG.md"
_HEADING_RE = re.compile(r"^## \[(?P<version>\d+\.\d+\.\d+)\](?: - (?P<date>\S+))?", re.M)


def changelog_versions(text):
    return [(m.group("version"), m.group("date")) for m in _HEADING_RE.finditer(text)]


def check():
    problems = []
    if not CHANGELOG.is_file():
        return ["CHANGELOG.md 不存在"]
    entries = changelog_versions(CHANGELOG.read_text(encoding="utf-8"))
    matching = [date for version, date in entries if version == VERSION]
    if not matching:
        problems.append("CHANGELOG 缺少 [%s] 条目（现有：%s）"
                        % (VERSION, ", ".join(v for v, _ in entries) or "无"))
    else:
        date = matching[0]
        if not date:
            problems.append("[%s] 条目缺少日期，应写成 `## [%s] - YYYY-MM-DD`" % (VERSION, VERSION))
        else:
            try:
                datetime.date.fromisoformat(date)
            except ValueError:
                problems.append("[%s] 的日期 %r 不是 YYYY-MM-DD" % (VERSION, date))
    # profile.json 的 kit_version 是部署身份的一部分，必须与单一真源一致，
    # 否则镜像仓库会声称自己是旧版本。
    profile = ROOT / "profile.json"
    if profile.is_file():
        try:
            declared = json.loads(profile.read_text(encoding="utf-8")).get("kit_version")
        except ValueError:
            problems.append("profile.json 不是合法 JSON")
        else:
            if declared != VERSION:
                problems.append("profile.json 的 kit_version 是 %r，应为 %r"
                                % (declared, VERSION))
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    if dirty:
        problems.append("工作树不干净，先提交再发版：\n%s" % dirty)
    return problems


def create_tag(name=None):
    tag = name or "v%s" % VERSION
    existing = subprocess.run(["git", "tag", "-l", tag], cwd=ROOT,
                              capture_output=True, text=True).stdout.strip()
    if existing:
        return ["tag %s 已存在" % tag]
    result = subprocess.run(["git", "tag", "-a", tag, "-m", "Release %s" % VERSION],
                            cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        return [(result.stderr or result.stdout).strip()]
    print("tagged %s at %s" % (tag, VERSION))
    return []


def main(argv=None):
    parser = argparse.ArgumentParser(description="verify release metadata")
    parser.add_argument("--check", action="store_true", help="校验版本号与 CHANGELOG 一致")
    parser.add_argument("--tag", nargs="?", const="", metavar="NAME", help="校验通过后打附注 tag")
    args = parser.parse_args(argv)
    if not args.check and args.tag is None:
        parser.print_help()
        return 2

    problems = check()
    if problems:
        print("release check FAILED (%s)" % VERSION)
        for item in problems:
            print("  - %s" % item)
        return 1
    print("release check OK (%s)" % VERSION)
    if args.tag is not None:
        tag_problems = create_tag(args.tag or None)
        if tag_problems:
            for item in tag_problems:
                print("  - %s" % item)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
