import os
import sys
import subprocess
import yaml
import xml.etree.ElementTree as ET
import re
from collections import defaultdict
import networkx as nx
import requests
import glob
from pyvis.network import Network
from flask import Flask, render_template_string, send_from_directory
import json

# Version: 1.0
# Usage Example: python aa_pro_max.py ./main-api.tar ./cfr-0.152.jar output

# Create graph objects
graph = nx.DiGraph()
service_discovery = "containerized-discovery"
# Dictory to store the service name as key and corresponding app label name
service_to_app_label_dict = {}
# Dictory to store the app label as key and corresponding application name
app_label_to_service_dict = {}

# Parse command line arguments
if len(sys.argv) < 5:
    print('Usage: python aa_pro_max.py <docker_image_tar_folder> <cfr_tool_path> <output_directory> <namespace> <root_dir>')
    sys.exit(1)
DOCKER_IMAGE_TAR_FOLDER = sys.argv[1]
CFR_TOOL_PATH = sys.argv[2]
OUTPUT_DIRECTORY = sys.argv[3]
NAMESPACE = sys.argv[4]
ROOT_DIR = sys.argv[5]


def init():
    # Loop through the root directory to find the application.yml and deployment.yml files
    # We can get the service name from the application.yml file and the app label name from the deployment.yml file
    for foldername, subfolders, filenames in os.walk(ROOT_DIR):
        application_file = None
        deployment_file = None
        # Check if the application.yml and deployment.yml files exist
        if 'k8s' in subfolders and 'deployment.yml' in os.listdir(os.path.join(foldername, 'k8s')):
            deployment_file = os.path.join(foldername, 'k8s', 'deployment.yml')
            with open(deployment_file, 'r') as f:
                deployment_yaml = yaml.safe_load(f)
        if 'src' in subfolders and 'main' in os.listdir(os.path.join(foldername, 'src')):
            for subfoldername, _, subfilenames in os.walk(os.path.join(foldername, 'src', 'main')):
                if 'resources' in subfoldername and 'application.yml' in subfilenames:
                    application_file = os.path.join(subfoldername, 'application.yml')
                    with open(application_file, 'r') as f:
                        application_yaml = yaml.safe_load(f)
        # If both files exist, add the application name and service name to the dictionary
        if application_file is not None and deployment_file is not None:
            service_to_app_label_dict[application_yaml.get('spring', {}).get('application', {}).get(
                'name')] = deployment_yaml.get('metadata', {}).get('labels', {}).get('app')
            app_label_to_service_dict[deployment_yaml.get('metadata', {}).get('labels', {}).get(
                'app')] = application_yaml.get('spring', {}).get('application', {}).get('name')        
            
    # Create a list to store the service names
    services = []
    # Create a dictionary to store the service names and corresponding calls
    names_calls = defaultdict(list)

    for index, filename in enumerate(os.listdir(DOCKER_IMAGE_TAR_FOLDER)):
        file_path = os.path.join(DOCKER_IMAGE_TAR_FOLDER, filename)
        name = '/' + filename.split(".")[0]
        # Check if the Docker image .tar file exists
        if not os.path.exists(file_path):
            print(
                f'[!] The Docker image .tar file does not exist: {file_path}')
            sys.exit(1)
        # Check if the CFR tool exists
        if not os.path.exists(CFR_TOOL_PATH):
            print(f'[!] The CFR tool does not exist: {CFR_TOOL_PATH}')
            sys.exit(1)

        # Create the output directory
        os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

        # Check if the Docker image has already been extracted
        if os.path.exists(OUTPUT_DIRECTORY + name + '/docker_image'):
            print(f"[!] The Docker image has already been extracted: {name}")
        else:
            # Create the output directory
            os.makedirs(OUTPUT_DIRECTORY + name + '/docker_image', exist_ok=True)
            # Extract the Docker image .tar file
            subprocess.run(['tar', '-xf', file_path, '-C',
                        OUTPUT_DIRECTORY + name + '/docker_image'])

        # # Find all the .tar files for each layer
        layer_tar_files = []
        for root, dirs, files in os.walk(OUTPUT_DIRECTORY + name + '/docker_image'):
            for file in files:
                if file.endswith('.tar'):
                    layer_tar_files.append(os.path.join(root, file))

        # Extract each layer
        if len(layer_tar_files) > 0:
            print(
                f"[*] {len(layer_tar_files)} layers found in the Docker image.")
            print("[+] Extracting layers...")
            # Check if the extracted layers directory exists
            if os.path.exists(OUTPUT_DIRECTORY + name + '/extracted_layers'):
                print(
                    f"[!] The extracted layers directory already exists: {name}")
            else:
                # Create the output directory
                os.makedirs(OUTPUT_DIRECTORY + name +
                            '/extracted_layers', exist_ok=True)
                for layer_tar_file in layer_tar_files:
                    subprocess.run(['tar', '-xf', layer_tar_file, '-C',
                                OUTPUT_DIRECTORY + name + '/extracted_layers'])
        else:
            print('[!] No layers found in the Docker image.')

        # Find JAR files in the extracted layers
        jar_files = []
        for root, dirs, files in os.walk(OUTPUT_DIRECTORY + name + '/extracted_layers'):
            for file in files:
                if file.endswith('.jar'):
                    jar_files.append(os.path.join(root, file))

        # # If JAR files were found, decompile them using CFR
        if len(jar_files) > 0:
            print(
                f"[*] {len(jar_files)} JAR files found in the extracted layers.")
            print("[+] Decompiling JAR files...\n")

            # Check if the output directory exists
            if not os.path.exists(OUTPUT_DIRECTORY + name + '/jars_decompiled'):           
                # Create the output directory
                os.makedirs(OUTPUT_DIRECTORY + name +
                            '/jars_decompiled', exist_ok=True)

            # Extract the JAR files and use CFR to decompile the JAR files
            for jar_file in jar_files:
                print(f'\n[+] Checking JAR file: {jar_file}')

                os.makedirs(OUTPUT_DIRECTORY + name + '/jars_decompiled/' +
                            jar_file.split('/')[-1], exist_ok=True)

                # Check if the JAR file was already unpacked
                if os.path.exists(OUTPUT_DIRECTORY + name + '/jars_decompiled/' + jar_file.split('/')[-1] + '/unpacked'):
                    print('   [+] JAR file was already unpacked.')
                else:
                    os.makedirs(OUTPUT_DIRECTORY + name + '/jars_decompiled/' +
                            jar_file.split('/')[-1] + '/unpacked', exist_ok=True)
                    # Extract the JAR file
                    subprocess.run(['unzip', jar_file, '-d', OUTPUT_DIRECTORY + name +
                                '/jars_decompiled/' + jar_file.split('/')[-1] + '/unpacked'])

                # Check if the directory contains an application.yml file
                yml_file = None
                for root, dirs, files in os.walk(OUTPUT_DIRECTORY + name + '/jars_decompiled/' + jar_file.split('/')[-1] + '/unpacked'):
                    if 'application.yml' in files:
                        print(
                            f'   [+] Found application.yml file: {os.path.join(root, "application.yml")}')
                        yml_file = os.path.join(root, 'application.yml')
                        break

                # If a yml file was found, parse it and extract the name
                if yml_file is not None:
                    # Check if the JAR file was already decompiled
                    if os.path.exists(OUTPUT_DIRECTORY + name + '/jars_decompiled/' + jar_file.split('/')[-1] + '/decompiled'):
                        print('   [+] JAR file was already decompiled.')
                    else:
                        # Use CFR to decompile the JAR file
                        print(f'[+] Decompiling JAR file: {jar_file}')
                        subprocess.run(['java', '-jar', CFR_TOOL_PATH, jar_file, '--outputdir', OUTPUT_DIRECTORY +
                                    name + '/jars_decompiled/' + jar_file.split('/')[-1] + '/decompiled'])

                    print(f'[+] Parsing application.yml file: {yml_file}')
                    with open(yml_file, 'r') as f:
                        data = yaml.safe_load(f)
                        app_name = data.get('spring', {}).get(
                            'application', {}).get('name')
                        if app_name is not None:
                            print(f'   [+] Found service name: {app_name}')
                            # Store the folder path and corresponding name
                            services.append(
                                [app_name, jar_file.split('/')[-1]])
                        if 'spring' in data and 'cloud' in data['spring'] and 'gateway' in data['spring']['cloud'] and 'routes' in data['spring']['cloud']['gateway']:
                            routes = data['spring']['cloud']['gateway']['routes']
                            route_ids = [route['id'].lower()
                                         for route in routes]
                            names_calls[app_name].extend(route_ids)
                            for id in route_ids:
                                graph.add_edge(service_to_app_label_dict[app_name], service_to_app_label_dict[id])

                    # Check decompiled source code for @FeignClient annotation
                    for root, dirs, files in os.walk(OUTPUT_DIRECTORY + name + '/jars_decompiled/' + jar_file.split('/')[-1] + '/decompiled'):
                        for file_name in files:
                            if file_name.endswith('.java'):
                                print(
                                    f'      [+] Searching for @FeignClient annotation in: {os.path.join(root, file_name)}')
                                # Open the .java file and search for @FeignClient annotation
                                with open(os.path.join(root, file_name), 'r') as f:
                                    for line in f:
                                        matched = re.search(
                                            r'@FeignClient\(value="([^"]+)"\)', line)
                                        if matched:
                                            print(
                                                f'         [+] Found @FeignClient annotation: {matched.group(1)}\n')
                                            # Store the folder path and corresponding name
                                            callto_name = matched.group(1)
                                            names_calls[app_name].append(
                                                callto_name)
                                            graph.add_edge(
                                                service_to_app_label_dict[app_name], service_to_app_label_dict[callto_name])
                                            break
                                        matched2 = re.search(
                                            r'@EnableEurekaServer', line)
                                        if matched2:
                                            print(
                                                f'         [+] Found @EnableEurekaServer annotation\n')
                                            # Store the folder path and corresponding name
                                            service_discovery = app_name
                                            break
                else:
                    print(
                        '   [!] No application.yml file found in the JAR file...Skipping.')
        else:
            print('[!] No JAR files found in the extracted layers.')

    print(service_discovery)
    all_svcs = []
    for node in graph.nodes():
        all_svcs.append(node)

    for node in all_svcs:
        # Associate the @FeignClient line with the folder it is in
        graph.add_edge(node, "k8n-service-discovery")
    
    app_label_to_service_dict["k8n-service-discovery"] = "containerized-discovery"
    print(f"[*] Init Complete! Successfully parsed {len(app_label_to_service_dict)} services.")


