#!/bin/bash
################################################################################
# Crux Job Submission Wrapper
# ============================
# Convenient wrapper for submitting XRD processing jobs with configurable
# parallelism.
#
# Usage:
#   ./scripts/submit_crux.sh <workers_per_node> [mode]
#
# Arguments:
#   workers_per_node: Number of Dask workers per node (1-128)
#   mode: "debug" or "production" (default: debug)
#
# Examples:
#   ./scripts/submit_crux.sh 64           # 64 workers/node, debug queue
#   ./scripts/submit_crux.sh 128 debug    # 128 workers/node, debug queue
#   ./scripts/submit_crux.sh 96 production  # 96 workers/node, production queue
#
# Parallelism Guide:
#   Conservative:  32 workers/node  (~8GB RAM per worker)
#   Balanced:      64 workers/node  (~4GB RAM per worker)
#   Aggressive:    96 workers/node  (~2.5GB RAM per worker)
#   Maximum:      128 workers/node  (~2GB RAM per worker)
#
# Author: William Gonzalez
# Date: October 2025
################################################################################

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
WORKERS_PER_NODE=${1:-64}
MODE=${2:-debug}

# Validate workers_per_node
if ! [[ "$WORKERS_PER_NODE" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}Error: workers_per_node must be a number${NC}"
    echo "Usage: $0 <workers_per_node> [mode]"
    exit 1
fi

if [ "$WORKERS_PER_NODE" -lt 1 ] || [ "$WORKERS_PER_NODE" -gt 128 ]; then
    echo -e "${RED}Error: workers_per_node must be between 1 and 128${NC}"
    echo "Crux nodes have 128 cores each"
    exit 1
fi

# Validate mode
if [ "$MODE" != "debug" ] && [ "$MODE" != "production" ]; then
    echo -e "${RED}Error: mode must be 'debug' or 'production'${NC}"
    echo "Usage: $0 <workers_per_node> [mode]"
    exit 1
fi

# Select PBS script
if [ "$MODE" = "debug" ]; then
    PBS_SCRIPT="scripts/submit_crux_debug.pbs"
    QUEUE="debug"
else
    PBS_SCRIPT="scripts/submit_crux_production.pbs"
    QUEUE="workq-route"
fi

# Check if PBS script exists
if [ ! -f "$PBS_SCRIPT" ]; then
    echo -e "${RED}Error: PBS script not found: $PBS_SCRIPT${NC}"
    exit 1
fi

# Display configuration
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Crux XRD Processing Job Submission            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Configuration:${NC}"
echo "  Mode: $MODE"
echo "  Queue: $QUEUE"
echo "  Workers per node: $WORKERS_PER_NODE"
echo "  PBS script: $PBS_SCRIPT"
echo ""

# Calculate parallelism for different node counts
echo -e "${GREEN}Expected parallelism:${NC}"
for nodes in 4 8 16 32; do
    total_ranks=$((nodes * WORKERS_PER_NODE))
    workers=$((total_ranks - 2))
    echo "  $nodes nodes: $workers Dask workers ($((workers / nodes)) per node)"
done
echo ""

# Memory estimate
MEM_PER_WORKER=$((256 / WORKERS_PER_NODE))
echo -e "${GREEN}Memory estimate:${NC}"
echo "  ~${MEM_PER_WORKER}GB RAM per worker"

if [ "$MEM_PER_WORKER" -lt 2 ]; then
    echo -e "  ${YELLOW}⚠ Warning: Less than 2GB per worker may cause memory issues${NC}"
elif [ "$MEM_PER_WORKER" -lt 3 ]; then
    echo -e "  ${YELLOW}⚠ Caution: 2-3GB per worker is tight for large datasets${NC}"
else
    echo -e "  ${GREEN}✓ Adequate memory per worker${NC}"
fi
echo ""

# Confirm submission
read -p "Submit job? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Job submission cancelled"
    exit 0
fi

# Submit job with WORKERS_PER_NODE variable
echo -e "${GREEN}Submitting job...${NC}"
JOB_ID=$(qsub -v WORKERS_PER_NODE=${WORKERS_PER_NODE} "$PBS_SCRIPT")

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Job submitted successfully${NC}"
    echo "  Job ID: $JOB_ID"
    echo ""
    echo "Monitor with:"
    echo "  qstat -u \$USER"
    echo "  qstat -f $JOB_ID"
    echo "  tail -f ~/xrd_${MODE}_${JOB_ID}.out"
else
    echo -e "${RED}✗ Job submission failed${NC}"
    exit 1
fi
