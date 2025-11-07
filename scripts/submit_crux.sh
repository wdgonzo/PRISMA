#!/bin/bash
################################################################################
# Crux Job Submission Wrapper
# ============================
# Convenient wrapper for submitting XRD processing jobs with configurable
# parallelism.
#
# Usage:
#   ./scripts/submit_crux.sh <workers_per_node> [mode] [num_nodes] [walltime_hours] [--no-move]
#
# Arguments:
#   workers_per_node: Number of Dask workers per node (1-128)
#   mode: "debug" or "production" (default: debug)
#   num_nodes: Number of nodes (PRODUCTION ONLY, 1-184, default: 32)
#   walltime_hours: Walltime in hours (PRODUCTION ONLY, 1-24, default: 8)
#   --no-move: Optional flag to keep recipes in place after processing (not moved to processed/)
#
# Examples:
#   ./scripts/submit_crux.sh 64                        # 64 workers/node, debug (4 nodes, 2hr fixed)
#   ./scripts/submit_crux.sh 128 debug                 # 128 workers/node, debug (4 nodes, 2hr fixed)
#   ./scripts/submit_crux.sh 96 production             # 96 workers/node, production (32 nodes, 8hr default)
#   ./scripts/submit_crux.sh 64 production 64          # 64 workers/node, production, 64 nodes, 8hr
#   ./scripts/submit_crux.sh 64 production 64 12       # 64 workers/node, production, 64 nodes, 12hr
#   ./scripts/submit_crux.sh 128 production 128 24     # 128 workers/node, production, 128 nodes, 24hr
#   ./scripts/submit_crux.sh 64 production 32 8 --no-move  # Keep recipes in place after processing
#
# Parallelism Guide:
#   Conservative:  32 workers/node  (~8GB RAM per worker)
#   Balanced:      64 workers/node  (~4GB RAM per worker)
#   Aggressive:    96 workers/node  (~2.5GB RAM per worker)
#   Maximum:      128 workers/node  (~2GB RAM per worker)
#
# Walltime Guide (production):
#   Small datasets (100-500 frames):     2-4 hours
#   Medium datasets (500-2000 frames):   4-8 hours
#   Large datasets (2000-5000 frames):   8-12 hours
#   Very large (5000+ frames):           12-24 hours
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
NUM_NODES=${3}  # Optional, only for production
WALLTIME_HOURS=${4}  # Optional, only for production
NO_MOVE_RECIPES="false"  # Default: move recipes after processing

# Check for --no-move flag in any position
for arg in "$@"; do
    if [ "$arg" = "--no-move" ]; then
        NO_MOVE_RECIPES="true"
        break
    fi
done

# Validate workers_per_node
if ! [[ "$WORKERS_PER_NODE" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}Error: workers_per_node must be a number${NC}"
    echo "Usage: $0 <workers_per_node> [mode] [num_nodes] [walltime_hours]"
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
    echo "Usage: $0 <workers_per_node> [mode] [num_nodes] [walltime_hours]"
    exit 1
fi

# Handle node count and walltime based on mode
if [ "$MODE" = "debug" ]; then
    NUM_NODES=4  # Debug mode always uses 4 nodes
    WALLTIME_HOURS=2  # Debug mode always uses 2 hours

    if [ -n "$3" ]; then
        echo -e "${YELLOW}Warning: num_nodes parameter ignored for debug mode (fixed at 4 nodes)${NC}"
    fi
    if [ -n "$4" ]; then
        echo -e "${YELLOW}Warning: walltime_hours parameter ignored for debug mode (fixed at 2 hours)${NC}"
    fi
else
    # Production mode: use provided values or defaults
    NUM_NODES=${NUM_NODES:-32}
    WALLTIME_HOURS=${WALLTIME_HOURS:-8}

    # Validate num_nodes for production
    if ! [[ "$NUM_NODES" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}Error: num_nodes must be a number${NC}"
        exit 1
    fi

    if [ "$NUM_NODES" -lt 1 ] || [ "$NUM_NODES" -gt 184 ]; then
        echo -e "${RED}Error: num_nodes must be between 1 and 184 for production${NC}"
        echo "Crux workq-route queue supports 1-184 nodes"
        exit 1
    fi

    # Validate walltime_hours for production
    if ! [[ "$WALLTIME_HOURS" =~ ^[0-9]+$ ]]; then
        echo -e "${RED}Error: walltime_hours must be a number${NC}"
        exit 1
    fi

    if [ "$WALLTIME_HOURS" -lt 1 ] || [ "$WALLTIME_HOURS" -gt 24 ]; then
        echo -e "${RED}Error: walltime_hours must be between 1 and 24 for production${NC}"
        echo "Crux workq-route queue supports up to 24 hours"
        exit 1
    fi
fi

# Format walltime as HH:MM:SS for PBS
WALLTIME_PBS=$(printf "%02d:00:00" $WALLTIME_HOURS)

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
echo "  Number of nodes: $NUM_NODES"
echo "  Workers per node: $WORKERS_PER_NODE"
echo "  Walltime: ${WALLTIME_HOURS}h (${WALLTIME_PBS})"
echo "  PBS script: $PBS_SCRIPT"
if [ "$NO_MOVE_RECIPES" = "true" ]; then
    echo -e "  Recipe movement: ${YELLOW}DISABLED (--no-move active)${NC}"
else
    echo "  Recipe movement: ENABLED (moved to processed/ after success)"
fi
echo ""

# Calculate parallelism for this configuration
echo -e "${GREEN}Expected parallelism:${NC}"
TOTAL_RANKS=$((NUM_NODES * WORKERS_PER_NODE))
EXPECTED_WORKERS=$((TOTAL_RANKS - 2))  # Minus scheduler and client
echo "  Total MPI ranks: $TOTAL_RANKS"
echo "  Dask workers: $EXPECTED_WORKERS (2 ranks used for scheduler + client)"

# Calculate expected speedup
if [ "$EXPECTED_WORKERS" -le 8 ]; then
    SPEEDUP=$EXPECTED_WORKERS
elif [ "$EXPECTED_WORKERS" -le 256 ]; then
    SPEEDUP=$((EXPECTED_WORKERS * 75 / 100))
    echo "  Expected speedup: ~${SPEEDUP}x vs single worker (75% efficiency)"
else
    SPEEDUP=$((EXPECTED_WORKERS * 60 / 100))
    echo "  Expected speedup: ~${SPEEDUP}x vs single worker (60% efficiency)"
fi
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

# Submit job with WORKERS_PER_NODE and NO_MOVE_RECIPES variables, node count, and walltime overrides
echo -e "${GREEN}Submitting job...${NC}"
JOB_ID=$(qsub -v WORKERS_PER_NODE=${WORKERS_PER_NODE},NO_MOVE_RECIPES=${NO_MOVE_RECIPES} -l select=${NUM_NODES}:system=crux -l walltime=${WALLTIME_PBS} "$PBS_SCRIPT")

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
