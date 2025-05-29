import time
import socket
import subprocess
import os
from utils.sudo import sudo_wrap

def run(host, user, password, args, executor, become=False):
    """
    Wait for conditions to be met
    
    Supported parameters:
    - host: hostname/IP to check (default: current host)
    - port: port number to check
    - path: file path to check for existence
    - timeout: maximum time to wait in seconds (default: 300)
    - delay: initial delay before starting checks (default: 0)
    - sleep: time between retries (default: 1)
    - state: started/stopped/present/absent/drained (default: started)
    - connect_timeout: timeout for individual connection attempts (default: 5)
    """
    
    # Extract parameters
    check_host = args.get("host", host)
    port = args.get("port")
    path = args.get("path")
    timeout = int(args.get("timeout", 300))
    delay = int(args.get("delay", 0))
    sleep_time = int(args.get("sleep", 1))
    state = args.get("state", "started")
    connect_timeout = int(args.get("connect_timeout", 5))
    
    # Validate parameters
    if not port and not path:
        return {
            "host": host,
            "output": "",
            "error": "Either 'port' or 'path' parameter is required",
            "changed": False
        }
    
    # Initial delay
    if delay > 0:
        time.sleep(delay)
    
    start_time = time.time()
    
    while True:
        current_time = time.time()
        elapsed = current_time - start_time
        
        if elapsed >= timeout:
            return {
                "host": host,
                "output": "",
                "error": f"Timeout waiting for condition after {timeout} seconds",
                "changed": False
            }
        
        try:
            if port:
                # Check port connectivity
                result = _check_port(check_host, port, connect_timeout, state)
            elif path:
                # Check file/directory existence
                result = _check_path(host, user, password, path, executor, become, state)
            
            if result["success"]:
                return {
                    "host": host,
                    "output": result["message"],
                    "error": "",
                    "changed": False,
                    "elapsed": int(elapsed)
                }
                
        except Exception as e:
            # Continue trying unless it's the last attempt
            if elapsed + sleep_time >= timeout:
                return {
                    "host": host,
                    "output": "",
                    "error": f"Error during wait: {str(e)}",
                    "changed": False
                }
        
        time.sleep(sleep_time)

def _check_port(host, port, connect_timeout, state):
    """Check if port is open/closed"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(connect_timeout)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        
        port_open = (result == 0)
        
        if state == "started" and port_open:
            return {"success": True, "message": f"Port {port} on {host} is open"}
        elif state == "stopped" and not port_open:
            return {"success": True, "message": f"Port {port} on {host} is closed"}
        elif state == "drained":
            # For drained state, we might want to check if connections are being accepted
            # but existing connections are being closed gracefully
            # This is a simplified check
            return {"success": port_open, "message": f"Port {port} on {host} status checked"}
        else:
            return {"success": False, "message": f"Port {port} on {host} not in expected state"}
            
    except Exception as e:
        if state == "stopped":
            # If we can't connect and we want it stopped, that might be success
            return {"success": True, "message": f"Port {port} on {host} is not accessible (stopped)"}
        return {"success": False, "message": f"Error checking port: {str(e)}"}

def _check_path(host, user, password, path, executor, become, state):
    """Check if file/directory exists"""
    
    # Use test command to check file existence
    if state in ["present", "started"]:
        check_cmd = f"test -e '{path}'"
        expected_success = True
    elif state in ["absent", "stopped"]:
        check_cmd = f"test ! -e '{path}'"
        expected_success = True
    else:
        return {"success": False, "message": f"Unsupported state '{state}' for path checking"}
    
    if become:
        check_cmd = sudo_wrap(check_cmd)
    
    result = executor.run_command(host, user, password, check_cmd)
    
    # Check exit code (test command returns 0 for true, 1 for false)
    # We need to determine success based on the command output/error
    command_succeeded = not result.get("error") or "exit status 0" in result.get("error", "")
    
    if command_succeeded == expected_success:
        if state in ["present", "started"]:
            return {"success": True, "message": f"Path {path} exists"}
        else:
            return {"success": True, "message": f"Path {path} does not exist"}
    else:
        return {"success": False, "message": f"Path {path} not in expected state"}