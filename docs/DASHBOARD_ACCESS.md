# Dask Dashboard Access Guide

Complete guide for accessing and using the Dask dashboard when running XRD processing jobs on ALCF Crux supercomputer.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Access Methods](#access-methods)
4. [Dashboard Features](#dashboard-features)
5. [Interpreting the Dashboard](#interpreting-the-dashboard)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Usage](#advanced-usage)

---

## Overview

### What is the Dask Dashboard?

The Dask dashboard is a real-time web-based monitoring interface that provides visual insights into your distributed processing job. It runs on the scheduler node (port 8787) and is accessible via SSH tunnel from your local machine.

### Why Use the Dashboard?

- **Monitor Progress**: See exactly what workers are doing in real-time
- **Identify Bottlenecks**: Spot performance issues before they waste compute time
- **Debug Errors**: Quickly locate and diagnose failures
- **Optimize Performance**: Understand resource utilization and scaling efficiency
- **Verify Setup**: Confirm all workers are connected and active

### Network Architecture

```
┌─────────────────┐         SSH Tunnel          ┌──────────────────┐
│  Your Laptop    │◄──────────────────────────►│  Crux Login Node │
│  localhost:8787 │  Port Forwarding (8787)     │  crux.alcf.anl.gov│
└─────────────────┘                              └──────────────────┘
                                                          │
                                                          │ Internal Network
                                                          ▼
                                                  ┌──────────────────┐
                                                  │  Compute Node    │
                                                  │  x1921c0s7b0n0   │
                                                  │  Dask Scheduler  │
                                                  │  Port 8787       │
                                                  └──────────────────┘
```

The dashboard runs on a compute node behind the CRUX firewall, so direct access from the internet is not possible. SSH tunneling forwards the port through the login node to your local machine.

---

## Quick Start

### Step 1: Submit Your Job

```bash
# Submit processing job
qsub scripts/submit_crux_production.pbs

# Note the job ID
qstat -u $USER
# Example output: 123456.crux-sched-01
```

### Step 2: Wait for Job to Start

```bash
# Monitor job status
watch -n 10 'qstat -u $USER'

# When status changes from 'Q' (queued) to 'R' (running), proceed
```

### Step 3: Find Compute Node Hostname

```bash
# Extract hostname from job output
grep "Compute Node:" ~/xrd_prod_123456.out

# Example output:
# Compute Node: x1921c0s7b0n0
```

### Step 4: Establish SSH Tunnel

**Option A: Helper Script (Recommended)**
```bash
./scripts/tunnel_dashboard.sh x1921c0s7b0n0
```

**Option B: Manual SSH Command**
```bash
ssh -L 8787:x1921c0s7b0n0:8787 crux.alcf.anl.gov
```

**Option C: Automated Monitoring**
```bash
# Automatically detects running jobs and establishes tunnel
python scripts/auto_tunnel.py
```

### Step 5: Open Dashboard

1. **Keep the tunnel terminal open** (do not close it!)
2. **Open your web browser**
3. **Navigate to:** `http://localhost:8787`

You should see the Dask dashboard interface with real-time metrics.

---

## Access Methods

### Method 1: Manual Tunnel (Best for Single Job)

**Pros:**
- Simple and direct
- Full control over connection
- Works on any system with SSH

**Cons:**
- Requires manual hostname lookup
- Must manually reconnect if tunnel drops

**Usage:**
```bash
# 1. Get hostname from job output
HOSTNAME=$(grep "Compute Node:" ~/xrd_prod_*.out | tail -1 | awk '{print $3}')

# 2. Establish tunnel
ssh -L 8787:${HOSTNAME}:8787 crux.alcf.anl.gov

# 3. Open http://localhost:8787 in browser

# 4. Press Ctrl+C when done to close tunnel
```

### Method 2: Helper Script (Best for Simplicity)

**Pros:**
- Interactive and user-friendly
- Auto-detects hostname from recent jobs
- Clear instructions and error messages
- Handles port conflicts

**Cons:**
- Requires bash shell
- Interactive (not suitable for scripting)

**Usage:**
```bash
# Auto-detect from most recent job
./scripts/tunnel_dashboard.sh

# Or specify hostname explicitly
./scripts/tunnel_dashboard.sh x1921c0s7b0n0

# Follow on-screen prompts
```

**Features:**
- Checks if port 8787 is already in use
- Offers to kill existing processes
- Validates hostname
- Provides clear connection instructions

### Method 3: Automated Monitor (Best for Multiple Jobs)

**Pros:**
- Fully automated - no manual intervention
- Monitors multiple jobs simultaneously
- Auto-reconnects if tunnel drops
- Handles job lifecycle (queued → running → complete)

**Cons:**
- Requires Python
- Runs continuously in foreground

**Usage:**
```bash
# Monitor all XRD jobs
python scripts/auto_tunnel.py

# Monitor specific job
python scripts/auto_tunnel.py --job-id 123456

# Custom poll interval (default: 30s)
python scripts/auto_tunnel.py --poll-interval 60

# Custom SSH host
python scripts/auto_tunnel.py --ssh-host username@crux.alcf.anl.gov
```

**Features:**
- Watches job queue for status changes
- Automatically extracts hostname when job starts
- Establishes tunnel immediately
- Monitors tunnel health and reconnects if needed
- Closes tunnel when job completes
- Graceful shutdown with Ctrl+C

---

## Dashboard Features

### Main Interface Sections

#### 1. Status Bar (Top)
- **Workers**: Number of connected workers (should match `nodes - 2`)
- **Cores**: Total CPU cores available
- **Memory**: Total memory across all workers
- **Processing**: Current processing rate (tasks/second)

#### 2. Task Stream (Center Left)
**What it shows:**
- Horizontal bars representing task execution over time
- Each color represents a different task type
- X-axis: Time
- Y-axis: Worker ID

**What to look for:**
- **Dense, continuous bars**: Good parallelism, workers staying busy
- **Gaps/white space**: Workers idle, insufficient parallelism
- **Many short tasks**: Overhead from task scheduling
- **Few long tasks**: Good chunk size

#### 3. Progress Bar (Top Center)
**What it shows:**
- Overall progress of current computation
- Number of completed vs remaining tasks

**What to look for:**
- Steady progress indicates healthy processing
- Stalled progress suggests a bottleneck or error

#### 4. Workers Table (Bottom Left)
**What it shows:**
- List of all connected workers
- Per-worker CPU and memory usage
- Worker health status

**What to look for:**
- **Green**: Worker healthy and connected
- **Yellow**: Worker under memory pressure
- **Red**: Worker failed or disconnected
- Memory usage should be relatively balanced across workers

#### 5. Memory Usage (Top Right)
**What it shows:**
- Real-time memory consumption per worker
- Historical memory usage over time

**What to look for:**
- **Stable at 50-80%**: Optimal
- **Above 90%**: Risk of out-of-memory errors
- **Frequent spikes to 100%**: Increase nodes or reduce chunk size
- **Uneven distribution**: Possible data skew

#### 6. CPU Utilization (Right)
**What it shows:**
- CPU usage percentage per worker
- Cores actively processing

**What to look for:**
- **80-100%**: Excellent utilization
- **50-80%**: Good utilization
- **Below 50%**: Check for I/O bottlenecks or insufficient parallelism

#### 7. Task Graph (Bottom Right)
**What it shows:**
- Dependency graph of tasks
- Task status (waiting, running, complete, error)

**What to look for:**
- **Green nodes**: Completed tasks
- **Blue nodes**: Running tasks
- **Gray nodes**: Waiting tasks
- **Red nodes**: Failed tasks (investigate immediately!)

---

## Interpreting the Dashboard

### Healthy Processing Patterns

#### Optimal Task Stream
```
Worker 0  ████████████████████████████████████████████████
Worker 1  ████████████████████████████████████████████████
Worker 2  ████████████████████████████████████████████████
Worker 3  ████████████████████████████████████████████████
          └────────────────────────────────────────────────►
                          Time
```
- All workers continuously busy (no gaps)
- Uniform color distribution (balanced task types)
- Minimal white space

#### Optimal Memory Usage
```
Memory (GB)
100% ┤
 80% ┤  ╭────────────────────────╮
 60% ┤  │                        │
 40% ┤  │                        │
 20% ┤  │                        │
  0% ┤──┴────────────────────────┴────►
         Time
```
- Steady at 60-80%
- Smooth curves (no spikes)
- All workers in similar range

### Problem Patterns

#### Insufficient Parallelism
```
Worker 0  ██████    ██████    ██████    ██████    ██████
Worker 1  ██████    ██████    ██████    ██████    ██████
Worker 2  ██████    ██████    ██████    ██████    ██████
Worker 3  ██████    ██████    ██████    ██████    ██████
          └────────────────────────────────────────────────►
```
**Symptoms:**
- Many gaps between tasks
- Workers idle most of the time
- Low overall throughput

**Solution:**
- Reduce chunk size to create more tasks
- In recipe JSON: decrease `spacing` parameter
- In code: reduce Dask chunk dimensions

#### Memory Pressure
```
Memory (GB)
100% ┤     ╭╮    ╭╮    ╭╮
 80% ┤    ╭╯╰╮  ╭╯╰╮  ╭╯╰╮
 60% ┤   ╭╯  ╰──╯  ╰──╯  ╰╮
 40% ┤  ╭╯                 ╰╮
 20% ┤──╯                   ╰──►
```
**Symptoms:**
- Frequent spikes to 90-100%
- Warning messages: "Worker is at 95% memory usage"
- Worker restarts or terminations

**Solution:**
- Increase number of nodes (more workers = less memory per task)
- Reduce chunk size
- Check for memory leaks in processing code

#### I/O Bottleneck
```
Worker 0  ██    ██    ██    ██    ██    (CPU: 30%)
Worker 1  ██    ██    ██    ██    ██    (CPU: 25%)
Worker 2  ██    ██    ██    ██    ██    (CPU: 35%)
Worker 3  ██    ██    ██    ██    ██    (CPU: 28%)
```
**Symptoms:**
- Workers busy but CPU utilization low (<50%)
- Long gaps between task completions
- Task stream shows waiting (gray) tasks

**Solution:**
- Check network/storage performance
- Verify Lustre stripe settings for large datasets
- Consider caching frequently-read data

#### Worker Failures
```
Workers: 30 / 32 connected  ⚠
Worker 15: DISCONNECTED (red)
Worker 22: DISCONNECTED (red)
```
**Symptoms:**
- Workers disappear from dashboard
- Red status in workers table
- Error messages in task graph

**Solution:**
- Check job output for worker errors
- Look for out-of-memory kills
- Verify node health with system admin
- Restart job if failures persist

---

## Troubleshooting

### Problem: Cannot Connect to Dashboard

#### Symptom 1: "Connection Refused"

**Cause:** Dashboard not yet available or tunnel not established

**Solution:**
```bash
# 1. Verify job is running
qstat -u $USER
# Status should be 'R' (running), not 'Q' (queued)

# 2. Check if dashboard started
grep "DASK DASHBOARD ACCESS" ~/xrd_prod_*.out
# Should show hostname and instructions

# 3. Verify SSH tunnel is active
# In tunnel terminal, you should NOT see command prompt
# If you see prompt, tunnel failed to connect

# 4. Test tunnel manually
curl http://localhost:8787/status
# Should return JSON with cluster status
```

#### Symptom 2: "Port 8787 Already in Use"

**Cause:** Another tunnel or service using the port

**Solution:**
```bash
# Option 1: Kill existing process
lsof -ti:8787 | xargs kill -9

# Option 2: Use different local port
ssh -L 8888:x1921c0s7b0n0:8787 crux.alcf.anl.gov
# Then access at http://localhost:8888
```

#### Symptom 3: "SSH Authentication Failed"

**Cause:** Need to authenticate with ALCF credentials

**Solution:**
```bash
# 1. First authenticate interactively
ssh crux.alcf.anl.gov
# Enter password + CRYPTOCard token
# Then exit

# 2. Within ~5 minutes, establish tunnel
ssh -L 8787:x1921c0s7b0n0:8787 crux.alcf.anl.gov
# Should connect without additional prompts
```

### Problem: Dashboard Shows No Workers

#### Symptom: Dashboard loads but shows "Workers: 0"

**Cause:** Workers still initializing or failed to start

**Solution:**
```bash
# 1. Wait 1-2 minutes (workers may still be starting)

# 2. Check job output for worker initialization
grep "Workers ready" ~/xrd_prod_*.out

# 3. Look for MPI errors
grep -i "mpi" ~/xrd_prod_*.out | grep -i error

# 4. Verify expected worker count
# Expected: (Total MPI ranks) - 2
# Example: 256 ranks = 254 workers (minus scheduler + client)

# 5. Check for resource errors
grep -i "memory\|resource\|timeout" ~/xrd_prod_*.out
```

### Problem: Dashboard Becomes Unresponsive

#### Symptom: Dashboard freezes or updates slowly

**Cause:** Scheduler overloaded or network issues

**Solution:**
```bash
# 1. Check if job is still running
qstat -u $USER

# 2. Verify tunnel is still active
ps aux | grep "ssh -L 8787"

# 3. Restart tunnel
# Press Ctrl+C in tunnel terminal
# Re-establish with helper script or manual command

# 4. Reduce scheduler load (if processing new jobs)
# In Dask config, reduce event logging:
export DASK_DISTRIBUTED__SCHEDULER__EVENTS_LOG_LENGTH=100
export DASK_DISTRIBUTED__ADMIN__LOG_LENGTH=100
```

### Problem: Tasks Shown as Failed (Red)

#### Symptom: Red nodes in task graph, error messages

**Cause:** Processing errors in worker code

**Solution:**
```bash
# 1. Click on failed task in dashboard to see error message

# 2. Check job output for stack trace
grep -A 20 "Error\|Exception\|Traceback" ~/xrd_prod_*.out

# 3. Common causes:
#    - Missing input files (check image paths in recipe)
#    - Invalid GSAS-II calibration files
#    - Out of memory (increase nodes)
#    - Corrupted diffraction images

# 4. If isolated failures, Dask will retry automatically
#    If many failures, job may need to be killed and fixed
```

### Problem: Tunnel Drops Unexpectedly

#### Symptom: Dashboard stops updating, browser shows "Connection Lost"

**Cause:** SSH timeout or network interruption

**Solution:**
```bash
# Temporary fix: Restart tunnel manually
./scripts/tunnel_dashboard.sh <hostname>

# Permanent fix: Use auto-monitor script (handles reconnection)
python scripts/auto_tunnel.py --job-id <JOBID>

# Alternative: Configure SSH keep-alive in ~/.ssh/config
cat >> ~/.ssh/config <<EOF
Host crux.alcf.anl.gov
    ServerAliveInterval 60
    ServerAliveCountMax 10
EOF
```

---

## Advanced Usage

### Monitoring Multiple Jobs

If you're running multiple jobs simultaneously:

```bash
# Terminal 1: Job 1 tunnel
ssh -L 8787:nodeA:8787 crux.alcf.anl.gov

# Terminal 2: Job 2 tunnel (different local port)
ssh -L 8788:nodeB:8787 crux.alcf.anl.gov

# Terminal 3: Job 3 tunnel
ssh -L 8789:nodeC:8787 crux.alcf.anl.gov

# Access in browser:
# Job 1: http://localhost:8787
# Job 2: http://localhost:8788
# Job 3: http://localhost:8789
```

Or use the automated monitor:
```bash
python scripts/auto_tunnel.py
# Automatically manages all running XRD jobs
```

### Sharing Dashboard with Team

**WARNING:** The dashboard may contain sensitive file paths and system information. Only share with authorized team members.

**Method 1: Reverse Tunnel (Advanced)**
```bash
# On compute node, create reverse tunnel to login node
ssh -R 8787:localhost:8787 crux-login-01 -N &

# Team members connect to login node
ssh -L 8787:localhost:8787 crux.alcf.anl.gov
```

**Method 2: VNC Session**
```bash
# Use ALCF VNC service (if available) to share desktop
# Contact ALCF support for VNC access
```

### Dashboard Export for Reports

Save dashboard snapshots for documentation:

1. **Screenshot method:**
   - Use browser screenshot tools (F12 → Device Toolbar → Capture Screenshot)

2. **Export data method:**
   ```python
   # In Python console on client node
   from dask.distributed import Client
   client = Client()

   # Export worker info
   import json
   info = client.scheduler_info()
   with open('cluster_info.json', 'w') as f:
       json.dump(info, f, indent=2)

   # Export performance metrics
   client.get_task_stream()  # Returns task timing data
   ```

3. **Automated logging:**
   ```bash
   # Enable performance logging in PBS script
   ENABLE_PROFILING=1

   # Generates performance reports in job output
   ```

### Custom Dashboard Deployment

For persistent dashboard access during development:

```python
# custom_cluster.py - Run on Crux interactively
from dask.distributed import LocalCluster, Client

cluster = LocalCluster(
    n_workers=4,
    threads_per_worker=1,
    dashboard_address=':8787',  # Bind to all interfaces
)

client = Client(cluster)
print(f"Dashboard: {client.dashboard_link}")

# Keep cluster running
import time
while True:
    time.sleep(60)
```

Then tunnel from your laptop:
```bash
ssh -L 8787:crux-compute-XX:8787 crux.alcf.anl.gov
```

---

## Best Practices

### Do's

✓ **Establish tunnel before job completes** - Dashboard is only available while job runs

✓ **Keep tunnel terminal visible** - Helps debug connection issues

✓ **Monitor during first 5 minutes** - Catch initialization problems early

✓ **Check dashboard for large jobs** - Prevent wasting compute time on configuration errors

✓ **Save screenshots** - Document performance for optimization discussions

✓ **Use auto-monitor for overnight runs** - Automatic reconnection if tunnel drops

### Don'ts

✗ **Don't close tunnel terminal** - Dashboard becomes inaccessible

✗ **Don't ignore red tasks** - Failed tasks indicate code/data problems

✗ **Don't ignore memory warnings** - Can cause worker crashes and job failure

✗ **Don't run multiple tunnels to same hostname** - Creates port conflicts

✗ **Don't share dashboard publicly** - May expose sensitive paths/data

---

## Quick Reference

### Essential Commands

```bash
# Check job status
qstat -u $USER

# Find compute node
grep "Compute Node:" ~/xrd_prod_*.out

# Establish tunnel (manual)
ssh -L 8787:HOSTNAME:8787 crux.alcf.anl.gov

# Establish tunnel (helper script)
./scripts/tunnel_dashboard.sh HOSTNAME

# Establish tunnel (auto-monitor)
python scripts/auto_tunnel.py

# Test dashboard accessibility
curl http://localhost:8787/status

# Kill existing tunnel
lsof -ti:8787 | xargs kill -9

# Monitor job output
tail -f ~/xrd_prod_*.out
```

### Dashboard URLs

Once tunnel is established:

- **Main Dashboard**: `http://localhost:8787`
- **Status**: `http://localhost:8787/status`
- **Info**: `http://localhost:8787/info`
- **Workers**: `http://localhost:8787/workers`
- **Task Stream**: `http://localhost:8787/tasks`
- **System**: `http://localhost:8787/system`
- **Profile**: `http://localhost:8787/profile`

### Color Code Reference

**Task Stream:**
- **Blue/Cyan**: Data loading tasks
- **Green**: Computation tasks (GSAS-II fitting)
- **Orange**: Data writing tasks
- **Purple**: Coordination/scheduler tasks
- **Red**: Failed tasks

**Worker Status:**
- **Green**: Healthy, connected
- **Yellow**: Memory pressure (>80%)
- **Orange**: High memory usage (>90%)
- **Red**: Disconnected or failed

---

## Support

### Resources

- **CRUX Deployment Guide**: [docs/CRUX_DEPLOYMENT.md](CRUX_DEPLOYMENT.md)
- **Dask Documentation**: https://docs.dask.org/en/stable/dashboard.html
- **ALCF Support**: [email protected]
- **GitHub Issues**: https://github.com/your-repo/issues

### Common Issues & Solutions

| Issue | Quick Fix |
|-------|-----------|
| Connection refused | Wait 1-2 min for job to start |
| Port in use | `lsof -ti:8787 \| xargs kill -9` |
| No workers | Wait for initialization, check MPI errors |
| Tunnel drops | Use auto-monitor script |
| High memory | Increase nodes or reduce chunk size |
| Low CPU usage | Check for I/O bottleneck |
| Red tasks | Check job output for errors |

---

**Last Updated:** October 2025
**Maintainer:** William Gonzalez
**Version:** 1.4
