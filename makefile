# Makefile - ShopnoOS Build
SHELL := /usr/bin/env bash

.PHONY: build clean help

help:
	@echo "Usage:"
	@echo "  make build 	Build ShopnoOS ISO"
	@echo "  make clean 	Remove build artifacts"

build:
	@echo "[MAKE] Building iso..."
	@sudo ./build.sh

clean:
	@echo "[MAKE] Cleaning build artifacts..."
	@sudo rm -rf build/
	@echo "[MAKE] Clean complete."
