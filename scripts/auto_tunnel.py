#!/usr/bin/env python3
"""
Automated Dask Dashboard SSH Tunnel
====================================
Monitors CRUX job queue and automatically establishes SSH tunnel
to Dask dashboard when job starts running.

Features:
- Watches job queue for your jobs
- Detects when job transitions from queued to running
- Extracts compute node hostname from job output
- Establishes SSH tunnel automatically
- Monitors job status and closes tunnel when job completes
- Handles reconnection if tunnel drops

Usage:
    # Monitor all your jobs
    python scripts/auto_tunnel.py

    # Monitor specific job
    python scripts/auto_tunnel.py --job-id 123456

    # Custom SSH host
    python scripts/auto_tunnel.py --ssh-host username@crux.alcf.anl.gov

Author: William Gonzalez
Date: October 2025
"""

import argparse
import subprocess
import time
import re
import os
import sys
from pathlib import Path
from typing import Optional, Dict, List
import signal


class DashboardTunnelManager:
    """Manages SSH tunnels to Dask dashboard on CRUX compute nodes."""

    def __init__(
        self,
        ssh_host: str = "crux.alcf.anl.gov",
        dashboard_port: int = 8787,
        poll_interval: int = 30,
        job_id: Optional[str] = None,
    ):
        self.ssh_host = ssh_host
        self.dashboard_port = dashboard_port
        self.poll_interval = poll_interval
        self.target_job_id = job_id
        self.tunnel_process = None
        self.monitored_jobs = {}  # job_id -> {status, hostname, tunnel_pid}
        self.running = True

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print("\n\nReceived shutdown signal. Cleaning up tunnels...")
        self.running = False
        self.cleanup_tunnels()
        sys.exit(0)

    def get_user_jobs(self) -> List[Dict[str, str]]:
        """Get list of user's jobs from qstat."""
        try:
            result = subprocess.run(
                ["qstat", "-u", os.environ.get("USER", "")],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                print(f"Warning: qstat failed: {result.stderr}")
                return []

            jobs = []
            for line in result.stdout.split("\n"):
                # Parse qstat output: JobID.server  JobName  User  Queue  Status
                if line.strip() and not line.startswith("Job id") and not line.startswith("-"):
                    parts = line.split()
                    if len(parts) >= 5:
                        job_id = parts[0].split(".")[0]  # Remove .server suffix
                        job_name = parts[1]
                        status = parts[4]  # Q=queued, R=running, C=complete

                        # Filter for XRD jobs
                        if "xrd" in job_name.lower():
                            jobs.append({
                                "id": job_id,
                                "name": job_name,
                                "status": status,
                            })

            return jobs

        except subprocess.TimeoutExpired:
            print("Warning: qstat timed out")
            return []
        except Exception as e:
            print(f"Error getting job list: {e}")
            return []

    def get_compute_node_hostname(self, job_id: str) -> Optional[str]:
        """Extract compute node hostname from job output file."""
        # Try common output file locations
        output_patterns = [
            f"{os.environ.get('HOME', '~')}/xrd_prod_{job_id}.out",
            f"{os.environ.get('HOME', '~')}/xrd_debug_{job_id}.out",
            f"{os.environ.get('HOME', '~')}/xrd_production_{job_id}.out",
        ]

        for pattern in output_patterns:
            output_file = Path(pattern).expanduser()
            if output_file.exists():
                try:
                    with open(output_file, 'r') as f:
                        content = f.read()
                        # Look for "Compute Node: hostname" pattern
                        match = re.search(r'Compute Node:\s+(\S+)', content)
                        if match:
                            hostname = match.group(1)
                            print(f"  Found compute node: {hostname}")
                            return hostname
                except Exception as e:
                    print(f"  Error reading {output_file}: {e}")

        return None

    def establish_tunnel(self, hostname: str) -> Optional[subprocess.Popen]:
        """Establish SSH tunnel to compute node."""
        try:
            print(f"\n{'='*60}")
            print(f"Establishing SSH tunnel to {hostname}:{self.dashboard_port}")
            print(f"{'='*60}")

            cmd = [
                "ssh",
                "-N",  # Don't execute remote command
                "-L", f"{self.dashboard_port}:{hostname}:{self.dashboard_port}",
                self.ssh_host,
            ]

            print(f"Command: {' '.join(cmd)}")
            print(f"\nDashboard will be available at: http://localhost:{self.dashboard_port}")
            print(f"Press Ctrl+C to stop monitoring and close tunnel")
            print(f"{'='*60}\n")

            # Start tunnel in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Give it a moment to establish
            time.sleep(2)

            # Check if tunnel is still alive
            if process.poll() is None:
                print(f"✓ Tunnel established successfully (PID: {process.pid})")
                return process
            else:
                stdout, stderr = process.communicate()
                print(f"✗ Tunnel failed to establish:")
                print(stderr.decode())
                return None

        except Exception as e:
            print(f"✗ Error establishing tunnel: {e}")
            return None

    def check_tunnel_alive(self, process: subprocess.Popen) -> bool:
        """Check if tunnel process is still running."""
        if process is None:
            return False
        return process.poll() is None

    def cleanup_tunnels(self):
        """Close all open tunnels."""
        print("\nClosing tunnels...")
        for job_id, info in self.monitored_jobs.items():
            if "tunnel" in info and info["tunnel"] is not None:
                try:
                    info["tunnel"].terminate()
                    info["tunnel"].wait(timeout=5)
                    print(f"  Closed tunnel for job {job_id}")
                except Exception as e:
                    print(f"  Error closing tunnel for job {job_id}: {e}")

    def monitor(self):
        """Main monitoring loop."""
        print("="*60)
        print("Automated Dask Dashboard Tunnel Monitor")
        print("="*60)
        print(f"SSH Host: {self.ssh_host}")
        print(f"Dashboard Port: {self.dashboard_port}")
        print(f"Poll Interval: {self.poll_interval}s")
        if self.target_job_id:
            print(f"Target Job: {self.target_job_id}")
        else:
            print("Monitoring: All XRD jobs")
        print("="*60)
        print("\nMonitoring job queue... (Press Ctrl+C to stop)\n")

        while self.running:
            try:
                jobs = self.get_user_jobs()

                # Filter to target job if specified
                if self.target_job_id:
                    jobs = [j for j in jobs if j["id"] == self.target_job_id]

                for job in jobs:
                    job_id = job["id"]
                    status = job["status"]

                    # New job detected
                    if job_id not in self.monitored_jobs:
                        print(f"\n[{time.strftime('%H:%M:%S')}] Detected job {job_id} ({job['name']}) - Status: {status}")
                        self.monitored_jobs[job_id] = {
                            "status": status,
                            "hostname": None,
                            "tunnel": None,
                        }

                    # Job transitioned to running
                    if status == "R" and self.monitored_jobs[job_id]["status"] != "R":
                        print(f"\n[{time.strftime('%H:%M:%S')}] Job {job_id} is now RUNNING")
                        self.monitored_jobs[job_id]["status"] = "R"

                        # Try to get hostname and establish tunnel
                        print(f"  Waiting for job to initialize (10s)...")
                        time.sleep(10)  # Give job time to write output

                        hostname = self.get_compute_node_hostname(job_id)
                        if hostname:
                            self.monitored_jobs[job_id]["hostname"] = hostname

                            # Establish tunnel
                            tunnel = self.establish_tunnel(hostname)
                            if tunnel:
                                self.monitored_jobs[job_id]["tunnel"] = tunnel
                        else:
                            print(f"  Could not find compute node hostname yet")
                            print(f"  Will retry on next poll...")

                    # Check if running job needs tunnel established
                    elif status == "R" and self.monitored_jobs[job_id].get("tunnel") is None:
                        if self.monitored_jobs[job_id].get("hostname") is None:
                            hostname = self.get_compute_node_hostname(job_id)
                            if hostname:
                                self.monitored_jobs[job_id]["hostname"] = hostname
                                tunnel = self.establish_tunnel(hostname)
                                if tunnel:
                                    self.monitored_jobs[job_id]["tunnel"] = tunnel

                    # Check tunnel health
                    elif status == "R" and self.monitored_jobs[job_id].get("tunnel"):
                        if not self.check_tunnel_alive(self.monitored_jobs[job_id]["tunnel"]):
                            print(f"\n[{time.strftime('%H:%M:%S')}] Tunnel for job {job_id} died. Reconnecting...")
                            hostname = self.monitored_jobs[job_id]["hostname"]
                            if hostname:
                                tunnel = self.establish_tunnel(hostname)
                                if tunnel:
                                    self.monitored_jobs[job_id]["tunnel"] = tunnel

                    # Job completed
                    elif status == "C" and self.monitored_jobs[job_id]["status"] == "R":
                        print(f"\n[{time.strftime('%H:%M:%S')}] Job {job_id} COMPLETED")
                        if self.monitored_jobs[job_id].get("tunnel"):
                            print(f"  Closing tunnel...")
                            self.monitored_jobs[job_id]["tunnel"].terminate()
                            self.monitored_jobs[job_id]["tunnel"] = None
                        self.monitored_jobs[job_id]["status"] = "C"

                # Sleep until next poll
                time.sleep(self.poll_interval)

            except KeyboardInterrupt:
                print("\n\nShutdown requested...")
                break
            except Exception as e:
                print(f"\nError in monitoring loop: {e}")
                time.sleep(self.poll_interval)

        # Cleanup
        self.cleanup_tunnels()
        print("\nMonitoring stopped.")


def main():
    parser = argparse.ArgumentParser(
        description="Automated SSH tunnel for Dask dashboard on CRUX",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor all XRD jobs
  python scripts/auto_tunnel.py

  # Monitor specific job
  python scripts/auto_tunnel.py --job-id 123456

  # Custom poll interval
  python scripts/auto_tunnel.py --poll-interval 60

  # Custom SSH host
  python scripts/auto_tunnel.py --ssh-host username@crux.alcf.anl.gov
        """
    )

    parser.add_argument(
        "--job-id",
        type=str,
        help="Specific job ID to monitor (default: monitor all XRD jobs)",
    )
    parser.add_argument(
        "--ssh-host",
        type=str,
        default="crux.alcf.anl.gov",
        help="SSH host for tunnel (default: crux.alcf.anl.gov)",
    )
    parser.add_argument(
        "--dashboard-port",
        type=int,
        default=8787,
        help="Dashboard port (default: 8787)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Job queue poll interval in seconds (default: 30)",
    )

    args = parser.parse_args()

    # Create and run monitor
    monitor = DashboardTunnelManager(
        ssh_host=args.ssh_host,
        dashboard_port=args.dashboard_port,
        poll_interval=args.poll_interval,
        job_id=args.job_id,
    )

    monitor.monitor()


if __name__ == "__main__":
    main()
