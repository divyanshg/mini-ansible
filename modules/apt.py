from utils.sudo import sudo_wrap

def run(host, user, password, args, executor, become=False):
    """apt module with state handling"""
    
    # Handle both single package and list of packages
    packages = args.get("name")
    if isinstance(packages, str):
        packages = [packages]
    elif isinstance(packages, list):
        pass
    else:
        return {"host": host, "output": "", "error": "Package name must be string or list"}
    
    state = args.get("state", "present")
    update_cache = args.get("update_cache", False)
    
    commands = []
    
    # Update cache if requested
    if update_cache:
        commands.append("apt-get update")
    
    # Handle different states
    if state == "present":
        pkg_list = " ".join(packages)
        commands.append(f"apt-get install -y {pkg_list}")
    elif state == "absent":
        pkg_list = " ".join(packages)
        commands.append(f"apt-get remove -y {pkg_list}")
    elif state == "latest":
        pkg_list = " ".join(packages)
        commands.append(f"apt-get install -y --only-upgrade {pkg_list}")
    else:
        return {"host": host, "output": "", "error": f"Unknown state '{state}' for apt module"}
    
    # Combine commands
    if become:
        commands = [sudo_wrap(cmd) for cmd in commands]

    full_command = " && ".join(commands)
    
    return executor.run_command(host, user, password, full_command)
