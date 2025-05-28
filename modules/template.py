from utils.sudo import sudo_wrap

def run(host, user, password, args, executor, become=False):
    """Template module - simplified version"""
    
    src = args.get("src")
    dest = args.get("dest")
    
    if not src or not dest:
        return {"host": host, "output": "", "error": "Both src and dest are required for template module"}
    
    #TODO: use jinja2
    
    commands = [f"cp {src} {dest}"]
    
    mode = args.get("mode")
    owner = args.get("owner")
    group = args.get("group")
    
    if mode:
        commands.append(f"chmod {mode} {dest}")
    
    if owner:
        if group:
            commands.append(f"chown {owner}:{group} {dest}")
        else:
            commands.append(f"chown {owner} {dest}")
    elif group:
        commands.append(f"chgrp {group} {dest}")
    
    if become:
        commands = [sudo_wrap(cmd) for cmd in commands]

    full_command = " && ".join(commands)
    
    return executor.run_command(host, user, password, full_command)