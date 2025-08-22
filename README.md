# **PCDdebugger**

PCDdebugger is a command-line tool designed to simplify and accelerate the troubleshooting process for PCD environments. It automates the collection of diagnostic information for various services and resources, consolidating the output into a structured directory for easy analysis and sharing.

## **Features**

* **Comprehensive Data Collection:** Gathers detailed information for key PCD resources including VMs (Nova), images (Glance), networks (Neutron), ports, volumes (Cinder), stacks (Heat) etc.  
* **Kubernetes Integration:** Performs a complete MySQL dump from a specified Kubernetes namespace, essential for debugging issues.  
* **Dependency Traversal:** Automatically discovers and collects data for resources related to a specified VM, such as its ports, volumes, network, subnets, image, and flavor.  
* **Standalone Binary:** Packaged as a single executable, allowing users to download and run it without installing Python or any dependencies.  
* **Organized Output:** Saves all collected data into a timestamped directory, with subfolders for each service, making the information easy to navigate.  
* **Archive Option:** Includes a \--zip flag to automatically create a compressed archive of the collected data, ready for sharing.

## **Prerequisites**

While the script itself is a standalone binary, it relies on the following command-line tools being installed and configured on the machine where it is run:

* **openstack client:** Authenticated and configured to connect to your PCD cloud. (Ensure your rc file is sourced).  
* **kubectl:** Authenticated and configured to connect to your Kubernetes cluster.( This is only required in case of mysql dump)  
* **yq:** A command-line YAML processor, used for parsing data from Consul.

## **Installation**

You can download the latest binary directly from the GitHub Releases page.

1. Download the executable:  
   Use curl to download the PCDdebugger binary from the latest release.  
   \# Replace v1.0.0 with the latest release tag  
   curl \-LJO https://github.com/chandSatyansh/PCDdebugger/releases/download/v1.0.0/PCDdebugger

2. **Make the binary executable:**  
   chmod \+x ./PCDdebugger

3. Run the tool:  
   You can now run the tool directly from your terminal.  
   ./PCDdebugger \--help

## **Usage**

The basic command structure is:

./PCDdebugger \[RESOURCE\_FLAG\] \[OPTIONS\]

### **Examples**

* Collect all information for a specific VM:  
  This will gather details for the VM, its ports, volumes, network, subnets, image, and flavor.  
  ./PCDdebugger \--vm \<VM\_ID\_OR\_NAME\>

* **Collect details for a specific Glance image:**  
  ./PCDdebugger \--image \<IMAGE\_ID\_OR\_NAME\>

* **Collect details for a Neutron network and its subnets:**  
  ./PCDdebugger \--network \<NETWORK\_ID\>

* Perform a MySQL dump from a Kubernetes cluster:  
  The \--namespace flag is required for this operation.  
  ./PCDdebugger \--mysql-dump \--namespace \<K8S\_NAMESPACE\>

* **Combine multiple flags and create a zip archive:**  
  ./PCDdebugger \--vm \<VM\_ID\> \--mysql-dump \--namespace \<K8S\_NAMESPACE\> \--zip

* **Specify a custom output directory and create a zip archive:**  
  ./PCDdebugger \--vm \<VM\_ID\> \--output ./my-debug-session \--zip

## **What It Collects**

All output is saved to a directory named PCDdebugger-\<TIMESTAMP\> by default.

### **General Health Checks (/health)**

* compute\_services.txt: pcd compute service list \--long  
* network\_agents.txt: pcd network agent list \--long  
* volume\_services.txt: pcd volume service list \--long  
* hypervisors.txt: pcd hypervisor list \--long  
* And more...

### **Nova (/nova)**

* server\_show.txt: pcd server show \<VM\_ID\>  
* server\_events.txt: pcd server event list \<VM\_ID\>  
* migrations.txt: pcd server migration list \--server \<VM\_ID\>  
* flavor\_show.txt: pcd flavor show \<FLAVOR\_ID\>

### **Glance (/glance)**

* image\_show.txt: pcd image show \<IMAGE\_ID\>

### **Neutron (/neutron)**

* vm\_ports\_list.txt: pcd port list \--device-id \<VM\_ID\>  
* port\_\<PORT\_ID\>.txt: pcd port show \<PORT\_ID\>  
* network\_\<NETWORK\_ID\>.txt: pcd network show \<NETWORK\_ID\>  
* subnet\_\<SUBNET\_ID\>.txt: pcd subnet show \<SUBNET\_ID\>  
* security\_group\_\<SG\_ID\>.txt: pcd security group show \<SG\_ID\>

### **Cinder (/cinder)**

* attached\_volumes\_list.txt: List of volumes attached to a VM.  
* volume\_\<VOLUME\_ID\>.txt: pcd volume show \<VOLUME\_ID\>

### **Heat (/heat)**

* stack\_show.txt: pcd stack show \<STACK\_ID\>  
* stack\_resources.txt: pcd stack resource list \<STACK\_ID\>

### **Keystone (/keystone)**

* user\_show.txt: pcd user show \<USER\_ID\>  
* user\_role\_assignments.txt: pcd role assignment list \--user \<USER\_ID\>

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

## **Building from Source**

If you want to build the binary yourself, you can do so with PyInstaller.

1. **Clone the repository:**  
   git clone https://github.com/chandSatyansh/PCDdebugger.git  
   cd PCDdebugger

2. **Install dependencies:**  
   pip install pyinstaller

3. **Build the binary:**  
   pyinstaller \--onefile \--name PCDdebugger pcddebugger.py

The final executable will be located in the dist/ directory.# PCDDebugger
