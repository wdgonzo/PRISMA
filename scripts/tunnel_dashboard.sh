#!/bin/bash
#
# Dask Dashboard SSH Tunnel Helper
# ==================================
# This script establishes an SSH tunnel to view the Dask dashboard
# running on a CRUX compute node.
#
# Usage:
#   ./scripts/tunnel_dashboard.sh <compute-node-hostname>
#   ./scripts/tunnel_dashboard.sh             (interactive mode)
#
# Author: William Gonzalez
# Date: October 2025
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DASHBOARD_PORT=8787
CRUX_LOGIN="crux.alcf.anl.gov"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}    Dask Dashboard SSH Tunnel Helper${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Function to check if port is already in use
check_port_available() {
    if lsof -Pi :$DASHBOARD_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "${YELLOW}WARNING: Port $DASHBOARD_PORT is already in use on localhost${NC}"
        echo -e "${YELLOW}You may already have a tunnel running, or another service is using this port${NC}"
        echo ""
        read -p "Kill existing process and continue? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            PID=$(lsof -ti:$DASHBOARD_PORT)
            kill -9 $PID 2>/dev/null || true
            echo -e "${GREEN}Killed process $PID${NC}"
            sleep 1
        else
            echo -e "${RED}Exiting. Close the existing tunnel or use a different port.${NC}"
            exit 1
        fi
    fi
}

# Function to extract hostname from job output
extract_hostname_from_output() {
    local job_id=$1
    local output_file="$HOME/xrd_prod_${job_id}.out"

    if [ -f "$output_file" ]; then
        # Look for "Compute Node: hostname" in the output
        COMPUTE_NODE=$(grep "Compute Node:" "$output_file" | head -n 1 | awk '{print $3}')
        if [ -n "$COMPUTE_NODE" ]; then
            echo -e "${GREEN}Found compute node from job output: $COMPUTE_NODE${NC}"
            return 0
        fi
    fi
    return 1
}

# Get compute node hostname
if [ $# -eq 0 ]; then
    echo "No hostname provided. Attempting to find from recent job output..."
    echo ""

    # Try to find the most recent job output file
    LATEST_OUTPUT=$(ls -t ~/xrd_prod_*.out 2>/dev/null | head -n 1)

    if [ -n "$LATEST_OUTPUT" ]; then
        JOB_ID=$(basename "$LATEST_OUTPUT" | sed 's/xrd_prod_//' | sed 's/.out//')
        echo -e "Found recent job output: ${GREEN}$LATEST_OUTPUT${NC}"

        if extract_hostname_from_output "$JOB_ID"; then
            COMPUTE_NODE="$COMPUTE_NODE"
        else
            echo -e "${YELLOW}Could not extract hostname from job output${NC}"
            echo ""
            read -p "Enter compute node hostname manually: " COMPUTE_NODE
        fi
    else
        echo -e "${YELLOW}No job output files found${NC}"
        echo ""
        echo "Please provide the compute node hostname."
        echo "You can find it in your job output file (look for 'Compute Node: hostname')"
        echo ""
        read -p "Enter compute node hostname: " COMPUTE_NODE
    fi
elif [ $# -eq 1 ]; then
    COMPUTE_NODE=$1
else
    echo -e "${RED}Error: Too many arguments${NC}"
    echo "Usage: $0 [compute-node-hostname]"
    exit 1
fi

# Validate hostname
if [ -z "$COMPUTE_NODE" ]; then
    echo -e "${RED}Error: Compute node hostname is required${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Tunnel Configuration:${NC}"
echo -e "  Local Port:     ${GREEN}$DASHBOARD_PORT${NC}"
echo -e "  Compute Node:   ${GREEN}$COMPUTE_NODE${NC}"
echo -e "  Remote Port:    ${GREEN}$DASHBOARD_PORT${NC}"
echo -e "  Login Node:     ${GREEN}$CRUX_LOGIN${NC}"
echo ""

# Check if local port is available
check_port_available

echo -e "${BLUE}Establishing SSH tunnel...${NC}"
echo ""
echo -e "SSH Command:"
echo -e "  ${YELLOW}ssh -L $DASHBOARD_PORT:$COMPUTE_NODE:$DASHBOARD_PORT $CRUX_LOGIN${NC}"
echo ""
echo -e "${GREEN}Once connected:${NC}"
echo -e "  1. Keep this terminal open (tunnel must stay active)"
echo -e "  2. Open your browser to: ${BLUE}http://localhost:$DASHBOARD_PORT${NC}"
echo -e "  3. Press Ctrl+C in this terminal to close the tunnel when done"
echo ""
echo -e "${YELLOW}Note: You will need to authenticate with your CRUX credentials${NC}"
echo ""
read -p "Press Enter to continue..."
echo ""

# Establish the tunnel
# -N: Don't execute a remote command (just forward ports)
# -L: Local port forwarding
ssh -N -L $DASHBOARD_PORT:$COMPUTE_NODE:$DASHBOARD_PORT $CRUX_LOGIN

# This line only executes when the tunnel is closed (Ctrl+C)
echo ""
echo -e "${GREEN}Tunnel closed successfully${NC}"
