def run(host, user, password, args, executor, become=False):
    command = args.get("cmd")
    if not command:
        return {
            "host": host,
            "output": "",
            "error": "Missing 'cmd' argument for shell module"
        }
    
    if become:
        command = f"sudo {command}"

    return executor.run_command(host, user, password, command)
