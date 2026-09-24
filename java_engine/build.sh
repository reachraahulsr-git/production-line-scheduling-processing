#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
SRC_DIR="$DIR/src"
BIN_DIR="$DIR/bin"

mkdir -p "$BIN_DIR"

echo "Compiling Java Multithreaded Production Processing Module..."
javac -d "$BIN_DIR" $(find "$SRC_DIR" -name "*.java")

echo "Java compilation successful! Binaries stored in $BIN_DIR"
