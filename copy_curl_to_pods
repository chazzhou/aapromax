import subprocess

# Set the namespace you want to copy the file to
namespace = "eureka-demo"

# Set the source file path and destination file path
src_file = "./curl-amd64"
dest_file = "/usr/local/bin/curl"

# Use the `kubectl get pods` command to list all the pods in the namespace
pods_output = subprocess.check_output(["kubectl", "get", "pods", "-n", namespace, "-o", "jsonpath='{.items[*].metadata.name}'"])

# Loop through the list of pod names and copy the file to each pod
for pod_name in pods_output.decode().strip("'").split(" "):
    # Use the `kubectl cp` command to copy the file to the pod
    subprocess.run(["kubectl", "cp", src_file, f"{pod_name}:{dest_file}"])
    # Use the `kubectl exec` command to set the executable permissions on the destination file
    subprocess.run(["kubectl", "exec", "-n", namespace, pod_name, "--", "chmod", "+x", dest_file])
    print(f"Copied {src_file} to {dest_file} and set executable permissions in pod {pod_name}")
