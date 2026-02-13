#!/usr/bin/env bash
# Requires bash 3.2+ (macOS compatible — no associative arrays)
#
# run_full_sweep.sh — Run the full eval suite across all local Ollama models.
#
# Usage:
#   ./scripts/run_full_sweep.sh                  # full suite, all models
#   ./scripts/run_full_sweep.sh --suite smoke     # specific suite, all models
#   ./scripts/run_full_sweep.sh --models "llama3 gemma3:4b"  # full suite, specific models
#
# Results are saved to results/<timestamp>/ as log + JSON files.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Defaults ──
SUITE="full"
MODELS=""
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
RESULTS_DIR=""
SKIP_MULTIMODAL=true

# ── Parse args ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --suite)      SUITE="$2"; shift 2 ;;
        --models)     MODELS="$2"; shift 2 ;;
        --results-dir) RESULTS_DIR="$2"; shift 2 ;;
        --include-multimodal) SKIP_MULTIMODAL=false; shift ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --suite NAME           Eval suite to run (default: full)"
            echo "  --models \"m1 m2\"       Space-separated model list (default: all local)"
            echo "  --results-dir DIR      Output directory (default: results/<timestamp>)"
            echo "  --include-multimodal   Include multimodal/vision models (skipped by default)"
            echo "  -h, --help             Show this help"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Timestamp for this sweep ──
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
RESULTS_DIR="${RESULTS_DIR:-$PROJECT_DIR/results/$TIMESTAMP}"
mkdir -p "$RESULTS_DIR"

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

log()  { echo -e "${CYAN}[sweep]${RESET} $*"; }
ok()   { echo -e "${GREEN}  ✓${RESET} $*"; }
fail() { echo -e "${RED}  ✗${RESET} $*"; }
warn() { echo -e "${YELLOW}  !${RESET} $*"; }

# ── Preflight checks ──
log "Checking Ollama at ${OLLAMA_HOST}..."
if ! curl -sf "${OLLAMA_HOST}/" >/dev/null 2>&1; then
    fail "Ollama is not reachable at ${OLLAMA_HOST}"
    echo "  Start Ollama first: ollama serve"
    exit 2
fi
ok "Ollama is running"

# ── Discover models ──
if [[ -n "$MODELS" ]]; then
    IFS=' ' read -ra MODEL_LIST <<< "$MODELS"
else
    log "Discovering local Ollama models..."
    MODEL_LIST=()
    while IFS= read -r line; do
        MODEL_LIST+=("$line")
    done < <(
        curl -sf "${OLLAMA_HOST}/api/tags" \
        | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    print(m['name'])
" | sort
    )
fi

# ── Optionally filter out multimodal/vision models ──
VISION_PATTERNS="llava|vision|moondream|bakllava|cogvlm|images"
FILTERED_LIST=()
SKIPPED_LIST=()

for model in "${MODEL_LIST[@]}"; do
    if $SKIP_MULTIMODAL && echo "$model" | grep -qiE "$VISION_PATTERNS"; then
        SKIPPED_LIST+=("$model")
    else
        FILTERED_LIST+=("$model")
    fi
done

MODEL_LIST=("${FILTERED_LIST[@]}")

