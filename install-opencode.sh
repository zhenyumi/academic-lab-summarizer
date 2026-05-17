#!/usr/bin/env bash
#
# Install Academic Lab Summarizer skills to OpenCode
#
# OpenCode stores skills under ~/.config/opencode/skills/ (global) or .opencode/skills/ (project).
# Each skill directory contains SKILL.md and optionally usage-guide.md and agents/.
#
# Usage:
#   ./install-opencode.sh                                       # Install globally
#   ./install-opencode.sh --project /path/to/project            # Install to project
#   ./install-opencode.sh --categories "skill1,skill2"          # Selective install
#   ./install-opencode.sh --validate                            # Validate before installing
#   ./install-opencode.sh --update                              # Only update changed skills
#   ./install-opencode.sh --uninstall                           # Remove installed skills
#   ./install-opencode.sh --dry-run                             # Preview install

source "$(dirname "$0")/install-common.sh"

TOOL_NAME="OpenCode"
DEFAULT_TARGET_DIR="$HOME/.config/opencode/skills"
PROJECT_SUBDIR=".opencode/skills"

print_usage() {
    echo "Usage: $(basename "$0") [OPTIONS]"
    echo ""
    echo "Install Academic Lab Summarizer skills for OpenCode."
    echo ""
    echo "Options:"
    print_common_options
}

copy_skill_files() {
    local src_dir="$1" target_dir="$2"
    cp -Rp "$src_dir"/. "$target_dir"/ 2>/dev/null || return 1
}

run_installer "$@"
