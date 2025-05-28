# mini-ansible

**A lightweight Ansible-like tool for automating provisioning, configuration management, and application deployment over SSH using simple YAML playbooks.**

---

## 🚀 Overview

`mini-ansible` is a minimal, educational infrastructure automation tool inspired by Ansible. It connects to remote machines via SSH, executes tasks defined in YAML playbooks, and allows you to manage servers without installing agents.

---

## 🧰 Features

✅ Agentless: Uses SSH for all operations  
✅ YAML-based playbooks  
✅ Inventory management with groups and variables  
✅ Task execution via `paramiko`  
✅ Support for basic modules like `shell`, `copy`, `apt`, `service`, and more  
✅ Lightweight and beginner-friendly

---

## ⚠️ Limitations

🔸 Not a full replacement for Ansible  
🔸 Limited OS support (Linux only for now)  
🔸 No role or tag system  
🔸 Minimal error handling and idempotency checks  
🔸 Only supports passwordless SSH (e.g., key-based auth)

This tool is ideal for learning, experimentation, or managing small infrastructure — not yet production-grade.

---

## 📦 Setup Guide

### Prerequisites

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) (fast Python package manager)
- SSH access to target hosts
