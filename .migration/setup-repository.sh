#!/usr/bin/env bash

# S2DM Migration Repository Setup Script

set -euo pipefail

S2DM_REPO_URL="https://raw.githubusercontent.com/COVESA/s2dm/main"
MIGRATE_YML_URL="$S2DM_REPO_URL/.migration/workflows/migrate.yml"
BUMPVERSION_TOML_URL="$S2DM_REPO_URL/.migration/.bumpversion.toml"

TARGET_DIR="$(pwd)"

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --directory|-d)
                TARGET_DIR="$2"
                shift 2
                ;;
            --help|-h)
                echo "Usage: $0 [--dir DIRECTORY]"
                echo "  --dir DIRECTORY  Target directory to set up (default: current directory)"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    TARGET_DIR="$(realpath "$TARGET_DIR")"
}

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

is_git_repo() {
    (cd "$TARGET_DIR" && git rev-parse --git-dir > /dev/null 2>&1)
}

init_git_repo() {
    if is_git_repo; then
        log_info "Git repository already exists in $TARGET_DIR"
        return 0
    fi

    log_info "Initializing git repository in $TARGET_DIR..."
    (cd "$TARGET_DIR" && git init)
    log_success "Git repository initialized"
}

create_spec_dir() {
    if [[ -d "$TARGET_DIR/spec" ]]; then
        log_info "spec directory already exists"
        return 0
    fi

    log_info "Creating spec directory..."
    mkdir -p "$TARGET_DIR/spec"
    log_success "spec directory created"
}

download_file() {
    local url="$1"
    local dest="$2"
    local description="$3"

    log_info "Downloading $description..."

    if command -v curl >/dev/null 2>&1; then
        if curl -fsSL "$url" -o "$dest"; then
            log_success "$description downloaded to $dest"
            return 0
        else
            log_error "Failed to download $description using curl"
            return 1
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q "$url" -O "$dest"; then
            log_success "$description downloaded to $dest"
            return 0
        else
            log_error "Failed to download $description using wget"
            return 1
        fi
    else
        log_error "Neither curl nor wget is available. Please install one of them."
        return 1
    fi
}

download_migration_files() {
    if [[ ! -d "$TARGET_DIR/.github/workflows" ]]; then
        log_info "Creating .github/workflows directory..."
        mkdir -p "$TARGET_DIR/.github/workflows"
    fi

    local migrate_dest="$TARGET_DIR/.github/workflows/migrate.yml"

    if [[ -f "$migrate_dest" ]]; then
        log_warning "migrate.yml already exists at $migrate_dest"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Skipping migrate.yml"
        else
            download_file "$MIGRATE_YML_URL" "$migrate_dest" "migrate.yml"
        fi
    else
        download_file "$MIGRATE_YML_URL" "$migrate_dest" "migrate.yml"
    fi

    local bumpversion_dest="$TARGET_DIR/.bumpversion.toml"

    if [[ -f "$bumpversion_dest" ]]; then
        log_warning ".bumpversion.toml already exists at $bumpversion_dest"
        read -p "Do you want to overwrite it? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Skipping .bumpversion.toml"
        else
            download_file "$BUMPVERSION_TOML_URL" "$bumpversion_dest" ".bumpversion.toml"
        fi
    else
        download_file "$BUMPVERSION_TOML_URL" "$bumpversion_dest" ".bumpversion.toml"
    fi
}

show_next_steps() {
    echo ""
    log_success "Repository setup complete!"
    echo ""
    echo "Follow the setup guide for next steps:"
    echo "https://github.com/COVESA/s2dm/blob/main/.migration/docs/setup-guide.md"
}

main() {
    parse_args "$@"

    log_info "Starting S2DM migration repository setup in $TARGET_DIR..."
    echo ""

    init_git_repo

    create_spec_dir

    download_migration_files

    show_next_steps
}

main "$@"