def generate_and_apply_network_policies():
    # Create the network policy folder if it does not exist
    if not os.path.exists(OUTPUT_DIRECTORY + "/network_policies"):
        os.makedirs(OUTPUT_DIRECTORY + "/network_policies")
    else:
        # Remove all files in the network policy folder
        for filename in os.listdir(OUTPUT_DIRECTORY + "/network_policies"):
            os.remove(OUTPUT_DIRECTORY + "/network_policies/" + filename)
    eureka_graph = get_app_instances()
    for node in eureka_graph.nodes():
        ips_to_the_node = []
        ips_from_the_node = []
        # Get nodes that are pointed to the current node
        for node_from in eureka_graph.predecessors(node):
            ips_to_the_node.append(node_from.split(" ")[0])
        # Get nodes that point from the current node
        for node_to in eureka_graph.successors(node):
            ips_from_the_node.append(node_to.split(" ")[0])
        # Generate a network policy for the current node
        generate_network_policy(node, ips_from_the_node, ips_to_the_node)
    # Apply the network policies to the cluster
    # using kubectl apply -f <file>
    for filename in os.listdir(OUTPUT_DIRECTORY + "/network_policies/"):
        if filename.endswith(".yaml"):
            # check if the policy is for containerized-discovery, ignore if it is
            # file names are in the format <ip>-<port>-containerized-xxxx-network_policy.yaml
            if filename.split("-")[3] == "discovery":
                continue
            filepath = os.path.join(OUTPUT_DIRECTORY + "/network_policies/", filename)
            os.system(f"kubectl apply -f {filepath}")



