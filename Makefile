.PHONY: test build run

test:
	python -m unittest discover tests -v

build:
	python -c "import datetime; open('windedup/_build_info.py', 'w').write(f'BUILD_TIMESTAMP = \"{datetime.datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}\"\n')"
	-powershell -Command "Stop-Process -Name 'Windedup' -Force -ErrorAction SilentlyContinue; exit 0"
	pyinstaller Windedup.spec --noconfirm

run:
	python main.py
