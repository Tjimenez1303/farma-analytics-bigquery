#!/bin/bash
# Prose linter for reader-facing docs (constitution, principle IX).
# Usage: lint_prosa.sh [PATH...]   (no args: default scope, "-": read stdin)
# Compatible with bash 3.2 (macOS default). Uses ripgrep's default regex engine.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
MULETILLAS="${LINT_PROSA_MULETILLAS:-$REPO_ROOT/scripts/muletillas.txt}"
EXCEPTIONS="$REPO_ROOT/scripts/prosa_excepciones.txt"

if ! command -v rg >/dev/null 2>&1; then
  echo "lint_prosa: falta ripgrep (rg)." >&2
  exit 2
fi
if [ ! -f "$MULETILLAS" ]; then
  echo "lint_prosa: no existe la lista de muletillas $MULETILLAS" >&2
  exit 2
fi

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# Lines of one section of the exceptions file.
section() {
  awk -v want="[$1]" '
    /^\[.*\]$/ { cur = $0; next }
    cur == want && $0 !~ /^#/ && NF > 0 { print }
  ' "$EXCEPTIONS"
}
LP_TERMS=$(section terminos | tr '[:upper:]' '[:lower:]')
LP_PROPER=$(section nombres_propios)
export LP_TERMS LP_PROPER

# Filler list split into literal phrases and regexes.
grep -v '^#' "$MULETILLAS" | grep -v '^re:' | sed '/^[[:space:]]*$/d' > "$WORK/literal.txt"
sed -n 's/^re://p' "$MULETILLAS" > "$WORK/regex.txt"

is_excluded() {
  case "$1" in
    specs/* | */specs/* | specs | .specify/* | */.specify/* | .specify) return 0 ;;
  esac
  case "$(basename "$1")" in
    muletillas.txt | prosa_excepciones.txt | .bigqueryrc | .sqlfluff) return 0 ;;
    *.yaml | *.yml | *.toml | *.json | *.env) return 0 ;;
  esac
  return 1
}

FILES="$WORK/files.txt"
: > "$FILES"

add_file() {
  local path=$1
  is_excluded "$path" && return
  case "$path" in
    *.md | *.txt | *.sql) printf '%s\n' "$path" >> "$FILES" ;;
    *) echo "lint_prosa: se ignora $path (solo .md, .txt y .sql)" >&2 ;;
  esac
}

add_dir() {
  is_excluded "$1" && return
  find "$1" -type f \( -name '*.md' -o -name '*.txt' -o -name '*.sql' \) | sort | while read -r f; do
    add_file "$f"
  done
}

if [ $# -eq 0 ]; then
  cd "$REPO_ROOT" || exit 2
  [ -f README.md ] && add_file README.md
  [ -d docs ] && add_dir docs
  [ -d sql ] && add_dir sql
else
  for arg in "$@"; do
    if [ "$arg" = "-" ]; then
      cat > "$WORK/stdin.md"
      printf '%s\n' "<stdin>" >> "$FILES"
    elif [ -d "$arg" ]; then
      add_dir "${arg%/}"
    elif [ -f "$arg" ]; then
      add_file "$arg"
    else
      echo "lint_prosa: no existe $arg" >&2
      exit 2
    fi
  done
fi

# Keep only SQL comments, line by line.
sql_comments() {
  awk '
    {
      line = $0; out = ""
      while (length(line) > 0) {
        if (inblock) {
          e = index(line, "*/")
          if (e) { out = out " " substr(line, 1, e - 1); line = substr(line, e + 2); inblock = 0 }
          else { out = out " " line; line = "" }
        } else {
          d = index(line, "--"); b = index(line, "/*")
          if (d && (!b || d < b)) { out = out " " substr(line, d + 2); line = "" }
          else if (b) { line = substr(line, b + 2); inblock = 1 }
          else { line = "" }
        }
      }
      print out
    }
  '
}

