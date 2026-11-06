# Profile page — common tasks (stdlib only, no extra dependencies)
PYTHON ?= python3

.PHONY: help doctor verify test gen gen-if-changed release clean

help:
	@echo "make doctor    environment and data sanity check"
	@echo "make verify    offline gate: reproducibility, asset refs, isolation"
	@echo "make test      unit tests"
	@echo "make gen       rebuild README + every SVG from build.py"
	@echo "make release   check profile.json version against CHANGELOG"
	@echo "make clean     remove __pycache__ and fingerprints"

doctor:
	$(PYTHON) scripts/doctor.py

verify:
	$(PYTHON) scripts/verify.py

test:
	$(PYTHON) -m unittest discover -s tests -v

gen:
	$(PYTHON) scripts/generate.py --here

gen-if-changed:
	$(PYTHON) scripts/generate.py --here --skip-if-unchanged

release:
	$(PYTHON) scripts/release.py --check

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -f .build-fingerprint