def generate_network_policy(pod, ips_from_the_pod, ips_to_the_pod):
    modified_string = pod.replace(" ", "").replace(":", "-")
    policy = {}
    policy['apiVersion'] = 'networking.k8s.io/v1'
    policy['kind'] = 'NetworkPolicy'

    metadata = {}
    metadata['name'] = modified_string + '-policy'
    metadata['namespace'] = NAMESPACE
    policy['metadata'] = metadata

    spec = {}
    spec['podSelector'] = {'matchLabels': {'ip': pod.split(":")[0]}}
    spec['policyTypes'] = ['Ingress', 'Egress']

    egress_rules = []
    ingress_rules = []

    for allowed_ip in ips_to_the_pod:
        ingress_selector = {'matchLabels': {'ip': allowed_ip.split(":")[0]}}
        ingress_rule = {'from': [{'podSelector': ingress_selector}]}
        ingress_rules.append(ingress_rule)
    
    for allowed_ip in ips_from_the_pod:
        egress_selector = {'matchLabels': {'ip': allowed_ip.split(":")[0]}}
        egress_rule = {'to': [{'podSelector': egress_selector}], 'ports': [{'port': int(allowed_ip.split(":")[1])}]}
        egress_rules.append(egress_rule)

    kube_dns_rule = {'to': [{'namespaceSelector': {'matchLabels': {'name': 'kube-system'}}, 'podSelector': {'matchLabels':{"k8s-app": 'kube-dns'}}}], 'ports': [{'port': 53, 'protocol': 'UDP'}]}
    to_services = {'to': [{'ipBlock': {'cidr': '10.152.183.0/24'}}]}
    egress_rules.append(kube_dns_rule)
    egress_rules.append(to_services)
    spec['egress'] = egress_rules
    spec['ingress'] = ingress_rules

    policy['spec'] = spec

    # Check if the network policy already exists
    if os.path.exists(OUTPUT_DIRECTORY + "/network_policies/" + modified_string + "-network_policy.yaml"):
        # Delete the file
        os.remove(OUTPUT_DIRECTORY + "/network_policies/" + modified_string + "-network_policy.yaml")
    with open(os.path.join(OUTPUT_DIRECTORY + "/network_policies", modified_string+'-network_policy.yaml'), 'w') as f:
        yaml.safe_dump(policy, f)

