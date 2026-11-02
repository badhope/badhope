# Security Policy

## 支持的版本

本项目产出静态资产，安全修复随最新主版本发布。

| 版本 | 支持 |
|---|---|
| 3.x | ✅ |
| 2.x | ❌ |

## 报告漏洞

**请不要开公开 issue。** 通过以下任一私有渠道报告：

- GitHub Security Advisories：仓库 `Security` 标签页 → `Report a vulnerability`
- 邮件：见仓库所有者 [@badhope](https://github.com/badhope) 的公开联系方式

请在报告里包含：受影响的版本或提交、复现步骤、影响范围（是否可泄露凭据 / 篡改产物）、
以及你希望的披露时间。

我们会在 7 天内确认收到，并在修复发布后于 CHANGELOG 中致谢（除非你要求匿名）。

## 设计层面已采取的措施

这个项目**没有运行期服务**，攻击面主要是构建链路与凭据处理：

- **凭据不落盘、不进 URL**。镜像与刷新使用 `GIT_ASKPASS` 传递令牌；
  令牌只从环境变量或 `~/.agent-secrets/` 读取，不写入仓库、日志或快照。
- **仓库内无密钥**。CI 跑 `gitleaks`，配置见 `.gitleaks.toml`。
- **外部文本一律转义**。仓库名、描述等外部输入进入 SVG 前经 `esc()` 处理，
  避免 SVG 注入；`tests/test_extras.py` 有对应断言。
- **快照写入原子化**。产物经临时文件 + `os.replace`，中断不会留下半截文件。
- **镜像只同步账号无关层**。`scripts/mirror-shared.sh` 使用固定清单，
  避免把源账号资产覆盖到目标仓库。

## 已知的信任边界

- 本项目会抓取第三方平台（GitHub / GitCode / Gitee / WakaTime）的公开数据。
  这些数据被视为**不可信输入**，只在渲染前做转义，不做代码执行。
- `scripts/refresh*.py` 需要网络与平台凭据，属于受信执行环境；
  不要在不可信的 CI 上运行带写权限令牌的刷新任务。
