#!/usr/bin/env bash
set -e

# Premium Terminal Styling
COLOR_RESET="\033[0m"
COLOR_BOLD="\033[1m"
COLOR_TEAL="\033[38;5;38m"
COLOR_AMBER="\033[38;5;214m"
COLOR_GREEN="\033[38;5;40m"
COLOR_RED="\033[38;5;196m"

echo -e "${COLOR_TEAL}${COLOR_BOLD}"
echo "=========================================================="
echo "          TAIGAAI WORKSTATION ENGINE INSTALLER            "
echo "=========================================================="
echo -e "${COLOR_RESET}"

WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_BIN_DIR="$HOME/.local/bin"

# 1. Self-Diagnosis
echo -n "Checking Python 3... "
if command -v python3 >/dev/null 2>&1; then
    echo -e "${COLOR_GREEN}OK (${COLOR_BOLD}$(python3 --version | cut -d' ' -f2)${COLOR_RESET}${COLOR_GREEN})${COLOR_RESET}"
else
    echo -e "${COLOR_RED}Missing! Please install Python 3.${COLOR_RESET}"
    exit 1
fi

echo -n "Checking Git... "
if command -v git >/dev/null 2>&1; then
    echo -e "${COLOR_GREEN}OK (${COLOR_BOLD}$(git --version | cut -d' ' -f3)${COLOR_RESET}${COLOR_GREEN})${COLOR_RESET}"
else
    echo -e "${COLOR_RED}Missing! Please install Git.${COLOR_RESET}"
    exit 1
fi

# Run setup configuration and diagnostics wizard
python3 "$WORKSPACE_DIR/core/setup_config.py"

# 2. Local Bin Symlinking (No-root boundaries)
echo -e "\nConfiguring Local Tool Symlinks... "
mkdir -p "$LOCAL_BIN_DIR"

ln -sf "$WORKSPACE_DIR/bin/taiga" "$LOCAL_BIN_DIR/taiga"
ln -sf "$WORKSPACE_DIR/bin/taiga-git" "$LOCAL_BIN_DIR/taiga-git"
ln -sf "$WORKSPACE_DIR/bin/taiga-review" "$LOCAL_BIN_DIR/taiga-review"
ln -sf "$WORKSPACE_DIR/bin/taiga-sec" "$LOCAL_BIN_DIR/taiga-sec"
ln -sf "$WORKSPACE_DIR/bin/taiga-manage" "$LOCAL_BIN_DIR/taiga-manage"

echo -e "${COLOR_GREEN}✔ Core router successfully linked: $LOCAL_BIN_DIR/taiga${COLOR_RESET}"
echo -e "${COLOR_GREEN}✔ Git assistant successfully linked: $LOCAL_BIN_DIR/taiga-git${COLOR_RESET}"
echo -e "${COLOR_GREEN}✔ Code reviewer successfully linked: $LOCAL_BIN_DIR/taiga-review${COLOR_RESET}"
echo -e "${COLOR_GREEN}✔ Security auditor successfully linked: $LOCAL_BIN_DIR/taiga-sec${COLOR_RESET}"
echo -e "${COLOR_GREEN}✔ Management console successfully linked: $LOCAL_BIN_DIR/taiga-manage${COLOR_RESET}"

# Remove old ai symlinks if they exist in LOCAL_BIN_DIR
rm -f "$LOCAL_BIN_DIR/ai" "$LOCAL_BIN_DIR/ai-git" "$LOCAL_BIN_DIR/ai-review" "$LOCAL_BIN_DIR/ai-sec"

# 3. Path Validation
if [[ ":$PATH:" != *":$LOCAL_BIN_DIR:"* ]]; then
    echo -e "\n${COLOR_AMBER}${COLOR_BOLD}⚠️ ACTION REQUIRED: ~/.local/bin is not in your system PATH!${COLOR_RESET}"
    echo -e "To execute the tools from anywhere, append this to your ~/.bashrc or ~/.zshrc file:"
    echo -e "  ${COLOR_BOLD}export PATH=\"\$HOME/.local/bin:\$PATH\"${COLOR_RESET}"
else
    echo -e "\n${COLOR_GREEN}${COLOR_BOLD}🎉 Setup complete! All tools are now accessible system-wide.${COLOR_RESET}"
fi

echo -e "\n${COLOR_TEAL}${COLOR_BOLD}Try running:${COLOR_RESET}"
echo -e "  taiga -h"
echo -e "  taiga-git help"
echo -e "  taiga-review"
echo -e "  taiga-sec"
echo -e "  taiga-manage"
echo ""