# Blank code, ignored lines, URLs and allowed terms while keeping line numbers.
clean_prose() {
  awk '
    BEGIN { n = split(ENVIRON["LP_TERMS"], terms, "\n") }
    /^[ \t]*(```|~~~)/ { fence = !fence; print ""; next }
    fence { print ""; next }
    index($0, "lint-prosa: ignorar") { print ""; next }
    {
      line = $0
      gsub(/`[^`]*`/, "", line)
      gsub(/<!--.*-->/, "", line)
      gsub(/https?:\/\/[^ )>\]]*/, "", line)
      gsub(/\]\([^)]*\)/, "]", line)
      for (i = 1; i <= n; i++) {
        if (terms[i] == "") continue
        while ((p = index(tolower(line), terms[i])) > 0)
          line = substr(line, 1, p - 1) " " substr(line, p + length(terms[i]))
      }
      print line
    }
  '
}

# Headings with capitalized words that are not acronyms or proper nouns.
title_case() {
  awk '
    BEGIN {
      n = split(ENVIRON["LP_PROPER"], words, "\n")
      for (i = 1; i <= n; i++) proper[words[i]] = 1
      split("Á É Í Ó Ú Ñ", acc, " ")
    }
    /^#+[ \t]/ {
      text = $0; sub(/^#+[ \t]+/, "", text)
      count = split(text, w, /[ \t]+/)
      for (i = 2; i <= count; i++) {
        word = w[i]
        gsub(/^[(¿¡"«]+|[).,:;?!"»]+$/, "", word)
        if (word == "" || (word in proper)) continue
        first = substr(word, 1, 1); rest = substr(word, 2); up = (first ~ /[A-Z]/)
        for (a in acc) if (substr(word, 1, 2) == acc[a]) { up = 1; rest = substr(word, 3) }
        if (!up || rest ~ /[A-Z]/ || rest == "") continue
        printf "%d\ttitle-case\t%s\n", NR, text
        break
      }
    }
  '
}

# Run ripgrep and emit "LINE<TAB>CATEGORY<TAB>FRAGMENT" (one mark per line and category).
search() {
  local category=$1 file=$2
  shift 2
  rg --no-filename --line-number --only-matching --no-heading "$@" "$file" 2>/dev/null |
    while IFS= read -r hit; do
      printf '%s\t%s\t%s\n' "${hit%%:*}" "$category" "${hit#*:}"
    done
}

TOTAL=0
WITH_MARKS=0
idx=0
while IFS= read -r display; do
  idx=$((idx + 1))
  if [ "$display" = "<stdin>" ]; then src="$WORK/stdin.md"; else src="$display"; fi
  clean="$WORK/clean_$idx.txt"
  case "$display" in
    *.sql) sql_comments < "$src" | clean_prose > "$clean" ;;
    *) clean_prose < "$src" > "$clean" ;;
  esac

  results="$WORK/results_$idx.txt"
  {
    search resto-de-herramienta "$src" -i -e 'oaicite|contentReference|utm_source=chatgpt\.com|turn0search|\[insertar[^\]]*\]'
    search raya "$clean" -e '[—–]'
    search guion-como-raya "$clean" -e '[^\s] - [^\s]'
    search punto-y-coma "$clean" -e ';'
    search emoji "$clean" -e '\p{Extended_Pictographic}'
    search flecha-o-caja "$clean" -e '[→←⇒⇐↑↓•★]|[\x{2500}-\x{257F}]'
    search comillas-curvas "$clean" -e '[“”‘’]'
    search negrita-con-dos-puntos "$clean" -e '^\s*([-*+]|[0-9]+\.)\s+\*\*[^*]+(:\*\*|\*\*\s*:)'
    title_case < "$clean"
    if [ -s "$WORK/literal.txt" ]; then
      search muletilla "$clean" -i -w -F -f "$WORK/literal.txt"
    fi
    if [ -s "$WORK/regex.txt" ]; then
      search muletilla "$clean" -i -f "$WORK/regex.txt"
    fi
  } | sort -t "$(printf '\t')" -k1,1n -s | awk -F '\t' '!seen[$1 FS $2]++' > "$results"

  count=$(grep -c . "$results" || true)
  if [ "$count" -gt 0 ]; then
    TOTAL=$((TOTAL + count))
    WITH_MARKS=$((WITH_MARKS + 1))
    while IFS="$(printf '\t')" read -r line category fragment; do
      printf '%s:%s: %s: %s\n' "$display" "$line" "$category" "$fragment"
    done < "$results"
  fi
done < "$FILES"

echo "$TOTAL marcas en $WITH_MARKS de $idx archivos revisados" >&2
[ "$TOTAL" -eq 0 ]
