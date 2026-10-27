.PHONY: build assets install audit clean demo

build:
	./scripts/build.sh

assets:
	python3 scripts/build_assets.py

install:
	./scripts/install.sh

audit:
	python3 audit/audit.py

release:
	./scripts/package.sh

demo:
	./bin/dafeiyu demo

clean:
	rm -rf .build bin/__pycache__ audit/last-report.json