def get_app_instances():
    ip_graph = nx.DiGraph()
    """Get the app instances from Eureka server and print out the instance IDs, IP addresses, and ports."""
    # Dictionary to store the app name and list of IP addresses
    app_to_ips = {}
    ips_to_app = {}
    ips_to_port = {}
    
    # Send GET request to Eureka server to get the app instances data in XML format
    resp = requests.get('http://localhost:8761/eureka/apps')
    if resp.status_code == 200:
        # Parse the XML response
        root = ET.fromstring(resp.content)

        # Print out the instance IDs, IP addresses, and ports
        print('Instance ID\t\tIP Address\tPort')
        for app in root.findall('.//application'):
            for instance in app.findall('instance'):
                name = instance.find('app').text.strip().lower()
                instance_id = instance.find('instanceId').text.strip()
                ip_addr = instance.find('ipAddr').text.strip()
                port_element = instance.find('port')
                if port_element is None:
                    print(
                        f'[?] Warning: No port element found for instance {instance_id}')
                else:
                    port_enabled = port_element.attrib.get(
                        'enabled', 'true') == 'true'
                    port = port_element.text.strip() if port_enabled else 'N/A'
                    print("for app "+name)
                    print(f'{instance_id}\t{ip_addr}\t\t{port}')
                    if name not in app_to_ips:
                        app_to_ips[name] = [[ip_addr, port]]
                    else:
                        app_to_ips[name].append([ip_addr, port])
                    ips_to_app[ip_addr] = name
                    ips_to_port[ip_addr] = port
    else:
        print('[!] Failed to get Eureka data')

    def get_pod_ips_and_ports(deployment_name):
        cmd = f'kubectl get pods -l app={deployment_name} -o json'
        result = subprocess.check_output(cmd, shell=True).decode('utf-8')
        pods = json.loads(result)['items']
        ips_and_ports = []
        for pod in pods:
            pod_ip = pod['status']['podIP']
            container_port = pod['spec']['containers'][0]['ports'][0]['containerPort']
            ips_and_ports.append((pod_ip, container_port))
        return ips_and_ports
    
    # Get the Eureka server's own IP address and port
    pod_ips_and_ports = get_pod_ips_and_ports('k8n-service-discovery')
    for pod_ip, port in pod_ips_and_ports:
        if service_discovery not in app_to_ips:
            app_to_ips[service_discovery] = [[pod_ip, port]]
        else:
            app_to_ips[service_discovery].append([pod_ip, port])
        ips_to_app[pod_ip] = service_discovery
        ips_to_port[pod_ip] = port

    # Compelete the IP graph
    for edge in graph.out_edges:
        s1, s2 = edge
        if app_label_to_service_dict[s1] in app_to_ips and app_label_to_service_dict[s2] in app_to_ips:
            ips1 = app_to_ips[app_label_to_service_dict[s1]]
            ips2 = app_to_ips[app_label_to_service_dict[s2]]
            for ip1 in ips1:
                for ip2 in ips2:
                    ip_graph.add_node(f"{ip1[0]}:{ips_to_port[ip1[0]]} - {ips_to_app[ip1[0]]}", group=ips_to_app[ip1[0]], size=20, ip=ip1[0], port=ips_to_port[ip1[0]])
                    ip_graph.add_edge(f"{ip1[0]}:{ips_to_port[ip1[0]]} - {ips_to_app[ip1[0]]}", f"{ip2[0]}:{ips_to_port[ip2[0]]} - {ips_to_app[ip2[0]]}")
    return ip_graph


