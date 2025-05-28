from utils.sudo import sudo_wrap

def run(host, user, password, args, executor, become=False):
    """Idempotent file module for creating files, directories, symlinks"""
    
    path = args.get("path")
    if not path:
        return {"host": host, "output": "", "error": "Path is required for file module"}
    
    state = args.get("state", "file")
    mode = args.get("mode")
    owner = args.get("owner")
    group = args.get("group")
    content = args.get("content")
    src = args.get("src")  # For symlinks
    
    commands = []

    # Base condition checks for idempotency
    if state == "directory":
        commands.append(f"test -d {path} || mkdir -p {path}")
    elif state == "file":
        if content:
            # Only update if content differs
            commands.append(f"echo '{content}' | cmp -s - {path} || echo '{content}' > {path}")
        else:
            commands.append(f"test -f {path} || touch {path}")
    elif state == "absent":
        commands.append(f"test ! -e {path} || rm -rf {path}")
    elif state == "link":
        if not src:
            return {"host": host, "output": "", "error": "src is required for symlink"}
        commands.append(f"test -L {path} && [ \"$(readlink {path})\" = \"{src}\" ] || ln -sf {src} {path}")
    else:
        return {"host": host, "output": "", "error": f"Unknown state '{state}' for file module"}

    # Permissions and ownership (only if not absent)
    if state != "absent":
        if mode:
            commands.append(f"test \"$(stat -c %a {path})\" = \"{mode}\" || chmod {mode} {path}")
        
        if owner:
            commands.append(f"test \"$(stat -c %U {path})\" = \"{owner}\" || chown {owner} {path}")
        if group:
            commands.append(f"test \"$(stat -c %G {path})\" = \"{group}\" || chgrp {group} {path}")
    
    
    if become:
        commands = [sudo_wrap(cmd) for cmd in commands]

    full_command = " && ".join(commands)
    
    return executor.run_command(host, user, password, full_command)
