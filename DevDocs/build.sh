#!/bin/bash
# Build script for DevDocs Keypirinha plugin (Linux development)

PACKAGE_NAME="DevDocs"
BUILD_DIR="./build"

show_help() {
    echo "Usage: ./build.sh [command]"
    echo ""
    echo "Commands:"
    echo "  help    - Show this help message"
    echo "  clean   - Remove build directory"
    echo "  build   - Build the plugin package"
    echo ""
    echo "Note: This script is for development on Linux."
    echo "      The plugin is designed to run on Windows with Keypirinha."
}

clean() {
    echo "Cleaning build directory..."
    rm -rf "$BUILD_DIR"
    echo "Clean complete."
}

build() {
    echo "Building $PACKAGE_NAME plugin..."

    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Create build directory
    mkdir -p "$SCRIPT_DIR/$BUILD_DIR"

    # Create a temporary directory for packaging
    TEMP_DIR=$(mktemp -d)

    # Copy files to temp directory (flattened - files at root, not in src/)
    cp "$SCRIPT_DIR/src/"*.py "$TEMP_DIR/"
    cp "$SCRIPT_DIR/src/"*.ini "$TEMP_DIR/"
    cp "$SCRIPT_DIR/LICENSE" "$TEMP_DIR/"
    cp "$SCRIPT_DIR/README.md" "$TEMP_DIR/"

    # Convert .ini file to Windows line endings (CRLF) since plugin runs on Windows
    if command -v unix2dos &> /dev/null; then
        unix2dos "$TEMP_DIR/"*.ini 2>/dev/null
    elif command -v dos2unix &> /dev/null; then
        dos2unix -n "$TEMP_DIR/"*.ini "$TEMP_DIR/"*.ini 2>/dev/null || sed -i 's/$/\r/' "$TEMP_DIR/"*.ini
    else
        # Fallback: use sed to add CR
        sed -i 's/$/\r/' "$TEMP_DIR/"*.ini
    fi

    # Create the package (it's just a ZIP file with .keypirinha-package extension)
    cd "$TEMP_DIR"
    zip -r "$PACKAGE_NAME.keypirinha-package" * > /dev/null
    cd - > /dev/null

    # Move package to build directory
    mv "$TEMP_DIR/$PACKAGE_NAME.keypirinha-package" "$SCRIPT_DIR/$BUILD_DIR/"

    # Clean up temp directory
    rm -rf "$TEMP_DIR"

    # Get absolute path
    ABS_PATH=$(realpath "$SCRIPT_DIR/$BUILD_DIR/$PACKAGE_NAME.keypirinha-package")

    echo "Build complete: $ABS_PATH"
    echo ""
    echo "Package structure:"
    unzip -l "$ABS_PATH" | grep -E "\.py|\.ini|LICENSE|README"
    echo ""
    echo "To install on Windows:"
    echo "  1. Copy the .keypirinha-package file to your Windows machine"
    echo "  2. Place it in: %APPDATA%\\Keypirinha\\InstalledPackages"
    echo "  3. Restart Keypirinha or reload the catalog"
}

# Main script
case "${1:-help}" in
    help|--help|-h)
        show_help
        ;;
    clean)
        clean
        ;;
    build)
        build
        ;;
    *)
        echo "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
