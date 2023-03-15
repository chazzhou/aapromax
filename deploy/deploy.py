import os

def get_folders():
    # Returns a list of subdirectories in the current directory
    return next(os.walk('.'))[1]

def deploy_deployment(namespace):
    # Deploys the deployment.yml files in each k8s subfolder to the specified namespace
    folders = get_folders()
    for folder in folders:
        k8s_dir = os.path.join(folder, 'k8s')
        if os.path.exists(k8s_dir):
            deployment_file = os.path.join(k8s_dir, 'deployment.yml')
            os.system(f'kubectl apply -f {deployment_file} -n {namespace}')

def delete_deployment(namespace):
    # Deletes the deployment.yml files in each k8s subfolder from the specified namespace
    folders = get_folders()
    for folder in folders:
        k8s_dir = os.path.join(folder, 'k8s')
        if os.path.exists(k8s_dir):
            deployment_file = os.path.join(k8s_dir, 'deployment.yml')
            os.system(f'kubectl delete -f {deployment_file} -n {namespace}')

def apply_service(namespace):
    # Applies the service.yml files in each k8s subfolder to the specified namespace
    folders = get_folders()
    for folder in folders:
        k8s_dir = os.path.join(folder, 'k8s')
        if os.path.exists(k8s_dir):
            service_file = os.path.join(k8s_dir, 'service.yml')
            os.system(f'kubectl apply -f {service_file} -n {namespace}')

def delete_service(namespace):
    # Deletes the service.yml files in each k8s subfolder from the specified namespace
    folders = get_folders()
    for folder in folders:
        k8s_dir = os.path.join(folder, 'k8s')
        if os.path.exists(k8s_dir):
            service_file = os.path.join(k8s_dir, 'service.yml')
            os.system(f'kubectl delete -f {service_file} -n {namespace}')

def delete_all_deployments(namespace):
    # Deletes all deployments from the specified namespace
    os.system(f'kubectl delete deployments --all -n {namespace}')

# Display menu options
print('Select an option:')
print('1. Deploy deployment.yml files')
print('2. Delete deployment.yml files')
print('3. Apply service.yml files')
print('4. Delete service.yml files')
print('5. Delete all deployments under a namespace')

option = input('Enter your choice (1/2/3/4/5): ')

# Get the namespace to deploy/delete the files to/from
namespace = input('Enter the namespace to deploy/delete the files from: ')

if option == '1':
    deploy_deployment(namespace)
elif option == '2':
    delete_deployment(namespace)
elif option == '3':
    apply_service(namespace)
elif option == '4':
    delete_service(namespace)
elif option == '5':
    delete_all_deployments(namespace)
else:
    print('Invalid option selected')