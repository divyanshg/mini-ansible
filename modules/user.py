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
    append = args.get("append", False)

    commands = []

    if state == "present":
        # Use a shell conditional: if user exists -> modify, else -> create
        check_user_cmd = f"id {name}"
        
        create_parts = ["useradd"]
        if system:
            create_parts.append("--system")
        if shell:
            create_parts.extend(["-s", shell])
        if home:
            create_parts.extend(["-d", home])
        create_parts.append("-m" if create_home else "-M")
        if groups and not append:
            if isinstance(groups, list):
                groups = ",".join(groups)
            create_parts.extend(["-G", groups])
        create_parts.append(name)
        create_cmd = " ".join(create_parts)

        modify_cmd = None
        if groups and append:
            if isinstance(groups, list):
                groups = ",".join(groups)
            modify_cmd = f"usermod -a -G {groups} {name}"

        # Build command: create if user doesn't exist
        combined_cmd = f"{check_user_cmd} || {create_cmd}"
        commands.append(combined_cmd)

        # If user exists and append is requested
        if append and groups:
            commands.append(modify_cmd)

    elif state == "absent":
        cmd = f"userdel -r {name}"
        commands.append(cmd)

    else:
        return {"host": host, "output": "", "error": f"Unknown state '{state}' for user module"}

    if become:
        commands = [sudo_wrap(cmd) for cmd in commands]

    full_command = " && ".join(commands)

    return executor.run_command(host, user, password, full_command)
