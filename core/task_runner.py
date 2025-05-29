from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import yaml
import importlib
import re
import os
import threading
import time
import signal
from collections import defaultdict
from . import executor

def normalize_task_syntax(task):
    """
    Normalize task syntax to support both:
    1. module: shell + args: {...}
    2. shell: {...} (direct module syntax)
    
    Returns the task in normalized format with 'module' and 'args' keys.
    """
    # If task already has 'module' key, return as-is
    if 'module' in task:
        return task.copy()
    
    # List of known modules - you can expand this list
    known_modules = {
        'apt', 'yum', 'shell', 'copy', 'file', 'git', 'pip', 
        'service', 'user', 'wait_for', 'systemd', 'template'
    }
    
    # Look for direct module syntax
    for key, value in task.items():
        if key in known_modules:
            # Found a direct module syntax
            normalized_task = task.copy()
            
            # Remove the direct module key and set up normalized format
            del normalized_task[key]
            normalized_task['module'] = key
            
            # Handle different value types for the module
            if isinstance(value, dict):
                # shell: {cmd: "echo hello"}
                normalized_task['args'] = value
            elif isinstance(value, str):
                # shell: "echo hello" -> shell: {cmd: "echo hello"}
                if key in ['shell', 'command', 'raw']:
                    normalized_task['args'] = {'cmd': value}
                elif key == 'apt':
                    normalized_task['args'] = {'name': value, 'state': 'present'}
                elif key == 'yum':
                    normalized_task['args'] = {'name': value, 'state': 'present'}
                elif key == 'copy':
                    normalized_task['args'] = {'content': value}
                else:
                    # For other modules, put the string value in a generic way
                    normalized_task['args'] = {'value': value}
            elif isinstance(value, list):
                # For modules that might accept lists
                normalized_task['args'] = {'items': value}
            else:
                # Fallback for other types
                normalized_task['args'] = {'value': value}
            
            return normalized_task
    
    # If no known module found, return original task
    # This will likely cause an error later, but that's expected behavior
    return task.copy()

class HostState:
    """Track the state of each host during playbook execution"""
    def __init__(self, ip):
        self.ip = ip
        self.failed = False
        self.unreachable = False
        self.changed = False
        self.task_results = []
        self.lock = threading.Lock()
    
    def mark_failed(self, error_msg):
        with self.lock:
            self.failed = True
            self.task_results.append({"status": "failed", "error": error_msg})
    
    def mark_unreachable(self, error_msg):
        with self.lock:
            self.unreachable = True
            self.task_results.append({"status": "unreachable", "error": error_msg})
    
    def add_result(self, result):
        with self.lock:
            if result.get("changed"):
                self.changed = True
            self.task_results.append(result)
    
    def should_continue(self):
        with self.lock:
            return not (self.failed or self.unreachable)

class PlaybookState:
    """Manage state for all hosts during playbook execution"""
    def __init__(self):
        self.hosts = {}
        self.run_once_tasks = set()  # Track tasks that have run once
        self.lock = threading.Lock()
    
    def get_host_state(self, ip):
        with self.lock:
            if ip not in self.hosts:
                self.hosts[ip] = HostState(ip)
            return self.hosts[ip]
    
    def get_active_hosts(self, host_list):
        """Return only hosts that haven't failed or become unreachable"""
        active = []
        for host in host_list:
            host_state = self.get_host_state(host["ip"])
            if host_state.should_continue():
                active.append(host)
        return active
    
    def should_run_once_task(self, task_id):
        """Check and mark if a run_once task should execute"""
        with self.lock:
            if task_id in self.run_once_tasks:
                return False
            self.run_once_tasks.add(task_id)
            return True

class StreamingOutput:
    """Handle streaming output with thread safety"""
    def __init__(self):
        self.lock = threading.Lock()
    
    def print_host_result(self, host_ip, task_name, result, loop_var=None):
        with self.lock:
            status_indicators = {
                "ok": "✓",
                "changed": "⚡",
                "failed": "✗",
                "unreachable": "⚠",
                "skipped": "⊝"
            }
            
            if result.get("skipped"):
                status = "skipped"
                color = "\033[93m"  # Yellow
            elif result.get("unreachable"):
                status = "unreachable"
                color = "\033[91m"  # Red
            elif result.get("error"):
                status = "failed"
                color = "\033[91m"  # Red
            elif result.get("changed"):
                status = "changed"
                color = "\033[92m"  # Green
            else:
                status = "ok"
                color = "\033[94m"  # Blue
            
            reset_color = "\033[0m"
            indicator = status_indicators.get(status, "?")
            
            loop_info = f" (item={loop_var})" if loop_var else ""
            print(f"{color}{indicator} {host_ip}{reset_color} | {task_name}{loop_info}")
            
            if result.get("skipped"):
                print(f"   SKIPPED: {result.get('msg', 'Condition not met')}")
            else:
                if result.get("output"):
                    for line in result["output"].strip().split('\n'):
                        print(f"   {line}")
                if result.get("error"):
                    print(f"   ERROR: {result['error']}")
            print()

