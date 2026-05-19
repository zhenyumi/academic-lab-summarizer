#!/usr/bin/env bash

if [ -z "${BASH_VERSION:-}" ] || shopt -oq posix; then
    echo "Error: This script requires Bash. Run with: bash $0" >&2
    exit 1
fi
#
# Shared functions for Academic Lab Summarizer install scripts.
# Sourced by install-claude.sh, install-codex.sh, install-opencode.sh, install-openclaw.sh
#
# Each installer must define before calling run_installer:
#   TOOL_NAME           - Display name (e.g., "Claude Code")
#   DEFAULT_TARGET_DIR  - Global install path
#   PROJECT_SUBDIR      - Project-level subdirectory
#   copy_skill_files()  - Platform-specific file copy: copy_skill_files src_dir target_dir
#   print_usage()       - Help text (use print_common_options for shared flags)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_MODE="global"
PROJECT_PATH=""
VALIDATE_ONLY=false
UPDATE_MODE=false
UNINSTALL_MODE=false
VERBOSE=false
DRY_RUN=false
CATEGORY_FILTER=""
FORCE=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The 4 skills in this pack (flat, not category-nested)
SKILLS=(lab-site-evidence-extraction
        lab-publication-profile
        lab-profile-synthesis
        academic-lab-summarizer)

print_common_options() {
    echo "  --global              Install to default global location (default)"
    echo "  --project [PATH]      Install to project/workspace directory"
    echo "  --categories CATS     Install only specified skills (comma-separated)"
    echo "  --list                List available skills"
    echo "  --validate            Validate all skills before installing"
    echo "  --update              Only update skills that have changed"
    echo "  --uninstall           Remove all installed skills"
    echo "  --dry-run             Preview what would be installed"
    echo "  --verbose             Show detailed output"
    echo "  --force               Force install even if target has existing content"
    echo "  -h, --help            Show this help message"
}

list_skills() {
    echo "Available Academic Lab Summarizer skills:"
    echo ""
    for skill in "${SKILLS[@]}"; do
        local skill_dir="$SCRIPT_DIR/$skill"
        if [[ -f "$skill_dir/SKILL.md" ]]; then
            local desc=$(grep "^description:" "$skill_dir/SKILL.md" | head -1 | sed 's/description: //')
            echo "  $skill"
            [[ -n "$desc" ]] && echo "    ${desc:0:80}"
            echo ""
        fi
    done
    echo "Total skills: ${#SKILLS[@]}"
}

