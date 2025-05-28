from utils.sudo import sudo_wrap

def run(host, user, password, args, executor, become=False):
    """Git module for cloning repositories"""
    
    repo = args.get("repo")
    dest = args.get("dest")
    
    if not repo or not dest:
        return {"host": host, "output": "", "error": "Both repo and dest are required for git module"}
    
    version = args.get("version", "HEAD")
    force = args.get("force", False)
    
    commands = []
    
    # Check if git is installed
    commands.append("which git || echo 'Git not installed' && exit 1")
    
    # Clone or update repository
    if force:
        commands.append(f"rm -rf {dest}")
    
    # Check if destination exists and is a git repo
    commands.append(f"""
    if [ -d "{dest}/.git" ]; then
        cd {dest} && git fetch && git reset --hard origin/{version}
    else
        git clone {repo} {dest}
        cd {dest} && git checkout {version}
    fi
    """)
    
    if become:
        commands = [sudo_wrap(cmd) for cmd in commands]

    full_command = " && ".join(commands)
    
    return executor.run_command(host, user, password, full_command)
