def run(host, user, password, args, executor, become=False):
    service = args.get("name")
    state = args.get("state")

    if state not in ["start", "stop", "restart"]:
        return {"error": f"Invalid state '{state}' for service module"}

    command = f"systemctl {state} {service}"

    if become:
        command = f"sudo {command}"
    return executor.run_command(host, user, password, command)