def get_app_instances_k8s():
    ip_graph = nx.DiGraph()
    """Get the app instances from k8s using kubectl and print out the instance IDs, IP addresses, and ports."""
    # Dictionary to store the app name and list of IP addresses
    app_to_ips = {}
    ips_to_app = {}
    ips_to_port = {}
    app_to_number_of_instances = {}

    def get_pod_ips_and_ports(deployment_name):
        cmd = f'kubectl get pods -l app={deployment_name} -o json'
        result = subprocess.check_output(cmd, shell=True).decode('utf-8')
        pods = json.loads(result)['items']
        ips_and_ports = []
        for pod in pods:
            pod_ip = pod['status']['podIP']
            container_port = pod['spec']['containers'][0]['ports'][0]['containerPort']
            ips_and_ports.append((pod_ip, container_port))
        return ips_and_ports
    
    def add_ip_to_dict(deployment_name):
        pod_ips_ports = get_pod_ips_and_ports(deployment_name)
        app_to_number_of_instances[deployment_name] = len(pod_ips_ports)
        for pod_ip, port in pod_ips_ports:
            if app_label_to_service_dict[deployment_name] not in app_to_ips:
                app_to_ips[app_label_to_service_dict[deployment_name]] = [[pod_ip, port]]
            else:
                app_to_ips[app_label_to_service_dict[deployment_name]].append([pod_ip, port])
            ips_to_app[pod_ip] = app_label_to_service_dict[deployment_name]
            ips_to_port[pod_ip] = port
    
    # Get ips and ports for each service
    for app_deployment in app_label_to_service_dict:
        add_ip_to_dict(app_deployment)
    
    # Compelete the IP graph
    for edge in graph.out_edges():
        s1, s2 = edge
        print(f"Adding edge {s1} to {s2}")
        if app_label_to_service_dict[s1] in app_to_ips and app_label_to_service_dict[s2] in app_to_ips:
            ips1 = app_to_ips[app_label_to_service_dict[s1]]
            ips2 = app_to_ips[app_label_to_service_dict[s2]]
            for ip1 in ips1:
                for ip2 in ips2:
                    ip_graph.add_node(f"{ip1[0]}:{ips_to_port[ip1[0]]} - {ips_to_app[ip1[0]]}", group=ips_to_app[ip1[0]], size=20, ip=ip1[0], port=ips_to_port[ip1[0]], instances=app_to_number_of_instances[s1])
                    ip_graph.add_edge(f"{ip1[0]}:{ips_to_port[ip1[0]]} - {ips_to_app[ip1[0]]}", f"{ip2[0]}:{ips_to_port[ip2[0]]} - {ips_to_app[ip2[0]]}")
        else:
            print(f"Could not find {s1} or {s2} in app_to_ips")
    return ip_graph

