from utils.sudo import sudo_wrap

def run(host, user, password, args, executor, become=False):
    """User module for managing system users"""
    
    name = args.get("name")
    if not name:
        return {"host": host, "output": "", "error": "Name is required for user module"}
    
    state = args.get("state", "present")
    shell = args.get("shell")
    home = args.get("home")
    create_home = args.get("create_home", True)
    system = args.get("system", False)
    groups = args.get("groups")
    
    commands = []
    
    if state == "present":
        cmd_parts = []
        if become:
            cmd_parts.append("sudo")
        
        cmd_parts.append("useradd")
        
        if system:
            cmd_parts.append("--system")
        
        if shell:
            cmd_parts.extend(["-s", shell])
        
        if home:
            cmd_parts.extend(["-d", home])
        
        if create_home:
            cmd_parts.append("-m")
        else:
            cmd_parts.append("-M")
        
        if groups:
            if isinstance(groups, list):
                groups = ",".join(groups)
            cmd_parts.extend(["-G", groups])
        
        cmd_parts.append(name)
        
        # Check if user exists first
        commands.append(f"id {name} || {' '.join(cmd_parts)}")
        
    elif state == "absent":
        cmd = f"userdel -r {name}"
        if become:
            cmd = f"sudo {cmd}"
        commands.append(cmd)
    else:
        return {"host": host, "output": "", "error": f"Unknown state '{state}' for user module"}
    
    if become:
        commands = [sudo_wrap(cmd) for cmd in commands]
        
    full_command = " && ".join(commands)

    return executor.run_command(host, user, password, full_command)
