from utils.sudo import sudo_wrap

def run(host, user, password, args, executor, become=False):
    """Systemd module for service management"""
    
    name = args.get("name")
    if not name:
        return {"host": host, "output": "", "error": "Service name is required"}
    
    state = args.get("state")
    enabled = args.get("enabled")
    daemon_reload = args.get("daemon_reload", False)
    
    commands = []
    
    if daemon_reload:
        commands.append("systemctl daemon-reload")
    
    if state:
        if state == "started":
            commands.append(f"systemctl start {name}")
        elif state == "stopped":
            commands.append(f"systemctl stop {name}")
        elif state == "restarted":
            commands.append(f"systemctl restart {name}")
        elif state == "reloaded":
            commands.append(f"systemctl reload {name}")
    
    if enabled is not None:
        if enabled:
            commands.append(f"systemctl enable {name}")
        else:
            commands.append(f"systemctl disable {name}")
    
    if not commands:
        return {"host": host, "output": "", "error": "No action specified for systemd module"}
    
    if become:
        commands = [sudo_wrap(cmd) for cmd in commands]

    full_command = " && ".join(commands)
    
    return executor.run_command(host, user, password, full_command)
