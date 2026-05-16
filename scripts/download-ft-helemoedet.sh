#!/usr/bin/env bash
# Download helemoedet XML files from the Folketing Open Data FTP server.
#
# Usage:
#   ./download-ft-helemoedet.sh <output_dir> [options] [session...]
#
# Arguments:
#   <output_dir>   Directory to write files into (required).
#                  Session files land at <output_dir>/<session>/<file>.xml
#
# Options:
#   -h, --help     Show this help and exit.
#
# Examples:
#   # Download everything not yet present into ./_data/
#   ./download-ft-helemoedet.sh ./_data
#
#   # Download only two specific sessions
#   ./download-ft-helemoedet.sh ./_data 20241 20251
#

set -euo pipefail

FTP_BASE="ftp://oda.ft.dk/ODAXML/Referat/samling"
OUT_DIR=""
sessions=()

# ── Argument parsing ──────────────────────────────────────────────────────────
usage() {
    grep '^#' "$0" | sed 's/^# \{0,1\}//'
    exit 0
}

if [[ $# -eq 0 ]]; then
    echo "Error: <output_dir> is required." >&2
    echo "Run with --help for usage." >&2
    exit 1
fi

# First positional arg is always the output dir
OUT_DIR="$1"
shift

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)  usage ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            sessions+=("$1")
            ;;
    esac
    shift
done

# ── Resolve session list ──────────────────────────────────────────────────────
if [[ ${#sessions[@]} -eq 0 ]]; then
    echo "Fetching session list from FTP..."
    while IFS= read -r line; do sessions+=("$line"); done < <(curl -s --list-only "${FTP_BASE}/")
fi

mkdir -p "${OUT_DIR}"

echo "Output directory : ${OUT_DIR}"
echo "Sessions         : ${sessions[*]}"

total_sessions=${#sessions[@]}
total_downloaded=0
total_skipped=0

# ── Progress display ──────────────────────────────────────────────────────────
# Renders: "... 20101 20102 ▶ 20111 20121 20131 ..."
#           (done sessions) ▶ (current + upcoming, windowed)
build_session_bar() {
    local curr_idx=$1
    local window=3
    local lo=$(( curr_idx - window ))
    local hi=$(( curr_idx + window + 1 ))
    [[ $lo -lt 0 ]] && lo=0
    [[ $hi -gt $total_sessions ]] && hi=$total_sessions

    local bar=""
    [[ $lo -gt 0 ]] && bar="... "
    for (( i=lo; i<curr_idx; i++ )); do bar+="${sessions[$i]} "; done
    bar+="▶ "
    for (( i=curr_idx; i<hi; i++ )); do bar+="${sessions[$i]} "; done
    [[ $hi -lt $total_sessions ]] && bar+="..."
    printf "%s" "$bar"
}

# Reserve 3 lines for the live display (blank gap + session bar + file progress)
printf "\n\n\n"

print_progress() {
    local sess_idx=$1 file_idx=$2 total_files=$3 action=$4 filename=$5
    local bar; bar=$(build_session_bar "$sess_idx")
    printf "\033[3A"
    printf "\033[2K\r\n"
    printf "\033[2K\r  %s\n" "$bar"
    printf "\033[2K\r  [%d/%d] %s %s\n" "$file_idx" "$total_files" "$action" "$filename"
}

# ── Download ──────────────────────────────────────────────────────────────────
sess_idx=0
for session in "${sessions[@]}"; do
    session_dir="${OUT_DIR}/${session}"
    mkdir -p "${session_dir}"

    files=()
    while IFS= read -r line; do files+=("$line"); done < <(curl -s --list-only "${FTP_BASE}/${session}/")

    if [[ ${#files[@]} -eq 0 ]]; then
        (( sess_idx++ )) || true
        continue
    fi

    session_downloaded=0
    session_skipped=0
    total_files=${#files[@]}
    file_idx=0

    for filename in "${files[@]}"; do
        (( file_idx++ )) || true
        dest="${session_dir}/${filename}"

        if [[ -f "${dest}" ]]; then
            (( session_skipped++ )) || true
            print_progress "$sess_idx" "$file_idx" "$total_files" "·" "$filename"
            continue
        fi

        print_progress "$sess_idx" "$file_idx" "$total_files" "↓" "$filename"
        curl -s --retry 3 --retry-delay 2 \
            -o "${dest}" \
            "${FTP_BASE}/${session}/${filename}"
        (( session_downloaded++ )) || true
    done

    (( total_downloaded += session_downloaded )) || true
    (( total_skipped    += session_skipped    )) || true
    (( sess_idx++ )) || true
done

# Clear the 2-line progress area and print final summary
printf "\033[3A\033[2K\r\n\033[2K\rDone.  Sessions: %d  Downloaded: %d  Skipped: %d\n\033[2K\r" \
    "$total_sessions" "$total_downloaded" "$total_skipped"
