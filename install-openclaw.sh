#!/usr/bin/env bash
#
# Install Academic Lab Summarizer skills to OpenClaw
#
# OpenClaw stores skills under ~/.openclaw/skills/<package>/ (global).
# Skills are grouped under a package name (academic-lab-summarizer) with each skill as a subdirectory.
#
# Usage:
#   ./install-openclaw.sh                                       # Install globally
#   ./install-openclaw.sh --project /path/to/workspace          # Install to workspace
#   ./install-openclaw.sh --categories "skill1,skill2"          # Selective install
#   ./install-openclaw.sh --validate                            # Validate before installing
#   ./install-openclaw.sh --update                              # Only update changed skills
#   ./install-openclaw.sh --uninstall                           # Remove installed skills
#   ./install-openclaw.sh --dry-run                             # Preview install

source "$(dirname "$0")/install-common.sh"

TOOL_NAME="OpenClaw"
PACKAGE_NAME="academic-lab-summarizer"
DEFAULT_TARGET_DIR="$HOME/.openclaw/skills/$PACKAGE_NAME"
PROJECT_SUBDIR="skills/$PACKAGE_NAME"

print_usage() {
    echo "Usage: $(basename "$0") [OPTIONS]"
    echo ""
    echo "Install Academic Lab Summarizer skills for OpenClaw."
    echo ""
    echo "Options:"
    print_common_options
}

copy_skill_files() {
    local src_dir="$1" target_dir="$2"
    cp -Rp "$src_dir"/. "$target_dir"/ 2>/dev/null || return 1
}

# Override uninstall: remove entire package directory, not individual skills.
uninstall_skills() {
    local target_dir="$1"

    if [[ ! -d "$target_dir" ]]; then
        echo "No skills package found at: $target_dir"
        exit 0
    fi

    echo "Removing $PACKAGE_NAME from $target_dir ..."
    rm -rf "$target_dir"
    echo "Removed $PACKAGE_NAME."

    # Remove parent if empty
    local parent=$(dirname "$target_dir")
    if [[ -d "$parent" ]] && [[ -z "$(ls -A "$parent" 2>/dev/null)" ]]; then
        rmdir "$parent" 2>/dev/null && echo "Removed empty skills directory."
    fi
}

run_installer "$@"
