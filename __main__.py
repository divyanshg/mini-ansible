from core.inventory import get_inventory
from core.task_runner import load_playbook, run_playbook

def main():
    hosts = get_inventory()
    playbook = load_playbook('./examples/basic-setup.yaml')
    run_playbook(hosts, playbook)

if __name__ == "__main__":
    main()
