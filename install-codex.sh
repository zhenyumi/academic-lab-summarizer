#!/usr/bin/env bash
#
# Install Academic Lab Summarizer skills to Codex CLI
#
# Codex CLI stores skills under ~/.agents/skills/ (global) or .agents/skills/ (project).
# It uses SKILL.md for instructions, examples/, scripts/, and usage-guide.md references.
#
# Usage:
#   ./install-codex.sh                                          # Install globally
#   ./install-codex.sh --project /path/to/project               # Install to project
#   ./install-codex.sh --categories "skill1,skill2"             # Selective install
#   ./install-codex.sh --validate                               # Validate before installing
#   ./install-codex.sh --update                                 # Only update changed skills
#   ./install-codex.sh --uninstall                              # Remove installed skills
#   ./install-codex.sh --dry-run                                # Preview install

source "$(dirname "$0")/install-common.sh"

TOOL_NAME="Codex CLI"
DEFAULT_TARGET_DIR="$HOME/.agents/skills"
PROJECT_SUBDIR=".agents/skills"

print_usage() {
    echo "Usage: $(basename "$0") [OPTIONS]"
    echo ""
    echo "Install Academic Lab Summarizer skills for Codex CLI."
    echo ""
    echo "Options:"
    print_common_options
}

copy_skill_files() {
    local src_dir="$1" target_dir="$2"
    cp -Rp "$src_dir"/. "$target_dir"/ 2>/dev/null || return 1
}

run_installer "$@"