app = Flask(__name__)

graphoptions = """const options = {
                        "edges": {
                            "color": {
                            "inherit": true
                            },
                            "selfReferenceSize": null,
                            "selfReference": {
                            "angle": 0.7853981633974483
                            },
                            "smooth": {
                            "forceDirection": "none"
                            },
                            "arrows": {
                                "to": {
                                    "enabled": true
                                },
                                "from": {
                                    "enabled": true,
                                    "scaleFactor": 0.5,
                                    "type": "bar"
                                }
                            }
                        },
                        "physics": {
                            "barnesHut": {
                            "springConstant": 0.001,
                            "avoidOverlap": 1
                            },
                            "minVelocity": 0.75
                        }
                        }
                        """

@app.route('/apply')
def apply():
    command = ["kubectl", "delete", "networkpolicies", "--all", "-n", NAMESPACE]
    subprocess.run(command, check=True)
    generate_and_apply_network_policies()
    html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>AutoArmor Pro Max</title>
            </head>
            <body>
                <h1>Network policies applied successfully!</h1>
            </body>
            </html>
                """
    return html

@app.route('/delete')
def delete():
    command = ["kubectl", "delete", "networkpolicies", "--all", "-n", NAMESPACE]
    subprocess.run(command, check=True)
    html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>AutoArmor Pro Max</title>
            </head>
            <body>
                <h1>Network policies deleted successfully!</h1>
            </body>
            </html>
                """
    return html


