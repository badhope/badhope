#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline verification gate.

1. regenerating into a scratch dir reproduces the committed tree byte for byte
2. every asset referenced by a README exists
3. no cross-platform leakage (github READMEs never link the mirrors, mirrors
   never link the github profile)
"""

import filecmp
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build  # noqa: E402
from scripts.generate import build_out  # noqa: E402

PLATFORM_MARKS = {
    "gh_badhope": ("gitcode.com/badhope", "gitee.com/badhope"),
    "gitcode_badhope": ("gitee.com/badhope",),
    "gitee_badhope": ("gitcode.com/badhope",),
}


def check_reproducible(tmp):
    account = build.current_account()
    outputs = build_out(tmp, account)
    for name in outputs:
        generated = tmp / name
        committed = ROOT / name
        if not committed.exists():
            print("FAIL missing committed file: %s" % name)
            return False
        if not filecmp.cmp(generated, committed, shallow=False):
            print("FAIL stale generated file: %s (run `make gen`)" % name)
            return False
    # assets referenced by the committed READMEs must exist
    for name in outputs:
        text = (ROOT / name).read_text(encoding="utf-8")
        for token in text.replace('"', " ").replace(")", " ").split():
            if token.startswith("assets/") and token.endswith(".svg"):
                if not (ROOT / token).exists():
                    print("FAIL asset referenced but missing: %s" % token)
                    return False
    return True


def check_isolation(tmp):
    account = build.current_account()
    for foreign in PLATFORM_MARKS[account]:
        for name in ("README.md", "README.zh-CN.md", "README.ja.md"):
            path = ROOT / name
            if not path.exists():
                continue
            if foreign in path.read_text(encoding="utf-8"):
                print("FAIL %s leaks %s" % (name, foreign))
                return False
    return True


def main():
    ok = True
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="verify-"))
    try:
        ok &= check_reproducible(tmp)
        ok &= check_isolation(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not ok:
        print("verify: FAILED")
        return 1
    print("verify: ok (reproducible, assets present, no cross-platform leakage)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
