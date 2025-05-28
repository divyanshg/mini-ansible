import paramiko
from paramiko.ssh_exception import SSHException, AuthenticationException, NoValidConnectionsError
import socket
from concurrent.futures import ThreadPoolExecutor
import yaml

def get_inventory():
    inventroy_file = open("./inventory.txt", "r")
    host_lines = inventroy_file.readlines()

    hosts = []

    for line in host_lines:
        ip, username, password = line.strip().split()
        hosts.append({
            "ip": ip,
            "username": username,
            "password": password
        })

    return hosts

def load_playbook(file_path):
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

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

def run_on_host(host, command):
    return run_command(
        host["ip"],
        host["username"],
        host["password"],
        command
    )

def run_on_all_hosts(hosts, command):
    results = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(run_on_host, host, command) for host in hosts]

        for future in futures:
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print("Error:", e)

    return results

def run_playbook(hosts, playbook):
    for task in playbook:
        print(f"\n============================================ [ Task: {task['name']} ] ============================================")
        command = task['command']
        results = run_on_all_hosts(hosts, command)

        for result in results:
            print(f"HOST: {result["host"]}")
            print(result["output"] + "\n")
def main():
    hosts = get_inventory()
    playbook = load_playbook('./playbook.yaml')
    run_playbook(
        hosts,
        playbook
    )

if __name__ == "__main__":
    main()