@app.route('/')
def index():
    net = Network(notebook=False, cdn_resources="remote", select_menu=True, filter_menu=True)
    net.from_nx(get_app_instances())
    net.set_options(graphoptions)
    # net.show_buttons()
    
    # write the graph to a standalone HTML file
    net.write_html('graph.html')
    with open("graph.html", "r") as f:
        html = f.read()
    
    # Modify the HTML code to include a title and a title bar
    html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>AutoArmor Pro Max</title>
                <style>
                    #title-bar {{
                        background-color: #4E2A84;
                        color: white;
                        height: 80px;
                        line-height: 80px;
                        padding-left: 10px;
                        padding-right: 10px;
                        display: flex;
                        align-items: center;
                    }}
                    #logo {{
                        background-image: url('https://common.northwestern.edu/v8/css/images/northwestern.svg');
                        background-repeat: no-repeat;
                        background-position: left center;
                        background-size: contain;
                        width: 120px;
                        height: 60px;
                        margin-right: 10px;
                    }}
                    #time {{
                        font-size: 12px;
                        margin-right: 10px;
                    }}
                    #countdown {{
                        font-size: 12px;
                    }}
                    #center-container {{
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        flex-direction: row;
                    }}
                    #time,
                    #countdown {{
                        margin: 10px;
                    }}
                </style>
                <link href="https://common.northwestern.edu/favicon.ico" rel="shortcut icon" type="image/x-icon"/>
                <link href="https://common.northwestern.edu/v8/icons/favicon-16.png" rel="icon" sizes="16x16" type="image/png"/>
                <link href="https://common.northwestern.edu/v8/icons/favicon-32.png" rel="icon" sizes="32x32" type="image/png"/>
                <link href="https://common.northwestern.edu/v8/icons/favicon-180.png" rel="apple-touch-icon" sizes="180x180"/>
            </head>
            <body>
                <div id="title-bar">
                    <div id="logo"></div>
                    <div>AutoArmor Pro Max</div>
                </div>
                {html}
                <div id="center-container">
                    <div id="time"></div>
                    <div id="countdown"></div>
                </div>
                <script>
                    function updateTime() {{
                        var d = new Date();
                        var chicagoTime = d.toLocaleString("en-US", {{timeZone: "America/Chicago"}});
                        document.getElementById("time").innerHTML = "Current Time: " + chicagoTime;
                    }}

                    function updateCountdown() {{
                        var countdownElement = document.getElementById("countdown");
                        var countdown = 600;
                        countdownElement.innerHTML = "Auto Reresh In: " + countdown + "s";
                        setInterval(function() {{
                            countdown--;
                            countdownElement.innerHTML = "Auto Reresh In: " + countdown + "s";
                            if (countdown == 0) {{
                                location.reload();
                            }}
                        }}, 1000);
                    }}

                    updateTime();
                    setInterval(updateTime, 1000);
                    updateCountdown();
                </script>
            </body>
            </html>

    """
    return render_template_string(html)

@app.route('/k8s')
def k8s():
    net = Network(notebook=False, cdn_resources="remote", select_menu=True, filter_menu=True)
    net.from_nx(get_app_instances_k8s())
    net.set_options(graphoptions)
    
    
    # write the graph to a standalone HTML file
    net.write_html('k8s_graph.html')
    with open("k8s_graph.html", "r") as f:
        html = f.read()
    
    # Modify the HTML code to include a title and a title bar
    html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>AutoArmor Pro Max</title>
                <style>
                    #title-bar {{
                        background-color: #4E2A84;
                        color: white;
                        height: 80px;
                        line-height: 80px;
                        padding-left: 10px;
                        padding-right: 10px;
                        display: flex;
                        align-items: center;
                    }}
                    #logo {{
                        background-image: url('https://common.northwestern.edu/v8/css/images/northwestern.svg');
                        background-repeat: no-repeat;
                        background-position: left center;
                        background-size: contain;
                        width: 120px;
                        height: 60px;
                        margin-right: 10px;
                    }}
                    #time {{
                        font-size: 12px;
                        margin-right: 10px;
                    }}
                    #countdown {{
                        font-size: 12px;
                    }}
                    #center-container {{
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        flex-direction: row;
                    }}
                    #time,
                    #countdown {{
                        margin: 10px;
                    }}
                </style>
                <link href="https://common.northwestern.edu/favicon.ico" rel="shortcut icon" type="image/x-icon"/>
                <link href="https://common.northwestern.edu/v8/icons/favicon-16.png" rel="icon" sizes="16x16" type="image/png"/>
                <link href="https://common.northwestern.edu/v8/icons/favicon-32.png" rel="icon" sizes="32x32" type="image/png"/>
                <link href="https://common.northwestern.edu/v8/icons/favicon-180.png" rel="apple-touch-icon" sizes="180x180"/>
            </head>
            <body>
                <div id="title-bar">
                    <div id="logo"></div>
                    <div>AutoArmor Pro Max</div>
                </div>
                {html}
                <div id="center-container">
                    <div id="time"></div>
                    <div id="countdown"></div>
                </div>
                <script>
                    function updateTime() {{
                        var d = new Date();
                        var chicagoTime = d.toLocaleString("en-US", {{timeZone: "America/Chicago"}});
                        document.getElementById("time").innerHTML = "Current Time: " + chicagoTime;
                    }}

                    function updateCountdown() {{
                        var countdownElement = document.getElementById("countdown");
                        var countdown = 600;
                        countdownElement.innerHTML = "Auto Reresh In: " + countdown + "s";
                        setInterval(function() {{
                            countdown--;
                            countdownElement.innerHTML = "Auto Reresh In: " + countdown + "s";
                            if (countdown == 0) {{
                                location.reload();
                            }}
                        }}, 1000);
                    }}

                    updateTime();
                    setInterval(updateTime, 1000);
                    updateCountdown();
                </script>
            </body>
            </html>

    """

    return render_template_string(html)

