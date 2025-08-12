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

# Function to get workspace info for a specific target
get_workspace_info() {
    local target=$1
    local host=""
    local root_path=""
    local in_target=0
    local in_workspace=0
    
    while IFS= read -r line; do
        # Check if we're entering the target section
        if [[ "$line" =~ ^[[:space:]]*${target}:[[:space:]]*$ ]]; then
            in_target=1
            in_workspace=0
            continue
        fi
        
        # Check if we're leaving the target section (new target or top-level key)
        if [[ "$line" =~ ^[[:space:]]*[a-zA-Z] ]] && [[ ! "$line" =~ ^[[:space:]]*workspace: ]] && [[ ! "$line" =~ ^[[:space:]]*host: ]] && [[ ! "$line" =~ ^[[:space:]]*root_path: ]] && [[ ! "$line" =~ ^[[:space:]]*mode: ]] && [ $in_target -eq 1 ]; then
            in_target=0
            in_workspace=0
        fi
        
        # Check if we're in the workspace section of our target
        if [ $in_target -eq 1 ] && [[ "$line" =~ ^[[:space:]]*workspace:[[:space:]]*$ ]]; then
            in_workspace=1
            continue
        fi
        
        # Extract host and root_path when in the right section
        if [ $in_target -eq 1 ] && [ $in_workspace -eq 1 ]; then
            if [[ "$line" =~ ^[[:space:]]*host:[[:space:]]*(.+)$ ]]; then
                host="${BASH_REMATCH[1]}"
            elif [[ "$line" =~ ^[[:space:]]*root_path:[[:space:]]*(.+)$ ]]; then
                root_path="${BASH_REMATCH[1]}"
            fi
        fi
    done < ../../databricks.yml
    
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
WORKSPACE_URL=$(echo "$workspace_info" | cut -d'|' -f1)
BUNDLE_PATH=$(echo "$workspace_info" | cut -d'|' -f2)

# Accept parameters
APP_FOLDER_IN_WORKSPACE=${1:-"${BUNDLE_PATH}/apps/chat-ui-fastapi/"}

# Deploy the application
databricks apps deploy "$LAKEHOUSE_APP_NAME" --source-code-path "$APP_FOLDER_IN_WORKSPACE" --target "$selected_target"
# Print the app page URL -- put your workspace name in the below URL.
echo "Open the app page for details and permission: $WORKSPACE_URL/apps/$LAKEHOUSE_APP_NAME"