validate_all_skills() {
    echo "Validating all skills..."
    echo ""
    local total=0 passed=0 failed=0

    for skill in "${SKILLS[@]}"; do
        total=$((total + 1))
        local skill_file="$SCRIPT_DIR/$skill/SKILL.md"
        local errors=()

        [[ -f "$skill_file" ]] || { errors+=("Missing SKILL.md"); }
        if [[ -f "$skill_file" ]]; then
            grep -q "^name:" "$skill_file" || errors+=("Missing 'name' in frontmatter")
            grep -q "^description:" "$skill_file" || errors+=("Missing 'description' in frontmatter")
            head -1 "$skill_file" | grep -q "^---$" || errors+=("No YAML frontmatter")
        fi

        if [[ ${#errors[@]} -gt 0 ]]; then
            failed=$((failed + 1))
            echo -e "  ${RED}FAIL${NC} $skill"
            for err in "${errors[@]}"; do
                echo "       - $err"
            done
        else
            passed=$((passed + 1))
            echo -e "  ${GREEN}PASS${NC} $skill"
        fi
    done

    echo ""
    echo "Validation complete: $passed/$total passed"
    [[ $failed -gt 0 ]] && return 1
    return 0
}

get_target_skills() {
    if [[ -n "$CATEGORY_FILTER" ]]; then
        IFS=',' read -ra FILTER <<< "$CATEGORY_FILTER"
        local result=()
        for s in "${FILTER[@]}"; do
            s=$(echo "$s" | xargs)
            local found=false
            for skill in "${SKILLS[@]}"; do
                if [[ "$skill" == "$s" ]]; then
                    result+=("$skill")
                    found=true
                    break
                fi
            done
            if ! $found; then
                echo -e "${YELLOW}Warning: unknown skill '$s' - skipping${NC}" >&2
            fi
        done
        echo "${result[@]}"
    else
        echo "${SKILLS[@]}"
    fi
}

file_mtime() {
    local file="$1"
    stat -c %Y "$file" 2>/dev/null || stat -f %m "$file" 2>/dev/null || echo 0
}

newest_mtime() {
    local dir="$1"
    local newest=0
    local file mtime
    while IFS= read -r -d '' file; do
        mtime=$(file_mtime "$file")
        [[ "$mtime" =~ ^[0-9]+$ ]] || mtime=0
        if (( mtime > newest )); then
            newest=$mtime
        fi
    done < <(find "$dir" -type f -print0 2>/dev/null)
    echo "$newest"
}

check_project_conflicts() {
    local target_dir="$1"
    [[ "$INSTALL_MODE" != "project" ]] && return 0
    $UPDATE_MODE && return 0
    if [[ -d "$target_dir" ]] && [[ -n "$(ls -A "$target_dir" 2>/dev/null)" ]]; then
        if [[ "$FORCE" != true ]]; then
            echo -e "${YELLOW}Warning: $target_dir already contains content.${NC}"
            echo "Use --update to update in place, or --force to install anyway."
            exit 1
        fi
    fi
}

install_skills() {
    local target_dir="$1"

    if [[ "$DRY_RUN" = false ]]; then
        if [[ "$INSTALL_MODE" = "project" ]]; then
            local base_dir="${PROJECT_PATH:-$(pwd)}"
            [[ -d "$base_dir" ]] || { echo -e "${RED}Error: Project directory does not exist: $base_dir${NC}"; exit 1; }
        fi
        check_project_conflicts "$target_dir"
    fi

    if $DRY_RUN; then
        echo "Dry run - would install to: $target_dir"
    else
        echo "Installing Academic Lab Summarizer skills to $target_dir ..."
    fi
    echo ""

    $DRY_RUN || mkdir -p "$target_dir"

    local installed=0 skipped=0 errors=0

    for skill in $(get_target_skills); do
        local skill_dir="$SCRIPT_DIR/$skill"
        local target_skill_dir="$target_dir/$skill"

        if [[ ! -d "$skill_dir" ]]; then
            echo -e "  ${RED}Error: $skill not found in source${NC}"
            errors=$((errors + 1))
            continue
        fi

        if $UPDATE_MODE && [[ -d "$target_skill_dir" ]]; then
            local src_newest=$(newest_mtime "$skill_dir")
            local dst_newest=$(newest_mtime "$target_skill_dir")
            src_newest=${src_newest:-0}
            dst_newest=${dst_newest:-0}
            if [[ "$src_newest" -le "$dst_newest" ]]; then
                skipped=$((skipped + 1))
                $VERBOSE && echo "  Skipped (unchanged): $skill"
                continue
            fi
        fi

        if $DRY_RUN; then
            installed=$((installed + 1))
            $VERBOSE && echo "  Would install: $skill"
            continue
        fi

        mkdir -p "$target_skill_dir"

        if ! copy_skill_files "$skill_dir" "$target_skill_dir"; then
            echo -e "  ${RED}Error copying: $skill${NC}"
            errors=$((errors + 1))
            continue
        fi

        installed=$((installed + 1))
        $VERBOSE && echo "  Installed: $skill"
    done

    echo ""
    if $DRY_RUN; then
        echo "Would install $installed skills."
    else
        echo "Installed $installed skills."
        if $UPDATE_MODE; then
            echo "Skipped (unchanged): $skipped"
        fi
        if [[ $errors -gt 0 ]]; then
            echo -e "${RED}Errors: $errors${NC}"
        fi
    fi
}

uninstall_skills() {
    local target_dir="$1"

    if [[ ! -d "$target_dir" ]]; then
        echo "No skills directory found at: $target_dir"
        exit 0
    fi

    echo "Removing Academic Lab Summarizer skills from $target_dir ..."
    echo ""
    local removed=0

    for skill in "${SKILLS[@]}"; do
        if [[ -d "$target_dir/$skill" ]]; then
            rm -rf "$target_dir/$skill"
            echo "  Removed: $skill"
            removed=$((removed + 1))
        fi
    done

    echo ""
    echo "Uninstalled $removed skills."

    # Remove empty parent directory
    if [[ -d "$target_dir" ]] && [[ -z "$(ls -A "$target_dir" 2>/dev/null)" ]]; then
        rmdir "$target_dir" 2>/dev/null && echo "Removed empty skills directory."
    fi
}

run_installer() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --global) INSTALL_MODE="global"; shift ;;
            --project)
                INSTALL_MODE="project"
                [[ -n "${2-}" && ! "$2" =~ ^-- ]] && { PROJECT_PATH="$2"; shift; }
                shift ;;
            --categories)
                [[ -n "${2-}" && ! "$2" =~ ^-- ]] && { CATEGORY_FILTER="$2"; shift; } || { echo "Error: --categories requires a list"; exit 1; }
                shift ;;
            --list) list_skills; exit 0 ;;
            --validate) VALIDATE_ONLY=true; shift ;;
            --update) UPDATE_MODE=true; shift ;;
            --uninstall) UNINSTALL_MODE=true; shift ;;
            --dry-run) DRY_RUN=true; shift ;;
            --verbose|-v) VERBOSE=true; shift ;;
            --force) FORCE=true; shift ;;
            -h|--help) print_usage; exit 0 ;;
            *) echo "Unknown option: $1"; print_usage; exit 1 ;;
        esac
    done

    # Determine target directory
    if [[ "$INSTALL_MODE" = "global" ]]; then
        TARGET_DIR="$DEFAULT_TARGET_DIR"
    else
        local base="${PROJECT_PATH:-$(pwd)}"
        TARGET_DIR="$base/$PROJECT_SUBDIR"
    fi

    # Validate only
    if $VALIDATE_ONLY; then
        validate_all_skills && echo -e "\n${GREEN}All skills passed validation.${NC}" || { echo -e "\n${RED}Some skills failed validation.${NC}"; exit 1; }
        exit 0
    fi

    # Uninstall
    if $UNINSTALL_MODE; then
        uninstall_skills "$TARGET_DIR"
        exit 0
    fi

    # Install
    install_skills "$TARGET_DIR"
}
