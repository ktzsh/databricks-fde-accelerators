#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

cd "$(dirname "$0")";

# Function to get available targets from databricks.yml
get_targets() {
    # Find the targets section and extract target names
    awk '/^targets:/ {in_targets=1; next} 
         /^[a-zA-Z]/ && in_targets {in_targets=0} 
         in_targets && /^  [a-zA-Z]/ {gsub(/^[ ]*/, "", $1); gsub(/:$/, "", $1); print $1}' ../../databricks.yml
}

# Function to get workspace info for a specific target using databricks bundle summary
get_workspace_info() {
    local target=$1
    local bundle_summary=$(databricks bundle summary -t "$target" --output json 2>/dev/null)
    
    if [ $? -ne 0 ] || [ -z "$bundle_summary" ]; then
        echo "Error: Failed to get bundle summary for target '$target'" >&2
        return 1
    fi
    
    local host=$(echo "$bundle_summary" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('workspace', {}).get('host', ''))")
    local root_path=$(echo "$bundle_summary" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('workspace', {}).get('root_path', ''))")
    
    if [ -z "$host" ] || [ -z "$root_path" ]; then
        echo "Error: Could not extract workspace information from bundle summary" >&2
        return 1
    fi
    
    echo "$host|$root_path"
}

# Databricks App must already have been created. You can do so with the Databricks CLI or via the UI in a Workspace.
LAKEHOUSE_APP_NAME=${2:-"chat-ui-fastapi"}

# Get available targets
echo "Available targets:"
targets=($(get_targets))
for i in "${!targets[@]}"; do
    echo "  $((i+1)). ${targets[$i]}"
done

# Let user select target or use default
if [ -z "$3" ]; then
    echo -n "Select target (1-${#targets[@]}) or press Enter for default (1): "
    read selection
    selection=${selection:-1}
else
    selection=$3
fi

# Validate selection
if ! [[ "$selection" =~ ^[0-9]+$ ]] || [ "$selection" -lt 1 ] || [ "$selection" -gt ${#targets[@]} ]; then
    echo "Invalid selection. Using first target."
    selection=1
fi

selected_target=${targets[$((selection-1))]}
echo "Selected target: $selected_target"

# Get workspace information for selected target
workspace_info=$(get_workspace_info "$selected_target")
if [ $? -ne 0 ]; then
    echo "Failed to get workspace information for target: $selected_target"
    exit 1
fi

WORKSPACE_URL=$(echo "$workspace_info" | cut -d'|' -f1)
BUNDLE_PATH=$(echo "$workspace_info" | cut -d'|' -f2)

# Accept parameters
APP_FOLDER_IN_WORKSPACE=${1:-"${BUNDLE_PATH}/files/apps/chat-ui-fastapi/"}

# Deploy the application
databricks apps deploy "$LAKEHOUSE_APP_NAME" --source-code-path "$APP_FOLDER_IN_WORKSPACE" --target "$selected_target"
# Print the app page URL -- put your workspace name in the below URL.
echo "Open the app page for details and permission: $WORKSPACE_URL/apps/$LAKEHOUSE_APP_NAME"
