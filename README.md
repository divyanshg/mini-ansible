# mini-ansible

**mini-ansible** is a lightweight, Ansible-inspired automation tool that allows you to provision, configure, and deploy to remote Linux systems over SSH using simple YAML playbooks.

<p align="center">
  ⚙️ Provisioning &nbsp;&nbsp; 📦 Configuration Management &nbsp;&nbsp; 🚀 Deployment &nbsp;&nbsp; 🔐 SSH-based &nbsp;&nbsp; ✨ Lightweight
</p>

---

## 🚀 Features

- **Playbook-based execution** with easy-to-read YAML syntax
- **SSH-based remote command execution** using `paramiko`
- Basic support for **modules** like `shell`, `copy` and more
- **`become: true`** support for running commands with sudo
- Group-based **inventory support** using INI-style files
- Parallel execution using Python's `ThreadPoolExecutor`
- **Idempotent-friendly architecture** (basic support)
- CLI interface: `mini-ansible run <playbook.yaml> --inventory <inventory.ini>`

---

## 📁 Example Inventory File (`inventory.ini`)

```ini
[webservers]
192.168.1.10 ubuntu password
192.168.1.11 ubuntu password

[dbservers]
192.168.1.20 root rootpass
```

## 📘 Example Playbook (`webserver.yaml`)

```yaml
- name: Webserver Setup
  hosts: webservers
  tasks:
    - name: Update apt cache
      become: true
      module: shell
      args:
        cmd: sudo apt-get update -y
        
    - name: Install Apache
      become: true
      module: shell
      args:
        cmd: sudo apt-get install apache2 -y
        
    - name: Copy homepage
      become: true
      module: copy
      args:
        src: ./examples/config/index.html
        dest: /var/www/html/index.html
        mode: 0644
```

## 🛠️ Modules Supported

| Module | Description |
|--------|-------------|
| `apt` | Run apt commands |
| `yum` | Run yum commands |
| `shell` | Run shell commands |
| `copy` | Copy files to remote systems |
| `file` | Run file based commands |
| `git` | Run git commands |
| `pip` | Run pip commands |
| `service` | Run linux service's related commands |
| `user` | Run linux user's related commands |

Additional modules can be added under the `modules/` directory.

---

## 🧑‍💻 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/divyanshg/mini-ansible.git
cd mini-ansible
```

### 2. Install dependencies

I recommend using `uv`:

```bash
uv venv
source ./venv/bin/activate
uv sync
```

### 4. Run a playbook

```bash
uv run cli.py run ./examples/basics/basic-setup.yaml --inventory ./examples/inventory.ini
```

---

## 📦 Project Structure

```bash
mini-ansible/
├── core/
│   ├── inventory.py     # Inventory parser with group support
│   ├── executor.py      # SSH command and file handling
│   ├── task_runner.py   # Module loader and playbook runner
├── modules/
│   ├── shell.py         # Shell command executor
│   └── copy.py          # File copy with mode and become
├── examples/
│   ├── inventory.ini
│   ├── basics/
│   ├── advanced/
│   └── config/
│       └── index.html
├── utils/
│      └── sudo.py
├── cli.py             # CLI tool setup
├── __main__.py #main entry point file             
└── README.md
```

---

## ❗ Limitations

- No advanced error recovery or retry logic yet
- No advanced templating support (like Jinja2 in Ansible)
- Idempotency is up to the module logic
- No handler/event support yet

---

## 🧩 Roadmap Ideas

- ✔️ Group-based host filtering
- 🔜 Templating support
- 🔜 File diffing for idempotent copy
- 🔜 Service management module
- 🔜 Facts

---

## 📄 License

MIT — use it freely, contribute if you can 🤝

---

## 🤝 Contributing

Feel free to fork, submit pull requests, or suggest features!

---

## ⭐ Star if you like it!

If this project helps you learn or automate faster, give it a ⭐ on GitHub!