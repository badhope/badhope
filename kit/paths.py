# -*- coding: utf-8 -*-
"""仓库路径解析。所有模块共用，避免各自 parents[N] 漂移。"""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
