import os
import posixpath
import paramiko

def file_checksum(host, user, password, path, executor):
    # Run 'sha256sum' on remote file and return checksum or None if no file
    cmd = f"sha256sum {path} || echo 'FILE_NOT_FOUND'"
    result = executor.run_command(host, user, password, cmd)
    if "FILE_NOT_FOUND" in result["output"] or result["error"]:
        return None
    return result["output"].split()[0]

def run(host, user, password, args, executor, become=False):
    src = args.get("src")
    dest = args.get("dest")
    mode = args.get("mode")
    owner = args.get("owner")
    group = args.get("group")

    result = {
        "host": host,
        "output": "",
        "error": ""
    }

    if not src or not dest:
        result["error"] = "Missing 'src' or 'dest' in copy module args"
        return result

    if not os.path.exists(src):
        result["error"] = f"Source file '{src}' does not exist"
        return result

    import hashlib
    def local_checksum(filepath):
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            h.update(f.read())
        return h.hexdigest()
        
    local_sum = local_checksum(src)

    remote_sum = file_checksum(host, user, password, dest, executor)

    if remote_sum == local_sum:
        return {"host": host, "output": "File already up-to-date, skipping copy", "error": ""}


    temp_dest = f"/tmp/{os.path.basename(dest)}"

    try:
        transport = paramiko.Transport((host, 22))
        transport.connect(username=user, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.put(src, temp_dest)
        sftp.close()
        transport.close()
        result["output"] = f"Copied '{src}' to '{dest}'"
    except Exception as e:
        result["error"] = f"SFTP copy failed: {e}"
        return result

    # Move file from temp to final destination with sudo
    mv_cmd = f"mv {temp_dest} {dest}"
    if become:
        mv_cmd = f"sudo {mv_cmd}"
    mv_result = executor.run_command(host, user, password, mv_cmd)
    result["output"] += f"\n{mv_result.get('output', '')}"
    if mv_result.get("error"):
        result["error"] += f"\nmove error: {mv_result['error']}"

    # Set permissions if specified
    if mode:
        cmd = f"chmod {mode} {dest}"
        if become:
            cmd = f"sudo {cmd}"
        chmod_result = executor.run_command(host, user, password, cmd)
        result["output"] += f"\n{chmod_result.get('output', '')}"
        if chmod_result.get("error"):
            result["error"] += f"\nchmod error: {chmod_result['error']}"

    if owner or group:
        chown_str = f"{owner or ''}:{group or ''}"
        cmd = f"chown {chown_str} {dest}"
        if become:
            cmd = f"sudo {cmd}"
        chown_result = executor.run_command(host, user, password, cmd)
        result["output"] += f"\n{chown_result.get('output', '')}"
        if chown_result.get("error"):
            result["error"] += f"\nchown error: {chown_result['error']}"

    return result
