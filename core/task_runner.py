from concurrent.futures import ThreadPoolExecutor
import yaml
import importlib
import re
import os
from . import executor

class VariableProcessor:
    """Handle variable substitution and conditionals"""
    
    def __init__(self, variables=None, host_facts=None):
        self.variables = variables or {}
        self.host_facts = host_facts or {}
        # Add some default facts
        self.host_facts.update({
            'mini_ansible_os_family': self._detect_os_family(),
            'mini_ansible_distribution': self._detect_distribution()
        })
    
    def _detect_os_family(self):
        # Simple OS detection - in real implementation will be gathering this from host
        return "Debian"  # Default for now
    
    def _detect_distribution(self):
        return "Ubuntu"  # Default for now
    
    def substitute_variables(self, text):
        """Replace {{ variable }} with actual values"""
        if not isinstance(text, str):
            return text
            
        # Find all {{ variable }} patterns
        pattern = r'\{\{\s*([^}]+)\s*\}\}'
        
        def replace_var(match):
            var_name = match.group(1).strip()
            # Look for variable in variables dict or host facts
            if var_name in self.variables:
                return str(self.variables[var_name])
            elif var_name in self.host_facts:
                return str(self.host_facts[var_name])
            else:
                # Return original if variable not found
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
        
        # Simple condition evaluation
        # Replace variables in condition
        condition = self.substitute_variables(condition)
        
        # Handle common operators
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
        
        # If no operator found, treat as boolean
        return bool(condition)

def load_playbook(file_path):
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def run_task(task, host, play_vars=None):
    """Enhanced task runner with variable support"""
    
    # Initialize variable processor
    var_processor = VariableProcessor(play_vars or {})
    
    # Process task for variable substitution
    processed_task = var_processor.process_dict(task)
    
    # Check conditions
    when_condition = processed_task.get("when")
    if not var_processor.evaluate_condition(when_condition):
        return {
            "host": host["ip"], 
            "output": "", 
            "error": "", 
            "skipped": True,
            "msg": "Skipped due to when condition"
        }
    
    module_name = processed_task["module"]
    args = processed_task.get("args", {})
    become = processed_task.get("become", False)

    try:
        mod = importlib.import_module(f"modules.{module_name}")
    except ModuleNotFoundError:
        return {"host": host["ip"], "output": "", "error": f"Module '{module_name}' not found"}

    return mod.run(
        host["ip"],
        host["username"],
        host["password"],
        args,
        executor,
        become=become
    )

def run_on_all_hosts(hosts, task, play_vars=None):
    results = []
    with ThreadPoolExecutor() as pool:
        futures = [pool.submit(run_task, task, host, play_vars) for host in hosts]
        for future in futures:
            try:
                results.append(future.result())
            except Exception as e:
                results.append({"host": "unknown", "output": "", "error": str(e)})
    return results

def run_playbook(hosts, playbook):
    """Enhanced playbook runner with variable and conditional support"""
    
    for play in playbook:
        inventory_group = play.get("hosts", "all")
        play_vars = play.get("vars", {})  # Extract play variables

        if inventory_group == "all":
            available_hosts = []
            for group_hosts in hosts.values():
                available_hosts.extend(group_hosts)
        else:
            available_hosts = hosts.get(inventory_group, [])
            if not available_hosts:
                print(f"No hosts found for group '{inventory_group}'\nPlease make sure that you have group '{inventory_group}' in your inventory file")
                continue

        for task in play.get("tasks", []):
            print(f"\n--- [ {task['name']} ] ---")
            results = run_on_all_hosts(available_hosts, task, play_vars)

            for result in results:
                print(f"HOST: {result['host']}")
                
                if result.get("skipped"):
                    print(f"SKIPPED: {result.get('msg', 'Condition not met')}")
                else:
                    if result["output"]:
                        print(result["output"])
                    if result["error"]:
                        print("ERROR:", result["error"])

# Utility functions for module development
def parse_module_args(args_string):
    """Parse module arguments from string format"""
    if isinstance(args_string, dict):
        return args_string
    
    # Simple key=value parser
    result = {}
    if args_string:
        for pair in args_string.split():
            if '=' in pair:
                key, value = pair.split('=', 1)
                result[key] = value
    return result