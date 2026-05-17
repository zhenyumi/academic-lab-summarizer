#!/usr/bin/env bash
#
# Install Academic Lab Summarizer skills to Claude Code
#
# Usage:
#   ./install-claude.sh                                          # Install globally
#   ./install-claude.sh --project /path/to/project               # Install to project
#   ./install-claude.sh --categories "skill1,skill2"             # Selective install
#   ./install-claude.sh --validate                               # Validate before installing
#   ./install-claude.sh --update                                 # Only update changed skills
#   ./install-claude.sh --uninstall                              # Remove installed skills
#   ./install-claude.sh --dry-run                                # Preview install

source "$(dirname "$0")/install-common.sh"

TOOL_NAME="Claude Code"
DEFAULT_TARGET_DIR="$HOME/.claude/skills"
PROJECT_SUBDIR=".claude/skills"

print_usage() {
    echo "Usage: $(basename "$0") [OPTIONS]"
    echo ""
    echo "Install Academic Lab Summarizer skills for Claude Code."
    echo ""
    echo "Options:"
    print_common_options
}

copy_skill_files() {
    local src_dir="$1" target_dir="$2"
    cp -Rp "$src_dir"/. "$target_dir"/ 2>/dev/null || return 1
}

run_installer "$@"
