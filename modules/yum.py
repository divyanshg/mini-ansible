from utils.sudo import sudo_wrap

def run(host, user, password, args, executor, become=False):
    """YUM module for RedHat/CentOS systems"""
    
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
        commands.append("yum makecache")
    
    # Handle different states
    if state == "present":
        pkg_list = " ".join(packages)
        commands.append(f"yum install -y {pkg_list}")
    elif state == "absent":
        pkg_list = " ".join(packages)
        commands.append(f"yum remove -y {pkg_list}")
    elif state == "latest":
        pkg_list = " ".join(packages)
        commands.append(f"yum update -y {pkg_list}")
    else:
        return {"host": host, "output": "", "error": f"Unknown state '{state}' for yum module"}
    
    if become:
        commands = [sudo_wrap(cmd) for cmd in commands]

    full_command = " && ".join(commands)
    
    return executor.run_command(host, user, password, full_command)
