from utils.sudo import sudo_wrap

def run(host, user, password, args, executor, become=False):
    """Pip module for Python package management"""
    
    name = args.get("name")
    requirements = args.get("requirements")
    virtualenv = args.get("virtualenv")
    state = args.get("state", "present")
    
    if not name and not requirements:
        return {"host": host, "output": "", "error": "Either name or requirements must be specified"}
    
    commands = []
    pip_cmd = "pip3"
    
    # Use virtualenv if specified
    if virtualenv:
        pip_cmd = f"{virtualenv}/bin/pip"
        # Ensure virtualenv exists
        commands.append(f"test -d {virtualenv} || python3 -m venv {virtualenv}")
    
    if requirements:
        if state == "present":
            commands.append(f"{pip_cmd} install -r {requirements}")
        else:
            return {"host": host, "output": "", "error": "Cannot uninstall from requirements file"}
    elif name:
        if state == "present":
            if isinstance(name, list):
                packages = " ".join(name)
            else:
                packages = name
            commands.append(f"{pip_cmd} install {packages}")
        elif state == "absent":
            if isinstance(name, list):
                packages = " ".join(name)
            else:
                packages = name
            commands.append(f"{pip_cmd} uninstall -y {packages}")
    
    if become:
        commands = [sudo_wrap(cmd) for cmd in commands]

    full_command = " && ".join(commands)
    
    return executor.run_command(host, user, password, full_command)
