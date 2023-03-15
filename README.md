# AutoArmor Pro Max (Version 1.0)

AutoArmor Pro Max is a Python script that analyzes and visualizes microservice architectures in containerized applications. It extracts and decompiles Docker images to find the corresponding JAR files and the `application.yml` files within. AA Pro Max then processes this information to build a directed graph of microservice dependencies.

## Prerequisites

- Python 3.6 or higher
- Docker images containing Java microservices
- A running Eureka server
- `kubectl` configured with access to your Kubernetes cluster
- [CFR (Class File Reader)](https://www.benf.org/other/cfr/) - A Java decompiler

## Usage

```bash
python aa_pro_max.py <docker_image_tar_folder> <cfr_tool_path> <output_directory> <namespace> <root_dir>
```

- `<docker_image_tar_folder>`: The path to the folder containing the Docker image .tar files.
- `<cfr_tool_path>`: The path to the CFR (Class File Reader) JAR file. This tool is used for decompiling JAR files.
- `<output_directory>`: The path where output files and directories should be saved.
- `<namespace>`: The Kubernetes namespace to use (not used in the current version).
- `<root_dir>`: The path to the root directory containing `application.yml` and `deployment.yml` files.

### Example

```bash
python3 aa_pro_max.py ./inputs ./cfr-0.152.jar ./outputs eureka-demo ./
```

## Output

The script generates several directories and files within the specified `output_directory`:

- `docker_image`: Contains extracted Docker images.
- `extracted_layers`: Contains extracted layers from the Docker images.
- `jars_decompiled`: Contains decompiled JAR files and their associated Java source code.

The script also prints the service discovery name, the number of services parsed, and detailed information about the processing of each Docker image, JAR file, and Java source code file.

## Function Descriptions

### init()

The `init()` function is the initial function responsible for extracting and decompiling the JAR files contained within Docker images, parsing their application.yml configuration files, and building an inter-service communication graph based on the parsed data. It performs the following tasks:

1. It searches for application.yml and deployment.yml files within the root directory and adds the application name and service name to a dictionary.
2. It loops through the Docker image .tar files in the specified folder, and if the image is not already extracted, it extracts the image.
3. It locates and extracts the layers of the Docker image, and then searches for JAR files within the extracted layers.
4. If JAR files are found, it decompiles them using the CFR tool, and then parses the application.yml files to extract the service names and inter-service communication information.
5. It checks the decompiled source code for `@FeignClient` annotations to identify additional inter-service communication and adds these relationships to the graph.
6. It adds connections between nodes and the Eureka server for service discovery.
7. Finally, it prints the number of successfully parsed services and completes the initialization.

Upon completion, the `init()` function will have built a graph representing the inter-service communication within the given application, which can then be used to generate network policies.

### generate_and_apply_network_policies()

This function generates and applies the network policies based on the Eureka service discovery data. It first creates a folder for the network policies and removes any existing policies. Then, it iterates through the application instances and generates a network policy for each instance. Finally, it applies the generated policies to the Kubernetes cluster using `kubectl apply`.

### generate_network_policy(pod, ips_from_the_pod, ips_to_the_pod)

This function generates a network policy for the given application instance (pod) based on the IP addresses it communicates with. It takes the pod's IP address and port, and lists of IP addresses it communicates to and from. The function creates ingress and egress rules for the instance and writes the policy to a YAML file in the output directory.

### get_app_instances()

This function retrieves the application instances from the Eureka server and populates a directed graph with the instances' IP addresses and ports. It sends a GET request to the Eureka server and parses the XML response to extract the instance data. The function then adds the instances to the graph as nodes and connects them based on the inter-service communication graph.

### get_pod_ips_and_ports(deployment_name)

This function retrieves the IP addresses and container ports of all pods associated with a given Kubernetes deployment. It calls `kubectl get pods` with the specified deployment name and parses the JSON output to extract the pod IP addresses and container ports. The function returns a list of tuples containing the pod IP addresses and container ports.

## How It Works

1. The script calls the `get_app_instances()` function to obtain the Eureka server's application instances data and create a directed graph of the IP addresses and ports.
2. The `generate_and_apply_network_policies()` function is called to generate network policies for each application instance.
3. The script iterates through the graph nodes and for each node, it collects the IP addresses it communicates with (both incoming and outgoing).
4. The `generate_network_policy()` function is called for each node to generate a network policy based on the collected IP addresses.
5. The generated network policies are written to YAML files in the output directory.
6. The script applies the generated network policies to the Kubernetes cluster using `kubectl apply`.

## Example

Suppose you have an application with the following inter-service communication graph:

```
A -> B -> C
B -> D
```

When you run the script, it will generate network policies for each application instance in your Eureka service registry. The generated network policies will allow the following communication:

- Instances of A can communicate with instances of B.
- Instances of B can communicate with instances of C and D.
- Instances of C and D cannot communicate with any other instances.

The script will also generate ingress and egress rules to allow communication with the Eureka server and Kubernetes services.

## Tips

- Make sure your Kubernetes cluster is running and `kubectl` is configured with the correct context and namespace.
- Ensure that your Eureka server is running and the application instances are registered with it.
- Update the `graph` variable in the script to match your application's inter-service communication graph.
- Check the output directory for the generated network policy YAML files and review them to ensure they match your expected policies.

## Flask Routes

### Routes

1. `/`: The root route displays an ip call graph generated from Eureka data. The graph is generated using the PyVis library and is periodically auto-refreshed.

2. `/k8s`: This route generates an ip call graph from the Kubernetes (K8s) data using kubectl.

3. `/apply`: When accessed, this route applies network policies by deleting any existing network policies in the specified namespace and generating new ones. The HTML response confirms the successful application of network policies.

4. `/delete`: When accessed, this route deletes all network policies in the specified namespace. The HTML response confirms the successful deletion of network policies.

5. `/servicegraph`: This route generates a service graph representation using the PyVis library.

6. `/lib/bindings/utils.js`: This route serves the "utils.js" JavaScript file from the 'lib/bindings' directory.

### Usage

These Flask routes are designed to provide a user-friendly interface for managing network policies and visualizing instances. Users can navigate to the appropriate route in their web browser to perform actions or view the various graph representations.
