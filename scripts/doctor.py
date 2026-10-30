# -*- coding: utf-8 -*-
"""环境与数据体检：一条命令回答「这台机器现在能不能正常构建/刷新」。

    python -m kit doctor
    python scripts/doctor.py

检查项：
- Python 版本、可选依赖是否可用（可用=走增强路径，不可用=降级但功能不减）
- accounts.py / data/*.json 的 schema 校验
- 产物是否与数据一致（输入指纹 vs manifest）
- 仓库关键文件是否齐全
- 网络可用性（可选：--online 时探测各平台 API）

输出分级：OK / WARN / FAIL。有 FAIL 时退出码 1。
"""

import importlib.util
import json
import pathlib
import platform
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import accounts as A  # noqa: E402
from kit.build import current_manifest, input_digest  # noqa: E402
from kit.plugins import describe as describe_plugins  # noqa: E402
from kit.schema import validate_all  # noqa: E402

OK, WARN, FAIL = "OK", "WARN", "FAIL"


def _check(results, level, name, detail=""):
    results.append((level, name, detail))
    icon = {OK: "✓", WARN: "!", FAIL: "×"}[level]
    print("  [%s] %-34s %s" % (icon, name, detail))


def check_runtime(results):
    major, minor = sys.version_info[:2]
    _check(results, OK if (major, minor) >= (3, 10) else FAIL,
           "Python", "%d.%d.%d (%s)" % (major, minor, sys.version_info[2], platform.system()))
    optional = {"httpx": "HTTP/2 + 连接池", "markdown_it": "CommonMark 渲染",
                "jsonschema": "第二遍结构校验", "PIL": "PNG 优化增强"}
    for mod, purpose in optional.items():
        present = importlib.util.find_spec(mod) is not None
        _check(results, OK if present else WARN,
               "optional: %s" % mod,
               "已安装 → %s" % purpose if present else "未安装 → 内置降级路径（功能不减）")


def check_data(results):
    problems = validate_all(ROOT)
    if problems:
        for problem in problems[:8]:
            _check(results, FAIL, "schema", problem)
        if len(problems) > 8:
            _check(results, FAIL, "schema", "还有 %d 条未显示" % (len(problems) - 8))
    else:
        _check(results, OK, "schema", "accounts + 3 份 JSON 快照全部通过")
    specs = describe_plugins()
    _check(results, OK if specs else FAIL, "card plugins", "%d 个：%s"
           % (len(specs), ", ".join(s["name"] for s in specs)))


def check_build_state(results):
    manifest = current_manifest(ROOT)
    if not manifest:
        _check(results, WARN, "build manifest", "尚未构建过（运行 make gen）")
        return
    same = manifest.get("input_digest") == input_digest(ROOT)
    _check(results, OK if same else WARN, "build manifest",
           "输入未变，产物是最新的" if same else "输入已变化，需要重新构建")


def check_files(results):
    required = ["accounts.py", "profile.json", "data/stats.json", "data/works.json",
                "data/writing.json", "README.md", "README.zh-CN.md", "README.ja.md",
                "kit/build.py", "scripts/generate.py", "scripts/verify.py"]
    missing = [rel for rel in required if not (ROOT / rel).is_file()]
    _check(results, OK if not missing else FAIL, "required files",
           "全部存在（%d）" % len(required) if not missing else "缺失：%s" % ", ".join(missing))


def check_online(results):
    from kit.net import HttpClient, HttpError
    probes = [
        ("GitHub API", "https://api.github.com/users/badhope"),
        ("Gitee API", "https://gitee.com/api/v5/users/badhope"),
        ("GitCode API", "https://api.gitcode.com/api/v5/users/badhope?access_token=%s"
         % __import__("os").environ.get("GITCODE_TOKEN", "")),
    ]
    with HttpClient(cache=False, timeout=10, max_retries=0) as client:
        for name, url in probes:
            try:
                client.get(url)
                _check(results, OK, name, "可达")
            except HttpError as err:
                _check(results, WARN, name, "HTTP %s（限流或权限，不影响离线构建）" % err.status)
            except OSError as err:
                _check(results, WARN, name, "%s" % type(err).__name__)


def main(argv=None):
    online = "--online" in (argv if argv is not None else sys.argv[1:])
    print("profile kit · doctor")
    print("repo: %s" % ROOT)
    results = []
    print("\n[runtime]")
    check_runtime(results)
    print("\n[data]")
    check_data(results)
    print("\n[build state]")
    check_build_state(results)
    print("\n[files]")
    check_files(results)
    if online:
        print("\n[network]")
        check_online(results)
    failures = sum(1 for level, _, _ in results if level == FAIL)
    warnings = sum(1 for level, _, _ in results if level == WARN)
    print("\nsummary: %d checks, %d warn, %d fail" % (len(results), warnings, failures))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
