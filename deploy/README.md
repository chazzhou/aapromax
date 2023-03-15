# deploy.py README

The `deploy.py` script is a utility for managing deployments and services in a Kubernetes cluster. It reads configuration files from `deployment.yml` and `service.yml` files located in `k8s` subdirectories of the project and deploys, updates, or deletes resources based on user input.

## Features

1. Deploy `deployment.yml` files to a specified namespace
2. Delete `deployment.yml` files from a specified namespace
3. Apply `service.yml` files to a specified namespace
4. Delete `service.yml` files from a specified namespace
5. Delete all deployments under a specified namespace

## Usage

Run the script with Python:

```python deploy.py```

You will be prompted to select an option (1-5) and input the namespace you want to apply the action to. The script will then iterate through each `k8s` subdirectory, applying the selected action.

## Requirements

- Python 3
- `kubectl` installed and configured to access your Kubernetes cluster