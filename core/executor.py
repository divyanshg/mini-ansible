import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException, NoValidConnectionsError
import socket

def run_command(host, user, password, command):
    result = {
        "host": host,
        "output": "",
        "error": ""
    }

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(hostname=host, username=user, password=password, timeout=10)
        stdin, stdout, stderr = ssh.exec_command(command)
        result["output"] = stdout.read().decode().strip()
        result["error"] = stderr.read().decode().strip()

    except AuthenticationException:
        result["error"] = f"Authentication failed for host {host}."
    except NoValidConnectionsError as e:
        result["error"] = f"Connection failed for host {host}: {e}"
    except socket.timeout:
        result["error"] = f"Connection to host {host} timed out."
    except SSHException as e:
        result["error"] = f"SSH error on host {host}: {e}"
    except Exception as e:
        result["error"] = f"Unexpected error on host {host}: {e}"
    finally:
        ssh.close()

    return result
