# **PCDdebugger**

PCDdebugger is a command-line Python script designed to simplify and accelerate the troubleshooting process for PCD environments. It automates the collection of diagnostic information for various services and resources, consolidating the output into a structured directory for easy analysis and sharing.

## **Features**

* **Comprehensive Data Collection:** Gathers detailed information for key PCD resources including VMs (Nova), images (Glance), networks (Neutron), ports, volumes (Cinder), stacks (Heat), and users (Keystone).  
* **Kubernetes Integration:** Performs a complete MySQL dump from a specified Kubernetes namespace, essential for debugging control plane issues.  
* **Dependency Traversal:** Automatically discovers and collects data for resources related to a specified VM, such as its ports, volumes, network, subnets, image, and flavor.  
* **Organized Output:** Saves all collected data into a timestamped directory, with subfolders for each service, making the information easy to navigate.  
* **Archive Option:** Includes a \--zip flag to automatically create a compressed archive of the collected data, ready for sharing.

## **Prerequisites**

Before running the script, ensure the following are installed and configured on your machine:

* **Python 3.6+**  
* **pcd client:** Authenticated and configured to connect to your pCD cloud. (Ensure your rc file is sourced).  
* **kubectl:** Authenticated and configured to connect to your Kubernetes cluster.  
* **yq:** A command-line YAML processor, used for parsing data from Consul.

## **Installation**

1. **Clone the repository:**  
   git clone https://github.com/chandSatyansh/PCDdebugger.git  
   cd PCDdebugger

2. **Make the script executable (optional but recommended):**  
   chmod \+x ./pcddebugger.py

## **Usage**

The basic command structure is:

./pcddebugger.py \[RESOURCE\_FLAG\] \[OPTIONS\]

### **Examples**

* Collect all information for a specific VM:  
  This will gather details for the VM, its ports, volumes, network, subnets, image, and flavor.  
  ./pcddebugger.py \--vm \<VM\_ID\_OR\_NAME\>

* **Collect details for a specific Glance image:**  
  ./pcddebugger.py \--image \<IMAGE\_ID\_OR\_NAME\>

* **Collect details for a Neutron network and its subnets:**  
  ./pcddebugger.py \--network \<NETWORK\_ID\>

* Perform a MySQL dump from a Kubernetes cluster:  
  The \--namespace flag is required for this operation.  
  ./pcddebugger.py \--mysql-dump \--namespace \<K8S\_NAMESPACE\>

* **Combine multiple flags and create a zip archive:**  
  ./pcddebugger.py \--vm \<VM\_ID\> \--mysql-dump \--namespace \<K8S\_NAMESPACE\> \--zip

* **Specify a custom output directory and create a zip archive:**  
  ./pcddebugger.py \--vm \<VM\_ID\> \--output ./my-debug-session \--zip

## **What It Collects**

All output is saved to a directory named PCDdebugger-\<TIMESTAMP\> by default.

### **General Health Checks (/health)**

* compute\_services.txt: openstack compute service list \--long  
* network\_agents.txt: openstack network agent list \--long  
* volume\_services.txt: openstack volume service list \--long  
* hypervisors.txt: openstack hypervisor list \--long  
* And more...

### **Nova (/nova)**

* server\_show.txt: openstack server show \<VM\_ID\>  
* server\_events.txt: openstack server event list \<VM\_ID\>  
* migrations.txt: openstack server migration list \--server \<VM\_ID\>  
* flavor\_show.txt: openstack flavor show \<FLAVOR\_ID\>

### **Glance (/glance)**

* image\_show.txt: openstack image show \<IMAGE\_ID\>

### **Neutron (/neutron)**

* vm\_ports\_list.txt: openstack port list \--device-id \<VM\_ID\>  
* port\_\<PORT\_ID\>.txt: openstack port show \<PORT\_ID\>  
* network\_\<NETWORK\_ID\>.txt: openstack network show \<NETWORK\_ID\>  
* subnet\_\<SUBNET\_ID\>.txt: openstack subnet show \<SUBNET\_ID\>  
* security\_group\_\<SG\_ID\>.txt: openstack security group show \<SG\_ID\>

### **Cinder (/cinder)**

* attached\_volumes\_list.txt: List of volumes attached to a VM.  
* volume\_\<VOLUME\_ID\>.txt: openstack volume show \<VOLUME\_ID\>

### **Heat (/heat)**

* stack\_show.txt: openstack stack show \<STACK\_ID\>  
* stack\_resources.txt: openstack stack resource list \<STACK\_ID\>

### **Keystone (/keystone)**

* user\_show.txt: openstack user show \<USER\_ID\>  
* user\_role\_assignments.txt: openstack role assignment list \--user \<USER\_ID\>

### **Database (/database)**

* mysql\_dump\_all\_databases.sql.gz: A compressed dump of all MySQL databases from the specified Kubernetes pod. This includes the following databases from the workload region:  
  * alertmanager  
  * appcatalog  
  * barbican  
  * ceilometer  
  * cinder  
  * designate  
  * glance  
  * gnocchi  
  * hamgr  
  * heat  
  * horizon  
  * masakari  
  * mors  
  * neutron  
  * nova  
  * nova\_api  
  * nova\_cell0  
  * octavia  
  * placement  
  * preference\_store  
  * resmgr  
  * terrakube  
  * watcher