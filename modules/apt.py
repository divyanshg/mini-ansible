from utils.sudo import sudo_wrap

def run(host, user, password, args, executor, become=False):
    """apt module with idempotent state handling"""
    
    # Handle both single package and list of packages
    packages = args.get("name")
    if isinstance(packages, str):
        packages = [packages]
    elif isinstance(packages, list):
        pass
    else:
        return {"host": host, "output": "", "error": "Package name must be string or list", "changed": False}
    
    state = args.get("state", "present")
    update_cache = args.get("update_cache", False)
    
    commands = []
    changed = False
    
    # Update cache if requested
    if update_cache:
        commands.append("apt-get update")
        changed = True  # Cache update is always considered a change
    
    # Check current package states
    pkg_status = {}
    for pkg in packages:
        check_cmd = f"dpkg -l {pkg} 2>/dev/null | grep -E '^ii|^rc' || echo 'not-installed'"
        if become:
            check_cmd = sudo_wrap(check_cmd)
        
        result = executor.run_command(host, user, password, check_cmd)
        if result.get("error"):
            return result
        
        output = result.get("output", "").strip()
        if "not-installed" in output:
            pkg_status[pkg] = "absent"
        elif output.startswith("ii"):
            pkg_status[pkg] = "present"
        elif output.startswith("rc"):
            pkg_status[pkg] = "removed-config"  # Removed but config files remain
        else:
            pkg_status[pkg] = "unknown"
    
    # Handle different states
    if state == "present":
        packages_to_install = [pkg for pkg in packages if pkg_status[pkg] in ["absent", "removed-config"]]
        if packages_to_install:
            pkg_list = " ".join(packages_to_install)
            commands.append(f"apt-get install -y {pkg_list}")
            changed = True
            
    elif state == "absent":
        packages_to_remove = [pkg for pkg in packages if pkg_status[pkg] == "present"]
        if packages_to_remove:
            pkg_list = " ".join(packages_to_remove)
            commands.append(f"apt-get remove -y {pkg_list}")
            changed = True
            
    elif state == "latest":
        # For latest, we need to check if updates are available
        packages_to_upgrade = []
        for pkg in packages:
            if pkg_status[pkg] == "absent":
                # Package not installed, will be installed
                packages_to_upgrade.append(pkg)
                changed = True
            elif pkg_status[pkg] == "present":
                # Check if upgrade is available
                check_upgrade_cmd = f"apt list --upgradable 2>/dev/null | grep '^{pkg}/' || echo 'no-upgrade'"
                if become:
                    check_upgrade_cmd = sudo_wrap(check_upgrade_cmd)
                
                result = executor.run_command(host, user, password, check_upgrade_cmd)
                if result.get("error"):
                    return result
                
                if "no-upgrade" not in result.get("output", ""):
                    packages_to_upgrade.append(pkg)
                    changed = True
        
        if packages_to_upgrade:
            # For new packages, use install; for existing, use upgrade
            new_packages = [pkg for pkg in packages_to_upgrade if pkg_status[pkg] == "absent"]
            existing_packages = [pkg for pkg in packages_to_upgrade if pkg_status[pkg] == "present"]
            
            if new_packages:
                pkg_list = " ".join(new_packages)
                commands.append(f"apt-get install -y {pkg_list}")
            
            if existing_packages:
                pkg_list = " ".join(existing_packages)
                commands.append(f"apt-get install -y --only-upgrade {pkg_list}")
    else:
        return {"host": host, "output": "", "error": f"Unknown state '{state}' for apt module", "changed": False}
    
    # If no changes needed, return early
    if not changed:
        return {
            "host": host, 
            "output": f"All packages already in desired state ({state})",
            "error": "",
            "changed": False
        }
    
    # Apply sudo wrapper if needed
    if become:
        commands = [sudo_wrap(cmd) for cmd in commands]

    # Execute commands
    if commands:
        full_command = " && ".join(commands)
        result = executor.run_command(host, user, password, full_command)
        result["changed"] = changed
        return result
    
    return {
        "host": host,
        "output": "No changes needed",
        "error": "",
        "changed": False
    }