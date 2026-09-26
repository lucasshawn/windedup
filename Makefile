.PHONY: test build run

test:
	python -m unittest discover tests -v

build:
	pyinstaller --noconsole --onefile --name "Windedup" --icon="assets/icon.ico" --add-data="assets;assets" main.py

run:
	python main.py