if [[ ${#MODEL_LIST[@]} -eq 0 ]]; then
    fail "No models to evaluate."
    exit 1
fi

# ── Print sweep plan ──
echo ""
echo -e "${BOLD}╭──────────────────────────────────────╮${RESET}"
echo -e "${BOLD}│       aeval Full Model Sweep          │${RESET}"
echo -e "${BOLD}╰──────────────────────────────────────╯${RESET}"
echo ""
echo -e "  Suite:      ${CYAN}${SUITE}${RESET}"
echo -e "  Models:     ${CYAN}${#MODEL_LIST[@]}${RESET}"
echo -e "  Results:    ${DIM}${RESULTS_DIR}${RESET}"
echo -e "  Timestamp:  ${DIM}${TIMESTAMP}${RESET}"
echo ""

if [[ ${#SKIPPED_LIST[@]} -gt 0 ]]; then
    warn "Skipping ${#SKIPPED_LIST[@]} multimodal model(s): ${SKIPPED_LIST[*]}"
    echo "  (use --include-multimodal to include them)"
    echo ""
fi

echo -e "  ${BOLD}Models to evaluate:${RESET}"
for model in "${MODEL_LIST[@]}"; do
    echo -e "    • ${model}"
done
echo ""

# ── Run evals ──
PASS_COUNT=0
FAIL_COUNT=0
ERROR_COUNT=0
TOTAL=${#MODEL_LIST[@]}
CURRENT=0

log "Starting sweep (${TOTAL} models × suite:${SUITE})..."
echo ""

SWEEP_START=$(date +%s)

for model in "${MODEL_LIST[@]}"; do
    CURRENT=$((CURRENT + 1))
    MODEL_LABEL="${model}"
    SAFE_NAME="${model//[:\/]/_}"
    LOG_FILE="${RESULTS_DIR}/${SAFE_NAME}.log"

    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${BOLD}[${CURRENT}/${TOTAL}]${RESET} ${CYAN}${MODEL_LABEL}${RESET}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""

    MODEL_START=$(date +%s)

    # Run aeval directly to terminal for live Rich output.
    # Use `script` to simultaneously capture a copy to the log file.
    # macOS `script`: script -q <logfile> <command> [args...]
    set +e
    script -q "$LOG_FILE" aeval run --suite "$SUITE" -m "ollama:${model}" --local
    EXIT_CODE=$?
    set -e

    MODEL_END=$(date +%s)
    ELAPSED=$((MODEL_END - MODEL_START))

    echo ""
    if [[ $EXIT_CODE -eq 0 ]]; then
        ok "${MODEL_LABEL}: completed (${ELAPSED}s)"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        fail "${MODEL_LABEL}: error after ${ELAPSED}s (exit code ${EXIT_CODE})"
        ERROR_COUNT=$((ERROR_COUNT + 1))
    fi
    echo ""
done

SWEEP_END=$(date +%s)
SWEEP_ELAPSED=$((SWEEP_END - SWEEP_START))
SWEEP_MINUTES=$((SWEEP_ELAPSED / 60))
SWEEP_SECONDS=$((SWEEP_ELAPSED % 60))

# ── Generate summary ──
SUMMARY_FILE="${RESULTS_DIR}/summary.json"
python3 << PYEOF
import json, glob, os, re

results_dir = '${RESULTS_DIR}'
suite = '${SUITE}'
timestamp = '${TIMESTAMP}'
elapsed = ${SWEEP_ELAPSED}

def strip_ansi(text):
    """Remove ANSI escape codes and control chars from script output."""
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    text = re.sub(r'\x1b\][^\x07]*\x07', '', text)
    text = re.sub(r'[\x00-\x09\x0b-\x0c\x0e-\x1f]', '', text)
    return text

model_results = {}

for f in sorted(glob.glob(os.path.join(results_dir, '*.log'))):
    model_name = os.path.basename(f).rsplit('.', 1)[0]
    try:
        raw = open(f).read()
        content = strip_ansi(raw)
    except Exception:
        continue

    evals = []

    # Pattern 1: Suite summary table rows like "│ factuality-v1  │ 0.840 │ PASS │"
    for m in re.finditer(r'│\s*([\w][\w.-]+)\s*│\s*(\d+\.\d{2,4})\s*│\s*(PASS|FAIL)\s*│', content):
        eval_name = m.group(1).strip()
        score = float(m.group(2))
        passed = m.group(3) == 'PASS'
        evals.append({'eval_name': eval_name, 'score': score, 'passed': passed})

    # Pattern 2: Individual eval output "Score: 0.840  (20/25 tasks)"
    if not evals:
        for m in re.finditer(r'Score:\s*(\d+\.\d{2,4})', content):
            score = float(m.group(1))
            passed = 'PASS' in content[m.start():m.start()+200]
            evals.append({'score': score, 'passed': passed})

    # Pattern 3: "factuality-v1 ... 0.840 ... passed" style
    if not evals:
        for m in re.finditer(r'([\w][\w.-]+).*?(\d+\.\d{3}).*?(passed|failed)', content, re.IGNORECASE):
            eval_name = m.group(1).strip()
            score = float(m.group(2))
            passed = m.group(3).lower() == 'passed'
            evals.append({'eval_name': eval_name, 'score': score, 'passed': passed})

    if evals:
        avg_score = sum(e['score'] for e in evals) / len(evals)
        model_results[model_name] = {
            'avg_score': round(avg_score, 4),
            'evals': evals,
            'num_evals': len(evals),
            'passed': sum(1 for e in evals if e.get('passed', False)),
        }

# Sort by avg score descending
ranked = sorted(model_results.items(), key=lambda x: x[1]['avg_score'], reverse=True)

summary = {
    'suite': suite,
    'timestamp': timestamp,
    'total_models': len(ranked),
    'elapsed_seconds': elapsed,
    'leaderboard': [
        {
            'rank': i + 1,
            'model': name,
            'avg_score': data['avg_score'],
            'evals_passed': data['passed'],
            'evals_total': data['num_evals'],
        }
        for i, (name, data) in enumerate(ranked)
    ],
    'per_model': {name: data for name, data in ranked},
}

with open('${SUMMARY_FILE}', 'w') as f:
    json.dump(summary, f, indent=2)
PYEOF

# ── Print leaderboard ──
echo -e "${BOLD}╭──────────────────────────────────────╮${RESET}"
echo -e "${BOLD}│          Sweep Leaderboard            │${RESET}"
echo -e "${BOLD}╰──────────────────────────────────────╯${RESET}"
echo ""

python3 << PYEOF
import json

with open('${SUMMARY_FILE}') as f:
    summary = json.load(f)

if not summary['leaderboard']:
    print('  No scores parsed — check log files in ${RESULTS_DIR}/')
else:
    print('  Suite: ${SUITE}    Models: ${TOTAL}    Time: ${SWEEP_MINUTES}m ${SWEEP_SECONDS}s')
    print()
    print(f'  {"Rank":<6}{"Model":<35}{"Avg Score":<12}{"Evals Passed":<15}')
    print(f'  {"────":<6}{"─────":<35}{"─────────":<12}{"────────────":<15}')

    for entry in summary['leaderboard']:
        rank = entry['rank']
        model = entry['model']
        score = f"{entry['avg_score']:.3f}"
        passed = f"{entry['evals_passed']}/{entry['evals_total']}"

        if rank == 1:
            prefix = '  1.'
        elif rank == 2:
            prefix = '  2.'
        elif rank == 3:
            prefix = '  3.'
        else:
            prefix = f'  {rank}.'

        print(f'  {prefix:<6}{model:<35}{score:<12}{passed:<15}')

    print()
PYEOF

# ── Final status ──
echo -e "  Completed: ${GREEN}${PASS_COUNT}${RESET}  Errors: ${RED}${ERROR_COUNT}${RESET}"
echo -e "  Results:   ${DIM}${RESULTS_DIR}${RESET}"
echo -e "  Summary:   ${DIM}${SUMMARY_FILE}${RESET}"
echo ""

# Exit with error if any model failed
if [[ $ERROR_COUNT -gt 0 ]]; then
    exit 1
fi