class LoopProcessor:
    """Handle different types of loops"""
    
    @staticmethod
    def process_with_items(items):
        """Process with_items loop"""
        if isinstance(items, list):
            return [{"item": item} for item in items]
        return [{"item": items}]
    
    @staticmethod
    def process_with_sequence(sequence_def):
        """Process with_sequence loop"""
        if isinstance(sequence_def, str):
            # Simple range like "1-5"
            if '-' in sequence_def:
                start, end = map(int, sequence_def.split('-'))
                return [{"item": i} for i in range(start, end + 1)]
        elif isinstance(sequence_def, dict):
            start = sequence_def.get('start', 1)
            end = sequence_def.get('end', 10)
            stride = sequence_def.get('stride', 1)
            format_str = sequence_def.get('format', '%d')
            
            items = []
            for i in range(start, end + 1, stride):
                if '%' in format_str:
                    formatted = format_str % i
                else:
                    formatted = str(i)
                items.append({"item": i, "formatted_item": formatted})
            return items
        
        return [{"item": sequence_def}]
    
    @staticmethod
    def process_loop(task):
        """Process any loop type and return loop items"""
        # Check for different loop types
        if 'with_items' in task:
            return LoopProcessor.process_with_items(task['with_items'])
        elif 'with_sequence' in task:
            return LoopProcessor.process_with_sequence(task['with_sequence'])
        elif 'loop' in task:
            return LoopProcessor.process_with_items(task['loop'])
        
        return None

class VariableProcessor:
    """Handle variable substitution and conditionals"""
    
    def __init__(self, variables=None, host_facts=None, loop_vars=None):
        self.variables = variables or {}
        self.host_facts = host_facts or {}
        self.loop_vars = loop_vars or {}
        # Add some default facts
        self.host_facts.update({
            'mini_ansible_os_family': self._detect_os_family(),
            'mini_ansible_distribution': self._detect_distribution()
        })
    
    def _detect_os_family(self):
        return "Debian"
    
    def _detect_distribution(self):
        return "Ubuntu"
    
    def substitute_variables(self, text):
        """Replace {{ variable }} with actual values"""
        if not isinstance(text, str):
            return text
            
        pattern = r'\{\{\s*([^}]+)\s*\}\}'
        
        def replace_var(match):
            var_name = match.group(1).strip()
            # Check loop vars first, then variables, then host facts
            if var_name in self.loop_vars:
                return str(self.loop_vars[var_name])
            elif var_name in self.variables:
                return str(self.variables[var_name])
            elif var_name in self.host_facts:
                return str(self.host_facts[var_name])
            else:
                return match.group(0)
        
        return re.sub(pattern, replace_var, text)
    
    def process_dict(self, data):
        """Recursively process dictionary for variable substitution"""
        if isinstance(data, dict):
            return {k: self.process_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.process_dict(item) for item in data]
        elif isinstance(data, str):
            return self.substitute_variables(data)
        else:
            return data
    
    def evaluate_condition(self, condition):
        """Evaluate when conditions"""
        if not condition:
            return True
        
        condition = self.substitute_variables(condition)

        operators = {
            '==': lambda a, b: str(a) == str(b),
            '!=': lambda a, b: str(a) != str(b),
            'in': lambda a, b: str(a) in str(b),
            'not in': lambda a, b: str(a) not in str(b)
        }
        
        for op, func in operators.items():
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) == 2:
                    left = parts[0].strip().strip('"\'')
                    right = parts[1].strip().strip('"\'')
                    return func(left, right)
        
        return bool(condition)

def load_playbook(file_path):
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def run_task_with_timeout(task_func, timeout_seconds):
    """Run a task with timeout"""
    import concurrent.futures
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(task_func)
        try:
            return future.result(timeout=timeout_seconds)
        except concurrent.futures.TimeoutError:
            return {
                "output": "",
                "error": f"Task timed out after {timeout_seconds} seconds",
                "timeout": True
            }