@app.route('/servicegraph')
def servicegraph():
    net = Network(notebook=False, cdn_resources="remote", select_menu=True, filter_menu=True)
    net.from_nx(graph)
    net.set_options(graphoptions)
    
    # write the graph to a standalone HTML file
    net.write_html('servicegraph.html')
    with open("servicegraph.html", "r") as f:
        html = f.read()
    
    # Modify the HTML code to include a title and a title bar
    html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>AutoArmor Pro Max</title>
                <style>
                    #title-bar {{
                        background-color: #4E2A84;
                        color: white;
                        height: 80px;
                        line-height: 80px;
                        padding-left: 10px;
                        padding-right: 10px;
                        display: flex;
                        align-items: center;
                    }}
                    #logo {{
                        background-image: url('https://common.northwestern.edu/v8/css/images/northwestern.svg');
                        background-repeat: no-repeat;
                        background-position: left center;
                        background-size: contain;
                        width: 120px;
                        height: 60px;
                        margin-right: 10px;
                    }}
                    #time {{
                        font-size: 12px;
                        margin-right: 10px;
                        margin: 10px;
                    }}
                    #center-container {{
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        flex-direction: row;
                    }}
                </style>
                <link href="https://common.northwestern.edu/favicon.ico" rel="shortcut icon" type="image/x-icon"/>
                <link href="https://common.northwestern.edu/v8/icons/favicon-16.png" rel="icon" sizes="16x16" type="image/png"/>
                <link href="https://common.northwestern.edu/v8/icons/favicon-32.png" rel="icon" sizes="32x32" type="image/png"/>
                <link href="https://common.northwestern.edu/v8/icons/favicon-180.png" rel="apple-touch-icon" sizes="180x180"/>
            </head>
            <body>
                <div id="title-bar">
                    <div id="logo"></div>
                    <div>AutoArmor Pro Max</div>
                </div>
                {html}
                <div id="center-container">
                    <div id="time"></div>
                </div>
                <script>
                    function updateTime() {{
                        var d = new Date();
                        var chicagoTime = d.toLocaleString("en-US", {{timeZone: "America/Chicago"}});
                        document.getElementById("time").innerHTML = "Current Time: " + chicagoTime;
                    }}
                    updateTime();
                    setInterval(updateTime, 1000);
                </script>
            </body>
            </html>

    """

    return render_template_string(html)

# Serve the utils.js file
@app.route('/lib/bindings/utils.js')
def serve_utils_js():
    return send_from_directory(os.path.join(app.root_path, 'lib/bindings'), 'utils.js')

if __name__ == '__main__':
    init()
    app.run()


