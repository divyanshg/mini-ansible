def get_inventory(path="./examples/inventory.ini"):
    inventory = {}
    current_group = None

    with open(path, "r") as inventory_file:
        for line in inventory_file:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current_group = line[1:-1].strip()
                inventory[current_group] = []
            else:
                # Assume line is: ip username password
                ip, username, password = line.split()
                if current_group is None:
                    # Hosts without a group go to 'ungrouped'
                    current_group = "ungrouped"
                    if current_group not in inventory:
                        inventory[current_group] = []
                inventory[current_group].append({
                    "ip": ip,
                    "username": username,
                    "password": password
                })

    return inventory
