#!/bin/bash

# setup_whisper.sh
# A robust script to setup whisper.cpp: clone, detect platform, build, and download model.

set -e  # Exit immediately if a command exits with a non-zero status.
set -o pipefail # Return value of a pipeline is the status of the last command to exit with a non-zero status

# --- Helper Functions ---

log() {
    echo -e "\033[1;32m[SETUP] $1\033[0m"
}

warn() {
    echo -e "\033[1;33m[WARN] $1\033[0m"
}

error() {
    echo -e "\033[1;31m[ERROR] $1\033[0m"
    exit 1
}

cleanup() {
    # This function is called on exit.
    # You can add cleanup logic here if needed (e.g., removing temp files).
    :
}

trap 'error "An unexpected error occurred on line $LINENO. Exiting."' ERR
trap cleanup EXIT

check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        error "$1 is not installed. Please install it and try again."
    fi
}

# --- 1. Dependency Checks ---

log "Checking dependencies..."
check_dependency git
check_dependency make
check_dependency cmake

# Check for a C++ compiler
if ! command -v g++ &> /dev/null && ! command -v clang++ &> /dev/null; then
    error "No C++ compiler found (g++ or clang++). Please install one."
fi

# Check for download tools (curl or wget required for model download script usually)
if ! command -v curl &> /dev/null && ! command -v wget &> /dev/null; then
    error "Neither curl nor wget found. Please install one of them for downloading models."
fi

# --- 2. Clone Repository ---

REPO_URL="https://github.com/innovatorved/whisper.cpp.original.git"
DIR_NAME="whisper.cpp"
BRANCH="develop"

if [ -d "$DIR_NAME" ]; then
    log "Directory '$DIR_NAME' already exists."
    
    # Check if it is a valid git repo
    if [ -d "$DIR_NAME/.git" ]; then
        log "Verifying it is the correct repository..."
        cd "$DIR_NAME"
        REMOTE_URL=$(git config --get remote.origin.url || echo "")
        cd .. # Go back to root to perform operations if needed

        # Normalize URLs for comparison (remove .git suffix, handle https vs ssh if needed - keeping simple for now)
        # We check if the REMOTE_URL contains the repo name or user/repo to be somewhat flexible but safe.
        if [[ "$REMOTE_URL" != *"$REPO_URL"* && "$REMOTE_URL" != *"innovatorved/whisper.cpp.original"* ]]; then
             warn "Directory '$DIR_NAME' exists but points to a different remote: $REMOTE_URL"
             warn "Expected: $REPO_URL"
             BACKUP_NAME="${DIR_NAME}.bak.$(date +%s)"
             warn "Backing up existing directory to '$BACKUP_NAME' and cloning fresh..."
             mv "$DIR_NAME" "$BACKUP_NAME"
             
             log "Cloning repository..."
             git clone "$REPO_URL" "$DIR_NAME"
             cd "$DIR_NAME"
             
             log "Checking out branch '$BRANCH'..."
             if ! git checkout "$BRANCH"; then
                 error "Failed to checkout branch '$BRANCH'."
             fi
        else
            # Remote matches, proceed with update
            cd "$DIR_NAME"
            log "Fetching updates..."
            if ! git fetch origin; then
                 error "Failed to fetch updates."
            fi

            log "Checking out branch '$BRANCH'..."
            if ! git checkout "$BRANCH"; then
                error "Failed to checkout branch '$BRANCH'."
            fi

            log "Pulling latest changes..."
            if ! git pull origin "$BRANCH"; then
                error "Failed to update repository. You may have local changes or merge conflicts. Please resolve them manually."
            fi
        fi
    else
        error "Directory '$DIR_NAME' exists but is not a git repository. Please remove it or rename it to proceed."
    fi
else
    log "Cloning repository..."
    git clone "$REPO_URL" "$DIR_NAME"
    cd "$DIR_NAME"
    
    log "Checking out branch '$BRANCH'..."
    if ! git checkout "$BRANCH"; then
        error "Failed to checkout branch '$BRANCH'."
    fi
fi

# --- 3. Platform Detection & Build Configuration ---

