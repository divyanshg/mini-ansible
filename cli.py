import argparse
from core.inventory import get_inventory
from core.task_runner import load_playbook, run_playbook

def main():
    parser = argparse.ArgumentParser(description="Mini Ansible - Lightweight automation tool")
    parser.add_argument("command", choices=["run"], help="What to do")
    parser.add_argument("playbook", help="Path to YAML playbook file")
    parser.add_argument("--inventory", default="./examples/inventory.ini", help="Path to inventory file")

    args = parser.parse_args()

    if args.command == "run":
        hosts = get_inventory(args.inventory)
        playbook = load_playbook(args.playbook)
        run_playbook(hosts, playbook)

if __name__ == "__main__":
    main()