def run_single_task_iteration(task, host, play_vars=None, task_vars=None, global_become=None, 
                            playbook_state=None, streaming_output=None, loop_vars=None, timeout=None):
    """Run a single iteration of a task (used for loops and regular tasks)"""
    
    host_ip = host["ip"]
    host_state = playbook_state.get_host_state(host_ip) if playbook_state else None
    
    # Check if host should be skipped due to previous failures
    if host_state and not host_state.should_continue():
        return {
            "host": host_ip,
            "output": "",
            "error": "Host skipped due to previous failure",
            "skipped": True,
            "unreachable": host_state.unreachable
        }
    
    # NORMALIZE TASK SYNTAX FIRST - before any processing
    normalized_task = normalize_task_syntax(task)
    
    # Merge variables: play_vars < task_vars < loop_vars
    all_vars = {}
    if play_vars:
        all_vars.update(play_vars)
    if task_vars:
        all_vars.update(task_vars)
    
    # Initialize variable processor with loop variables
    var_processor = VariableProcessor(all_vars, {
        "mini_ansible_host": host["ip"],
        "mini_ansible_user": host["username"],
        "mini_ansible_host_group": host["group"],
        "mini_ansible_password": host["password"]
    }, loop_vars)
    
    # Process normalized task for variable substitution
    processed_task = var_processor.process_dict(normalized_task)
    
    # Check conditions
    when_condition = processed_task.get("when")
    if not var_processor.evaluate_condition(when_condition):
        result = {
            "host": host_ip,
            "output": "",
            "error": "",
            "skipped": True,
            "msg": "Skipped due to when condition"
        }
        
        # Stream output immediately
        if streaming_output:
            loop_var = loop_vars.get("item") if loop_vars else None
            streaming_output.print_host_result(host_ip, task.get("name", "unnamed task"), result, loop_var)
        
        return result
    
    # Now we're guaranteed to have 'module' and 'args' keys
    module_name = processed_task["module"]
    args = processed_task.get("args", {})
    become = processed_task.get("become", global_become)

    def execute_task():
        try:
            mod = importlib.import_module(f"modules.{module_name}")
        except ModuleNotFoundError:
            return {
                "host": host_ip,
                "output": "",
                "error": f"Module '{module_name}' not found",
                "failed": True
            }

        try:
            return mod.run(
                host["ip"],
                host["username"],
                host["password"],
                args,
                executor,
                become=become
            )
        except Exception as e:
            return {
                "host": host_ip,
                "output": "",
                "error": f"Unexpected error: {str(e)}",
                "failed": True
            }

    # Execute with timeout if specified
    if timeout:
        result = run_task_with_timeout(execute_task, timeout)
        if result.get("timeout"):
            result["failed"] = True
    else:
        result = execute_task()
    
    # Handle module loading errors
    if result.get("failed") and "not found" in result.get("error", ""):
        if host_state:
            host_state.mark_failed(result["error"])
        
        if streaming_output:
            loop_var = loop_vars.get("item") if loop_vars else None
            streaming_output.print_host_result(host_ip, task.get("name", "unnamed task"), result, loop_var)
        
        return result
    
    # Check for connection/execution errors
    if result.get("error"):
        error_msg = result["error"].lower()
        if any(keyword in error_msg for keyword in ["connection", "timeout", "unreachable", "ssh"]):
            result["unreachable"] = True
            if host_state:
                host_state.mark_unreachable(result["error"])
        else:
            result["failed"] = True
            if host_state:
                host_state.mark_failed(result["error"])
    else:
        # Task succeeded
        if host_state:
            host_state.add_result(result)
    
    # Stream output immediately
    if streaming_output:
        loop_var = loop_vars.get("item") if loop_vars else None
        streaming_output.print_host_result(host_ip, task.get("name", "unnamed task"), result, loop_var)
    
    return result

def run_task(task, host, play_vars=None, global_become=None, playbook_state=None, streaming_output=None):
    """Enhanced task runner with loops, run_once, timeout, and task vars"""
    
    # Extract task-level variables
    task_vars = task.get("vars", {})
    
    # Check for timeout
    timeout = task.get("timeout")
    
    # Check if this is a run_once task
    run_once = task.get("run_once", False)
    if run_once:
        task_id = f"{task.get('name', 'unnamed')}_{task.get('module')}"
        if playbook_state and not playbook_state.should_run_once_task(task_id):
            return {
                "host": host["ip"],
                "output": "",
                "error": "",
                "skipped": True,
                "msg": "Skipped due to run_once (already executed on another host)"
            }
    
    # Check for loops
    loop_items = LoopProcessor.process_loop(task)
    
    if loop_items:
        # Execute task for each loop item
        results = []
        for loop_item in loop_items:
            result = run_single_task_iteration(
                task, host, play_vars, task_vars, global_become, 
                playbook_state, streaming_output, loop_item, timeout
            )
            results.append(result)
            
            # If this iteration failed and we're not ignoring errors, stop the loop
            if result.get("failed") and not task.get("ignore_errors", False):
                break
        
        # Return summary result for loops
        failed_count = sum(1 for r in results if r.get("failed"))
        changed_count = sum(1 for r in results if r.get("changed"))
        
        return {
            "host": host["ip"],
            "output": f"Loop completed: {len(results)} iterations, {changed_count} changed, {failed_count} failed",
            "error": "" if failed_count == 0 else f"{failed_count} loop iterations failed",
            "failed": failed_count > 0,
            "changed": changed_count > 0,
            "loop_results": results
        }
    else:
        # Execute single task
        return run_single_task_iteration(
            task, host, play_vars, task_vars, global_become, 
            playbook_state, streaming_output, None, timeout
        )