OS=$(uname -s)
ARCH=$(uname -m)
MAKE_ARGS=""

log "Detected Platform: OS=$OS, Arch=$ARCH"

if [ "$OS" = "Darwin" ]; then
    log "macOS detected."
    # Makefile usually handles Metal automatically on macOS
    MAKE_ARGS=""
elif [ "$OS" = "Linux" ]; then
    log "Linux detected."
    if command -v nvidia-smi &> /dev/null; then
        log "NVIDIA GPU detected. Enabling CUDA support."
        MAKE_ARGS="GGML_CUDA=1"
    else
        log "No NVIDIA GPU detected. Using CPU-only build."
        MAKE_ARGS=""
    fi
else
    log "Unknown or unsupported OS: $OS. Attempting standard build..."
    MAKE_ARGS=""
fi

# --- 4. Build ---

log "Building project with make..."

# Clean previous build if needed (optional, but good for robustness)
# make clean

# Compile the specific target 'whisper-cli' (or 'main' if that's the default name, but user mentioned cli)
# Based on standard whisper.cpp, the main example is usually 'main' or 'whisper-cli' in newer versions.
# Checking the README provided, usage is ./build/bin/whisper-cli.
# If using Makefile directly, it might output to ./main or ./whisper-cli.
# Let's try building the default target first or specific if known.
# The user mentioned "compile it in to the use system afte rteh compiling cli part copy and paste in t the my app".

if ! make -j $MAKE_ARGS; then
    error "Build failed."
fi

# Locate the binary. It might be 'main' or 'whisper-cli' depending on the Makefile.
# Usually in root or bin/
BINARY_SOURCE=""
if [ -f "whisper-cli" ]; then
    BINARY_SOURCE="whisper-cli"
elif [ -f "main" ]; then
    BINARY_SOURCE="main"
elif [ -f "build/bin/whisper-cli" ]; then
    BINARY_SOURCE="build/bin/whisper-cli"
else
    # Try to find it
    BINARY_SOURCE=$(find . -maxdepth 2 -name "whisper-cli" -type f | head -n 1)
    if [ -z "$BINARY_SOURCE" ]; then
         BINARY_SOURCE=$(find . -maxdepth 2 -name "main" -type f | head -n 1)
    fi
fi

if [ -z "$BINARY_SOURCE" ]; then
    error "Could not locate compiled binary (whisper-cli or main)."
fi

log "Found binary at: $BINARY_SOURCE"

# --- 5. Install Binary ---

DEST_DIR="../binary"
DEST_BINARY="$DEST_DIR/whisper-cli"

log "Installing binary to $DEST_BINARY..."
mkdir -p "$DEST_DIR"
cp "$BINARY_SOURCE" "$DEST_BINARY"

# --- 6. Download Model ---

# Go back to root
cd ..

MODEL="base"
MODEL_PATH="models/ggml-$MODEL.bin"
DOWNLOAD_SCRIPT="./whisper.cpp/models/download-ggml-model.sh"

mkdir -p models

if [ -f "$MODEL_PATH" ]; then
    log "Model '$MODEL' already exists at $MODEL_PATH."
else
    if [ ! -f "$DOWNLOAD_SCRIPT" ]; then
        error "Download script '$DOWNLOAD_SCRIPT' not found."
    fi

    log "Downloading model '$MODEL'..."
    # The script downloads to the current directory or models/ depending on implementation.
    # We pass "." as the second argument to force downloading to the current directory (subtitle/models).
    
    cd models
    bash "../$DOWNLOAD_SCRIPT" "$MODEL" "."
    cd ..
    
    # Verify download
    if [ ! -f "models/ggml-$MODEL.bin" ]; then
        error "Failed to download model '$MODEL'."
    fi
fi

# --- 7. Verification ---

CLI_PATH="./binary/whisper-cli"

if [ ! -f "$CLI_PATH" ]; then
    error "Installation failed: $CLI_PATH not found."
fi

log "Verifying installed binary..."
if ! "$CLI_PATH" -h > /dev/null 2>&1; then
    error "Verification failed. The executable did not run correctly."
fi

log "Setup completed successfully!"
