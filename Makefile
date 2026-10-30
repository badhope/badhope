# 主页面 kit —— 常用任务入口（全部纯 stdlib / node，无额外依赖）
PYTHON ?= python
NODE ?= node

.PHONY: help doctor verify test gen gen-if-changed preview pack links bench clean

help:
	@echo "make doctor    环境与数据体检（可选依赖 / schema / 构建状态 / 文件）"
	@echo "make verify    离线自检（数据 + 生成 + 资产引用 + 幂等）"
	@echo "make test      单元测试"
	@echo "make gen       按 profile.json 原地重建 README 与 SVG"
	@echo "make preview   生成 preview/ 与 dist/ 本地预览"
	@echo "make pack      打出可部署仓库树（ACCOUNT=gitcode_badhope）"
	@echo "make bench     性能基准（生成/增量/资产体积）"
	@echo "make links     在线校验 accounts.py 中的链接"
	@echo "make clean     清理 dist/ preview/ __pycache__"

doctor:
	$(PYTHON) scripts/doctor.py

verify:
	$(PYTHON) scripts/verify.py

test:
	$(PYTHON) -m unittest discover -s tests -v

gen:
	$(PYTHON) scripts/generate.py --here

# 增量：输入（accounts.py / data/*.json / profile.json）没变就一个字节都不写
gen-if-changed:
	$(PYTHON) scripts/generate.py --here --skip-if-unchanged

preview:
	$(PYTHON) scripts/generate.py --preview

pack:
	$(PYTHON) scripts/generate.py --pack $(or $(ACCOUNT),gitcode_badhope)

links:
	$(PYTHON) scripts/refresh.py --check-links

bench:
	$(PYTHON) scripts/bench.py

clean:
	rm -rf dist preview pack .tmp .cache .build-manifest.json
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
