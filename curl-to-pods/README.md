# copy_curl_to_pods.py

This script automates the process of copying the `curl` utility to all the pods within a specified Kubernetes namespace and setting its executable permissions. It's particularly useful when you need to distribute the `curl` utility across multiple pods in a namespace, ensuring that it has the correct permissions for execution.

## Usage

1. Set the `namespace` variable to the desired Kubernetes namespace.
2. Set the `src_file` variable to the source file path (e.g., `./curl-amd64`).
3. Set the `dest_file` variable to the destination file path (e.g., `/usr/local/bin/curl`).

Once the variables are set, run the script. It will retrieve a list of pod names in the specified namespace using `kubectl get pods`. For each pod, the script uses `kubectl cp` to copy the source file to the destination path within the pod, and `kubectl exec` to set the executable permissions for the copied file.

## Requirements

- Python 3
- `kubectl` installed and configured to access your Kubernetes cluster
- Single binary curl file like https://github.com/moparisthebest/static-curl

Make sure the `curl` utility you want to copy to the pods is present in the same directory as the script or modify the `src_file` variable accordingly.