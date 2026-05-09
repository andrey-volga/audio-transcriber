#!/bin/bash
# Запуск audio-transcriber watch с параметрами
# Использование:
#   ./watch.sh                           # использует default_source из конфига
#   ./watch.sh ~/input                   # мониторит ~/input
#   ./watch.sh ~/input --model small     # с моделью small

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# Если аргументов нет, показываем справку
if [[ $# -eq 0 ]]; then
    echo "Использование: $0 [SOURCE] [OPTIONS]"
    echo ""
    echo "Примеры:"
    echo "  $0 ~/input"
    echo "  $0 ~/input --model small"
    echo "  $0 ~/input --lang en"
    echo ""
    echo "Доступные опции:"
    uv run transcribe watch --help
    exit 0
fi

uv run transcribe watch "$@"