def run_on_all_hosts(hosts, task, play_vars=None, global_become=False, playbook_state=None, streaming_output=None):
    """Run task on all hosts with streaming output and error handling"""
    
    # Filter out failed/unreachable hosts
    active_hosts = playbook_state.get_active_hosts(hosts) if playbook_state else hosts
    
    if not active_hosts:
        print("No active hosts available for this task")
        return []
    
    # Check for run_once - if so, only run on first host
    if task.get("run_once", False):
        active_hosts = active_hosts[:1]
    
    results = []
    
    with ThreadPoolExecutor(max_workers=min(len(active_hosts), 10)) as executor:
        # Submit all tasks
        future_to_host = {
            executor.submit(
                run_task, 
                task, 
                host, 
                play_vars, 
                global_become, 
                playbook_state, 
                streaming_output
            ): host for host in active_hosts
        }
        
        # Process results as they complete (streaming)
        for future in as_completed(future_to_host):
            host = future_to_host[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                error_result = {
                    "host": host["ip"],
                    "output": "",
                    "error": f"Task execution failed: {str(e)}",
                    "failed": True
                }
                results.append(error_result)
                
                # Mark host as failed
                if playbook_state:
                    host_state = playbook_state.get_host_state(host["ip"])
                    host_state.mark_failed(error_result["error"])
                
                # Stream the error
                if streaming_output:
                    streaming_output.print_host_result(
                        host["ip"], 
                        task.get("name", "unnamed task"), 
                        error_result
                    )
    
    return results

def run_playbook(hosts, playbook):
    """Enhanced playbook runner with proper error handling and streaming"""
    
    playbook_state = PlaybookState()
    streaming_output = StreamingOutput()
    
    for play in playbook:
        target_inventory_group = play.get("hosts", "all")
        play_vars = play.get("vars", {})
        global_become = play.get("become", False)

        print(f"\nPLAY [{play.get('name', 'Unnamed Play')}] ***")
        print("=" * 60)

        # Prepare host list
        if target_inventory_group == "all":
            available_hosts = []
            for group, group_hosts in hosts.items():
                for host in group_hosts:
                    host_with_group = host.copy()
                    host_with_group["group"] = group
                    available_hosts.append(host_with_group)
        else:
            group_hosts = hosts.get(target_inventory_group, [])
            if not group_hosts:
                print(f"No hosts found for group '{target_inventory_group}'")
                print(f"Please make sure that you have group '{target_inventory_group}' in your inventory file")
                continue
            available_hosts = []
            for host in group_hosts:
                host_with_group = host.copy()
                host_with_group["group"] = target_inventory_group
                available_hosts.append(host_with_group)

        # Execute tasks
        for task in play.get("tasks", []):
            task_name = task.get("name", "Unnamed Task")
            print(f"\nTASK [{task_name}] ***")
            print("-" * 40)
            
            results = run_on_all_hosts(
                available_hosts, 
                task, 
                play_vars, 
                global_become, 
                playbook_state, 
                streaming_output
            )
            
            # Print summary for this task
            if results:
                failed_count = sum(1 for r in results if r.get("failed") or r.get("error"))
                unreachable_count = sum(1 for r in results if r.get("unreachable"))
                changed_count = sum(1 for r in results if r.get("changed"))
                skipped_count = sum(1 for r in results if r.get("skipped"))
                ok_count = len(results) - failed_count - unreachable_count - skipped_count
                
                if failed_count > 0 or unreachable_count > 0:
                    print(f"Task failed on {failed_count} hosts, unreachable on {unreachable_count} hosts")
    
    # Print final play recap
    print("\nPLAY RECAP ***")
    print("=" * 60)
    
    for host_ip, host_state in playbook_state.hosts.items():
        status_parts = []
        if host_state.unreachable:
            status_parts.append("\033[91munreachable=1\033[0m")
        elif host_state.failed:
            status_parts.append("\033[91mfailed=1\033[0m")
        else:
            status_parts.append("\033[92mok=1\033[0m")
        
        if host_state.changed:
            status_parts.append("\033[93mchanged=1\033[0m")
        
        print(f"{host_ip:<20} : {' '.join(status_parts)}")

# Utility functions for module development
def parse_module_args(args_string):
    """Parse module arguments from string format"""
    if isinstance(args_string, dict):
        return args_string
    
    result = {}
    if args_string:
        for pair in args_string.split():
            if '=' in pair:
                key, value = pair.split('=', 1)
                result[key] = value
    return result