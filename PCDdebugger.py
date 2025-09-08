#!/usr/bin/env python3

import argparse
import subprocess
import os
import json
import ast
from datetime import datetime
import shutil
import re
import gzip
import yaml

DEFAULT_OUTPUT_DIR = f"PCDdebugger-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
OUTPUT_DIR = DEFAULT_OUTPUT_DIR
USE_INSECURE = False # Will be set to True if the script is run with --insecure

def run_cmd(cmd, shell=False):
    """Runs a command, adding --insecure (if flagged) and --max-width to openstack commands, and returns output and the command string."""
    
    # Automatically add flags to openstack commands
    if isinstance(cmd, list) and cmd[0] == "openstack":
        # Add --insecure to bypass SSL verification if the script's --insecure flag is used
        if USE_INSECURE and "--insecure" not in cmd:
            cmd.insert(1, "--insecure")
        
        # Add --max-width to list/show commands for better formatting, unless a specific format is requested
        is_list_or_show = any(sub in ["list", "show"] for sub in cmd)
        is_formatted_output = any(flag in cmd for flag in ["-f", "--format"])
        if is_list_or_show and "--max-width" not in cmd and not is_formatted_output:
            cmd.extend(["--max-width", "170"])
            
    cmd_str = ' '.join(cmd) if isinstance(cmd, list) else cmd
    print(f"[RUNNING] {cmd_str}")
    
    try:
        result = subprocess.run(cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return result.stdout.strip(), cmd_str
    except subprocess.CalledProcessError as e:
        error_msg = f"ERROR: {e.stderr.strip()}"
        print(f"[ERROR] Command failed: {cmd_str}\n{e.stderr.strip()}")
        return error_msg, cmd_str

def save_text(text, path, command_str=None):
    """Saves text to a file, prepending the command that generated it."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        if command_str:
            header = f"# Command: {command_str}\n# {'-'*70}\n\n"
            f.write(header)
        f.write(text)

def save_binary(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)

def check_openstack_auth():
    print("[INFO] Checking OpenStack authentication...")
    required_envs = ["OS_AUTH_URL", "OS_USERNAME", "OS_PROJECT_NAME"]
    missing_vars = [var for var in required_envs if not os.environ.get(var)]
    if missing_vars:
        print(f"[ERROR] Missing environment variables: {', '.join(missing_vars)}")
        print("[HINT] Please source your OpenStack RC file (e.g., `source ~/admin-openrc.sh`)")
        exit(1)

    result, _ = run_cmd(["openstack", "token", "issue"])
    if "ERROR" in result or "Missing" in result or "Failed" in result:
        print("[ERROR] Unable to authenticate with OpenStack.")
        print("[HINT] Please ensure your RC file is sourced and credentials are correct.")
        exit(1)
    print("[OK] OpenStack authentication validated.")

def collect_health_checks():
    os.makedirs(f"{OUTPUT_DIR}/health", exist_ok=True)
    cmds = {
        "compute_services": ["openstack", "compute", "service", "list", "--long", "--timing"],
        "resource_providers": ["openstack", "resource", "provider", "list"],
        "network_agents": ["openstack", "network", "agent", "list", "--long"],
        "hypervisors": ["openstack", "hypervisor", "list", "--long"],
        "hypervisor_stats": ["openstack", "hypervisor", "stats", "show"],
        "volume_services": ["openstack", "volume", "service", "list", "--long"],
        "cinder_pools": ["openstack", "volume", "backend", "pool", "list", "--long"],
    }
    for name, cmd in cmds.items():
        output, cmd_str = run_cmd(cmd)
        save_text(output, f"{OUTPUT_DIR}/health/{name}.txt", command_str=cmd_str)

def collect_nova_info(vm_id):
    os.makedirs(f"{OUTPUT_DIR}/nova", exist_ok=True)
    info_text, cmd_str = run_cmd(["openstack", "server", "show", vm_id])
    save_text(info_text, f"{OUTPUT_DIR}/nova/server_show.txt", command_str=cmd_str)
    
    # Collect hypervisor info
    hypervisor_hostname = None
    for line in info_text.splitlines():
        if "OS-EXT-SRV-ATTR:hypervisor_hostname" in line:
            parts = line.split('|')
            if len(parts) > 2:
                hypervisor_hostname = parts[2].strip()
                break
    
    if hypervisor_hostname:
        print(f"[INFO] Collecting details for hypervisor: {hypervisor_hostname}")
        hypervisor_info, cmd_str_hv = run_cmd(["openstack", "hypervisor", "show", hypervisor_hostname])
        save_text(hypervisor_info, f"{OUTPUT_DIR}/nova/hypervisor_{hypervisor_hostname}_show.txt", command_str=cmd_str_hv)
    else:
        print(f"[WARN] Could not find hypervisor hostname for VM {vm_id}.")

    events, cmd_str = run_cmd(["openstack", "server", "event", "list", vm_id])
    save_text(events, f"{OUTPUT_DIR}/nova/server_events.txt", command_str=cmd_str)
    migrations, cmd_str = run_cmd(["openstack", "server", "migration", "list", "--server", vm_id])
    save_text(migrations, f"{OUTPUT_DIR}/nova/migrations.txt", command_str=cmd_str)

def collect_ports_for_vm(vm_id):
    os.makedirs(f"{OUTPUT_DIR}/neutron", exist_ok=True)
    ports_raw, cmd_str = run_cmd(["openstack", "port", "list", "--device-id", vm_id])
    save_text(ports_raw, f"{OUTPUT_DIR}/neutron/vm_ports_list.txt", command_str=cmd_str)
    
    port_ids_str, _ = run_cmd(["openstack", "port", "list", "--device-id", vm_id, "-c", "ID", "-f", "value"])
    if "ERROR" in port_ids_str: return
    
    for port_id in port_ids_str.splitlines():
        collect_port_info(port_id, is_dependency=True)
        network_id, _ = run_cmd(["openstack", "port", "show", port_id, "-c", "network_id", "-f", "value"])
        if network_id and "ERROR" not in network_id:
            collect_network_info(network_id)

def collect_volumes_for_vm(vm_id):
    os.makedirs(f"{OUTPUT_DIR}/cinder", exist_ok=True)
    try:
        volumes_str, cmd_str = run_cmd(["openstack", "server", "show", vm_id, "-c", "volumes_attached", "-f", "value"])
        if "ERROR" in volumes_str or not volumes_str.strip():
            print(f"[INFO] No volumes attached to VM {vm_id}.")
            return
        
        attached_vols = ast.literal_eval(volumes_str)
        save_text(json.dumps(attached_vols, indent=2), f"{OUTPUT_DIR}/cinder/attached_volumes_list.txt", command_str=cmd_str)
        
        for vol in attached_vols:
            vol_id = vol.get("id")
            if vol_id:
                collect_volume_details(vol_id, is_dependency=True)
    except Exception as e:
        print(f"[WARN] Failed to collect or parse volumes for VM {vm_id}: {e}")

def collect_network_info(network_id):
    print(f"[INFO] Collecting details for network: {network_id}")
    os.makedirs(f"{OUTPUT_DIR}/neutron", exist_ok=True)
    net_text, cmd_str = run_cmd(["openstack", "network", "show", network_id])
    save_text(net_text, f"{OUTPUT_DIR}/neutron/network_{network_id}.txt", command_str=cmd_str)
    
    subnet_ids_str, _ = run_cmd(["openstack", "subnet", "list", "--network", network_id, "-c", "ID", "-f", "value"])
    if "ERROR" in subnet_ids_str: return
    
    print(f"[INFO] Found {len(subnet_ids_str.splitlines())} subnets for network {network_id}")
    for subnet_id in subnet_ids_str.splitlines():
        subnet_detail, cmd_str_subnet = run_cmd(["openstack", "subnet", "show", subnet_id])
        save_text(subnet_detail, f"{OUTPUT_DIR}/neutron/subnet_{subnet_id}.txt", command_str=cmd_str_subnet)

def collect_port_info(port_id, is_dependency=False):
    prefix = "vm_port" if is_dependency else "port"
    print(f"[INFO] Collecting details for port: {port_id}")
    os.makedirs(f"{OUTPUT_DIR}/neutron", exist_ok=True)
    port_text, cmd_str = run_cmd(["openstack", "port", "show", port_id])
    save_text(port_text, f"{OUTPUT_DIR}/neutron/{prefix}_{port_id}.txt", command_str=cmd_str)
    try:
        sg_ids_str, _ = run_cmd(["openstack", "port", "show", port_id, "-c", "security_group_ids", "-f", "value"])
        if "ERROR" in sg_ids_str: return
        
        sg_ids = ast.literal_eval(sg_ids_str)
        print(f"[INFO] Found {len(sg_ids)} security groups for port {port_id}")
        for sg_id in sg_ids:
            sg_detail, cmd_str_sg = run_cmd(["openstack", "security", "group", "show", sg_id])
            save_text(sg_detail, f"{OUTPUT_DIR}/neutron/security_group_{sg_id}.txt", command_str=cmd_str_sg)
            sg_rules, cmd_str_rules = run_cmd(["openstack", "security", "group", "rule", "list", sg_id])
            save_text(sg_rules, f"{OUTPUT_DIR}/neutron/security_group_{sg_id}_rules.txt", command_str=cmd_str_rules)
    except Exception as e:
        print(f"[WARN] Could not collect security groups for port {port_id}: {e}")

def collect_volume_details(volume_id, is_dependency=False):
    prefix = "attached_volume" if is_dependency else "volume"
    print(f"[INFO] Collecting details for volume: {volume_id}")
    os.makedirs(f"{OUTPUT_DIR}/cinder", exist_ok=True)
    
    # Save the human-readable table output
    vol_detail_table, cmd_str_table = run_cmd(["openstack", "volume", "show", volume_id])
    save_text(vol_detail_table, f"{OUTPUT_DIR}/cinder/{prefix}_{volume_id}.txt", command_str=cmd_str_table)

    # Get attachments reliably using JSON format to avoid parsing truncated table output
    attachments_json_str, _ = run_cmd(["openstack", "volume", "show", volume_id, "-c", "attachments", "-f", "json"])
    
    if attachments_json_str and "ERROR" not in attachments_json_str:
        try:
            data = json.loads(attachments_json_str)
            attachments = data.get("attachments", [])
            
            if isinstance(attachments, list):
                for attachment in attachments:
                    attachment_id = attachment.get("attachment_id")
                    server_id = attachment.get("server_id")
                    if attachment_id:
                        print(f"[INFO] Collecting details for volume attachment: {attachment_id} (VM: {server_id})")
                        # CORRECTED COMMAND: Removed the invalid "--volume" argument
                        attachment_detail, cmd_str_attach = run_cmd(["openstack", "volume", "attachment", "show", attachment_id])
                        save_text(attachment_detail, f"{OUTPUT_DIR}/cinder/volume_{volume_id}_attachment_{attachment_id}.txt", command_str=cmd_str_attach)
                    
                    # If called via --volume, also grab details for the attached VM
                    if server_id and not is_dependency:
                        print(f"[INFO] Volume {volume_id} is attached to VM {server_id}. Collecting related VM info...")
                        collect_nova_info(server_id)
                        collect_ports_for_vm(server_id)

        except json.JSONDecodeError as e:
            print(f"[WARN] Could not parse JSON attachments for volume {volume_id}: {e}")
    else:
        print(f"[INFO] No attachment information found for volume {volume_id}.")


def collect_stack_info(stack_id):
    os.makedirs(f"{OUTPUT_DIR}/heat", exist_ok=True)
    stack_show, cmd_str = run_cmd(["openstack", "stack", "show", stack_id])
    save_text(stack_show, f"{OUTPUT_DIR}/heat/stack_show.txt", command_str=cmd_str)
    
    resource_list_raw, cmd_str = run_cmd(["openstack", "stack", "resource", "list", stack_id])
    save_text(resource_list_raw, f"{OUTPUT_DIR}/heat/stack_resources.txt", command_str=cmd_str)
    
    resource_names_str, _ = run_cmd(["openstack", "stack", "resource", "list", stack_id, "-c", "resource_name", "-f", "value"])
    if "ERROR" in resource_names_str: return
    
    for res_name in resource_names_str.splitlines():
        res_show, cmd_str_res = run_cmd(["openstack", "stack", "resource", "show", stack_id, res_name])
        save_text(res_show, f"{OUTPUT_DIR}/heat/resource_{res_name}.txt", command_str=cmd_str_res)

def collect_image_details(image_id, is_dependency=False, vm_id=None):
    """Collects details for a specific Glance image."""
    prefix = f"image_of_vm_{vm_id}" if is_dependency and vm_id else f"image_{image_id}"
    print(f"[INFO] Collecting details for image: {image_id}")
    os.makedirs(f"{OUTPUT_DIR}/glance", exist_ok=True)
    
    image_details, cmd_str = run_cmd(["openstack", "image", "show", image_id])
    save_text(image_details, f"{OUTPUT_DIR}/glance/{prefix}.txt", command_str=cmd_str)

def collect_image_and_flavor(vm_id):
    os.makedirs(f"{OUTPUT_DIR}/nova", exist_ok=True)
    
    image_id_str, _ = run_cmd(["openstack", "server", "show", vm_id, "-c", "image", "-f", "value"])
    image_match = re.search(r'\(([^)]+)\)', image_id_str)
    image_id = image_match.group(1) if image_match else None
        
    print("[INFO] Attempting to determine flavor ID...")
    flavor_id = None
    flavor_id_str, _ = run_cmd(["openstack", "server", "show", vm_id, "-c", "flavor", "-f", "value"])

    flavor_match = re.search(r'\(([^)]+)\)', flavor_id_str)
    if flavor_match:
        flavor_id = flavor_match.group(1)
        print(f"[INFO] Found flavor ID '{flavor_id}' using regex match.")
    elif flavor_id_str.strip().startswith('{'):
        try:
            flavor_dict = ast.literal_eval(flavor_id_str)
            if isinstance(flavor_dict, dict) and 'id' in flavor_dict:
                flavor_id = flavor_dict['id']
                print(f"[INFO] Found flavor ID '{flavor_id}' by parsing dictionary output.")
        except (ValueError, SyntaxError) as e:
            print(f"[WARN] Could not parse flavor output as a dictionary: {e}")

    if image_id and "ERROR" not in image_id:
        collect_image_details(image_id, is_dependency=True, vm_id=vm_id)
    else:
        print("[INFO] No image ID found for this VM. Skipping image details.")
        
    if flavor_id and "ERROR" not in flavor_id:
        print(f"[INFO] Collecting details for flavor: {flavor_id}")
        flavor, cmd_str = run_cmd(["openstack", "flavor", "show", flavor_id])
        save_text(flavor, f"{OUTPUT_DIR}/nova/flavor_show.txt", command_str=cmd_str)
    else:
        print("[WARN] Could not determine a valid flavor ID. Skipping flavor details.")

def collect_keystone_user_info(user_id_or_name):
    os.makedirs(f"{OUTPUT_DIR}/keystone", exist_ok=True)
    user_info, cmd_str = run_cmd(["openstack", "user", "show", user_id_or_name])
    save_text(user_info, f"{OUTPUT_DIR}/keystone/user_show.txt", command_str=cmd_str)
    role_assignments, cmd_str_roles = run_cmd(["openstack", "role", "assignment", "list", "--user", user_id_or_name, "--names"])
    save_text(role_assignments, f"{OUTPUT_DIR}/keystone/user_role_assignments.txt", command_str=cmd_str_roles)

def collect_quota_info(project_id):
    if not project_id:
        print("[WARN] No project ID provided for quota collection.")
        return
    print(f"[INFO] Collecting quotas for project: {project_id}")
    os.makedirs(f"{OUTPUT_DIR}/quota", exist_ok=True)
    quota_details, cmd_str = run_cmd(["openstack", "quota", "show", project_id])
    save_text(quota_details, f"{OUTPUT_DIR}/quota/project_{project_id}_quota.txt", command_str=cmd_str)

def archive_output():
    zip_path = shutil.make_archive(OUTPUT_DIR, 'zip', OUTPUT_DIR)
    print(f"[DONE] Output archived at: {zip_path}")

def collect_mysql_dump(namespace, db_pod_label, db_service_name):
    """Connects to a Percona HAProxy pod to perform a MySQL dump, parsing Consul data with PyYAML."""
    print(f"[INFO] Starting MySQL dump for namespace: {namespace}")
    os.makedirs(f"{OUTPUT_DIR}/database", exist_ok=True)

    try:
        print("[INFO] Fetching DB configuration from consul...")
        cmd_get_db_config = f'kubectl exec deploy/resmgr -c resmgr -n {namespace} -- bash -l -c "consul-dump-yaml --start-key customers/\\$CUSTOMER_ID/regions/\\$REGION_ID/db"'
        db_config_yaml, _ = run_cmd(cmd_get_db_config, shell=True)
        if "ERROR" in db_config_yaml:
            print("[ERROR] Could not fetch DB config from resmgr/consul. Aborting.")
            return

        data = yaml.safe_load(db_config_yaml)
        
        customer_id = list(data['customers'].keys())[0]
        region_id = list(data['customers'][customer_id]['regions'].keys())[0]
        db_server = data['customers'][customer_id]['regions'][region_id]['dbserver']
        
        if not db_server:
            print("[ERROR] Could not parse DB server name from Consul YAML. Aborting.")
            return

        print(f"[INFO] Found DB server: {db_server}. Fetching password...")
        cmd_get_pass_config = f'kubectl exec deploy/resmgr -c resmgr -n {namespace} -- bash -l -c "consul-dump-yaml --start-key customers/\\$CUSTOMER_ID/dbservers/{db_server}"'
        pass_config_yaml, _ = run_cmd(cmd_get_pass_config, shell=True)
        if "ERROR" in pass_config_yaml:
            print("[ERROR] Could not fetch DB password config from resmgr/consul. Aborting.")
            return
        
        pass_data = yaml.safe_load(pass_config_yaml)
        db_admin_pass = pass_data['customers'][customer_id]['dbservers'][db_server]['admin_pass']

        if not db_admin_pass:
            print("[ERROR] Could not parse DB admin password from Consul YAML. Aborting.")
            return

        print(f"[INFO] Finding a database pod using label: '{db_pod_label}'...")
        cmd_get_pod = f"kubectl get pods -n {namespace} -l {db_pod_label} -o jsonpath='{{.items[0].metadata.name}}'"
        db_pod_name, _ = run_cmd(cmd_get_pod, shell=True)
        
        if "ERROR" in db_pod_name or not db_pod_name:
            print(f"[ERROR] Could not find a pod with label '{db_pod_label}' in namespace '{namespace}'. Aborting.")
            return
        print(f"[INFO] Found pod to connect to: {db_pod_name}")

        print("[INFO] Performing mysqldump...")
        cmd_dump_str = f"kubectl exec -i {db_pod_name} -c haproxy -n {namespace} -- bash -l -c \"MYSQL_PWD='{db_admin_pass}' mysqldump -h {db_service_name} --single-transaction --all-databases -u root\""
        
        print(f"[RUNNING] {cmd_dump_str}")
        result = subprocess.run(cmd_dump_str, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1800)

        if result.returncode != 0:
            print(f"[ERROR] mysqldump command failed:\n{result.stderr.decode('utf-8', 'ignore').strip()}")
            return

        if not result.stdout:
            print("[WARN] mysqldump produced no output.")
            return
        
        print("[INFO] Compressing dump file...")
        dump_filename = f"{OUTPUT_DIR}/database/mysql_dump_all_databases.sql.gz"
        compressed_data = gzip.compress(result.stdout)
        
        save_binary(compressed_data, dump_filename)
        print(f"[OK] MySQL dump saved to {dump_filename}")

    except (subprocess.TimeoutExpired, yaml.YAMLError, KeyError, IndexError) as e:
        print(f"[ERROR] An error occurred during the MySQL dump process: {e}")
        print("[HINT] This could be due to a timeout, invalid YAML from Consul, or an unexpected data structure.")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")

def main():
    global OUTPUT_DIR, USE_INSECURE
    parser = argparse.ArgumentParser(description="Cloud Debug Collector")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--zip", action="store_true", help="Zip output")
    parser.add_argument("--insecure", action="store_true", help="Bypass SSL verification for OpenStack commands.")

    # OpenStack flags
    parser.add_argument("--vm", help="VM ID or Name")
    parser.add_argument("--image", help="Image ID or Name")
    parser.add_argument("--network", help="Network ID")
    parser.add_argument("--port", help="Port ID")
    parser.add_argument("--volume", help="Volume ID")
    parser.add_argument("--stack", help="Heat Stack ID or Name")
    parser.add_argument("--user", help="Keystone User ID or Name")
    
    # MySQL/Kubernetes flags
    parser.add_argument("--mysql-dump", action="store_true", help="Perform a MySQL dump from the k8s cluster.")
    parser.add_argument("--namespace", help="Kubernetes namespace for resmgr and database.")
    parser.add_argument("--db-pod-label", default="app.kubernetes.io/component=haproxy", help="The label to select the database proxy pod.")
    parser.add_argument("--db-service-name", default="percona-db-pxc-db-haproxy", help="The Kubernetes service name of the database.")

    args = parser.parse_args()
    OUTPUT_DIR = args.output
    USE_INSECURE = args.insecure
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    is_openstack_command = any([args.vm, args.image, args.network, args.port, args.volume, args.stack, args.user])

    if is_openstack_command:
        check_openstack_auth()
        collect_health_checks()
        collected_project_ids = set()

        if args.vm:
            collect_nova_info(args.vm)
            collect_image_and_flavor(args.vm)
            collect_ports_for_vm(args.vm)
            collect_volumes_for_vm(args.vm)
            project_id, _ = run_cmd(["openstack", "server", "show", args.vm, "-c", "project_id", "-f", "value"])
            if project_id and "ERROR" not in project_id and project_id not in collected_project_ids:
                collect_quota_info(project_id)
                collected_project_ids.add(project_id)

        if args.image:
            collect_image_details(args.image)
        
        if args.network:
            collect_network_info(args.network)

        if args.port:
            collect_port_info(args.port)

        if args.volume:
            collect_volume_details(args.volume)

        if args.stack:
            collect_stack_info(args.stack)
            project_id, _ = run_cmd(["openstack", "stack", "show", args.stack, "-c", "project", "-f", "value"])
            if project_id and "ERROR" not in project_id and project_id not in collected_project_ids:
                collect_quota_info(project_id)
                collected_project_ids.add(project_id)

        if args.user:
            collect_keystone_user_info(args.user)
            project_id, _ = run_cmd(["openstack", "user", "show", args.user, "-c", "default_project_id", "-f", "value"])
            if project_id and "ERROR" not in project_id and project_id not in collected_project_ids:
                collect_quota_info(project_id)
                collected_project_ids.add(project_id)

    if args.mysql_dump:
        if not args.namespace:
            print("[ERROR] The '--namespace' argument is required when using '--mysql-dump'.")
            exit(1)
        collect_mysql_dump(args.namespace, args.db_pod_label, args.db_service_name)

    if args.zip:
        archive_output()

    print(f"[DONE] All debug information saved to: {os.path.abspath(OUTPUT_DIR)}")

if __name__ == "__main__":
    main()