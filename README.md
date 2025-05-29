# mini-ansible

**mini-ansible** is a lightweight, Ansible-inspired automation tool that allows you to provision, configure, and deploy to remote Linux systems over SSH using simple YAML playbooks.

<p align="center">
  ⚙️ Provisioning &nbsp;&nbsp; 📦 Configuration Management &nbsp;&nbsp; 🚀 Deployment &nbsp;&nbsp; 🔐 SSH-based &nbsp;&nbsp; ✨ Lightweight
</p>

---

## 🚀 Features

- **Playbook-based execution** with easy-to-read YAML syntax
- **SSH-based remote command execution** using `paramiko`
- **Idempotent operations** - modules check current state before making changes
- **Advanced error handling** with fail-fast behavior and host state tracking
- **Real-time streaming output** with color-coded status indicators
- **Loop support** - `with_items`, `with_sequence`, and `loop` constructs
- **Task-level variables** and variable hierarchy management
- **Run-once tasks** for operations that should execute on only once
- **Timeout handling** for long-running tasks
- Basic support for **modules** like `shell`, `copy`, `apt`, `wait_for` and more
- **`become: true`** support for running commands with sudo
- Group-based **inventory support** using INI-style files
- **Parallel execution** using Python's `ThreadPoolExecutor`
- **Play recap** with comprehensive execution summaries
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
  vars:
    packages:
      - apache2
      - nginx
  tasks:
    - name: Update apt cache
      become: true
      module: apt
      args:
        update_cache: true
        
    - name: Install web servers
      become: true
      module: apt
      args:
        name: "{{ item }}"
        state: present
      with_items: "{{ packages }}"
        
    - name: Copy homepage
      become: true
      module: copy
      args:
        src: ./examples/config/index.html
        dest: /var/www/html/index.html
        mode: 0644
        
    - name: Wait for Apache to be ready
      module: wait_for
      args:
        port: 80
        timeout: 30
        
    - name: One-time configuration
      run_once: true
      module: shell
      args:
        cmd: echo "Configuration applied once"
```

## 🛠️ Modules Supported

| Module | Description | Idempotent |
|--------|-------------|------------|
| `apt` | Package management with state checking | ✅ |
| `yum` | Run yum commands | ❌ |
| `shell` | Run shell commands | ❌ |
| `copy` | Copy files to remote systems | ✅ |
| `file` | Run file based commands | ✅ |
| `git` | Run git commands | ❌ |
| `pip` | Run pip commands | ❌ |
| `service` | Run linux service's related commands | ✅ |
| `user` | Run linux user's related commands | ✅ |
| `wait_for` | Wait for conditions (ports, files) | ✅ |

Additional modules can be added under the `modules/` directory.

---

## 🔄 Loop Support

mini-ansible supports various loop constructs:

```yaml
# with_items
- name: Install packages
  module: apt
  args:
    name: "{{ item }}"
    state: present
  with_items:
    - nginx
    - apache2

# with_sequence  
- name: Create users
  module: user
  args:
    name: "user{{ item }}"
  with_sequence: start=1 end=3

# loop (modern syntax)
- name: Copy files
  module: copy
  args:
    src: "{{ item.src }}"
    dest: "{{ item.dest }}"
  loop:
    - { src: "file1.txt", dest: "/tmp/file1.txt" }
    - { src: "file2.txt", dest: "/tmp/file2.txt" }
```

---

## ⚡ Real-time Output

mini-ansible provides immediate feedback with color-coded status indicators:

- ✅ **OK** - Task completed successfully
- ⚡ **CHANGED** - Task made changes to the system  
- ❌ **FAILED** - Task failed to execute
- ⚠️ **UNREACHABLE** - Host connection failed
- ⊝ **SKIPPED** - Task was skipped

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
│   ├── state.py         # Host and playbook state management
│   └── output.py        # Streaming output handling
├── modules/
│   ├── shell.py         # Shell command executor
│   ├── copy.py          # File copy with mode and become
│   ├── apt.py           # Idempotent package management
│   └── wait_for.py      # Wait for conditions
├── examples/
│   ├── inventory.ini
│   ├── basics/
│   ├── advanced/
│   └── config/
│       └── index.html
├── utils/
│   ├── sudo.py          # Sudo handling utilities
│   └── loops.py         # Loop processing logic
├── cli.py               # CLI tool setup
├── __main__.py          # Main entry point file             
└── README.md
```

---

## 🎯 Advanced Features

### Idempotent Operations
The APT module now checks current system state before making changes:
- Only installs packages that aren't already present
- Only removes packages that are currently installed  
- Only upgrades packages with available updates
- Returns change status for accurate reporting

### Error Handling & Host Management
- **Fail-fast behavior**: Failed hosts are excluded from subsequent tasks
- **Connection vs execution errors**: Distinguishes between unreachable hosts and task failures
- **Thread-safe operations**: Safe concurrent execution across multiple hosts

### Variable Hierarchy
Variables are resolved in order of precedence:
1. Loop variables (`item`)
2. Task-level variables  
3. Play-level variables

---

## ❗ Limitations

- Limited idempotency (currently only in few modules)
- No advanced templating support (like Jinja2 in Ansible)
- No handler/event support yet
- Basic facts gathering

---

## 🧩 Roadmap Ideas

- ✅ Group-based host filtering
- ✅ Idempotent package management
- ✅ Loop constructs and variable hierarchy
- ✅ Real-time output and error handling  
- ✅ Timeout and wait_for support
- 🔜 More idempotent modules
- 🔜 Templating support (Jinja2)
- 🔜 Handler and notification support
- 🔜 Facts gathering
- 🔜 Vault support for secrets
- 🔜 Service management module

---

## 📄 License

MIT — use it freely, contribute if you can 🤝

---

## 🤝 Contributing

Feel free to fork, submit pull requests, or suggest features!

---

## ⭐ Star if you like it!

If this project helps you learn or automate faster, give it a ⭐ on GitHub!