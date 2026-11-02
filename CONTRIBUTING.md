# Contributing to profile-kit

感谢你愿意改进这个项目。它是一台**静态 profile 资产编译器**：把账号配置与数据快照
编译成 README 与 SVG 资产。所有产出都是 git 里的字节，没有运行期服务。

开始前请先读 [`ARCHITECTURE.md`](ARCHITECTURE.md) 的分层说明——它会告诉你改动应该落在哪一层。

## 开发环境

| 依赖 | 版本 | 说明 |
|---|---|---|
| Python | 3.10+ | 核心只吃标准库，无第三方运行时依赖 |
| Node.js | 18+ | 仅 `scripts/render_cards.mjs` 需要（可选） |
| Chromium 系浏览器 | 任意近期版本 | 仅 `scripts/rasterize.py` 生成 hero PNG 时需要（可选） |

```bash
git clone https://github.com/badhope/badhope.git
cd badhope
python -m unittest discover -s tests -v   # 全部单元测试
python scripts/verify.py                  # 离线门禁
python scripts/doctor.py                  # 环境与数据体检
```

可选增强依赖（不装会自动降级，`doctor.py` 会标注当前走哪条路径）：

```bash
python -m pip install -r requirements-optional.txt
```

## 改动流程

1. **先跑基线**：`make test && make verify`，确认起点是绿的。
2. **小步提交**：一个提交只做一件事，提交信息用祈使句（`fix:` / `feat:` / `docs:`）。
3. **补测试**：新增行为要有断言；修复缺陷要有回归测试（先红后绿）。
4. **保持产物可复现**：任何让渲染结果依赖时间、网络或环境的改动都会被拒绝。
   验证方式是连续两次 `python scripts/generate.py --here` 后 `git status` 为空。
5. **更新文档**：用户可见变更写进 `CHANGELOG.md` 的 `[Unreleased]`。

## 硬性约束

这几条是项目定位的一部分，不接受"优化"：

- **渲染期禁止联网**。所有外部数据必须先落进 `data/*.json` 快照。
  `scripts/refresh*.py` 是唯一允许发起网络请求的地方。
- **产物必须字节级可复现**。不得写入时间戳、随机数（除非用 CRC32 账号种子）、
  绝对路径或构建机器信息。
- **单卡失败不得炸掉整体构建**。卡片插件应返回 `None`（跳过）或由注册表兜底为占位卡。
- **账号之间不得串号**。跨账号共享目录里不得使用全局 `assets/` 判断产物存在性。
- **不加运行时依赖**。需要新能力时优先标准库实现；确有必要则放进
  `requirements-optional.txt` 并保留降级路径。

## 新增一张卡片

```python
# kit/cards.py —— 写渲染函数，返回 SVG 字符串或 None
def mycard_svg(acct, lang, theme=None):
    ...

# kit/cardset.py —— 一行注册，build.py / verify.py / pack.py 都不用改
@card("mycard", "mycard-{lang}.svg", priority=110,
      when=lambda acct, ctx: bool(ctx.get("stats")))
def _mycard(acct, key, lang, ctx):
    return mycard_svg(acct, lang, theme=ctx["theme"])
```

若要在 README 里展示，再到 `kit/readme.py` 对应 section 加 `<img>` 引用。
注册后 `verify.py` 会自动枚举并校验文件名唯一性与资产引用。

## 提交信息格式

```
<type>(<scope>): <祈使句摘要>

<为什么这样改，而不是改了什么——diff 已经说明改了什么>
```

`type` 取值：`feat` / `fix` / `docs` / `refactor` / `perf` / `test` / `build` / `chore`。

## 报告问题

- 缺陷：请附上复现命令、`python scripts/doctor.py` 输出、以及期望与实际结果的差异。
- 安全问题：不要开公开 issue，见 [`SECURITY.md`](SECURITY.md)。

## 许可

提交的贡献按 [MIT](LICENSE) 授权。
