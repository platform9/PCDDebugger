

# **PCDdebugger**

PCDdebugger is a command-line tool designed to simplify and accelerate the troubleshooting process for PCD environments. It automates the collection of diagnostic information for various services and resources, consolidating the output into a structured directory for easy analysis and sharing.

## **Features**

* **Comprehensive Data Collection**: Gathers detailed information for key PCD resources including VMs (Nova), images (Glance), networks (Neutron), ports, volumes (Cinder), stacks (Heat), etc.  
* **Kubernetes Integration**: Performs a complete MySQL dump from a specified Kubernetes namespace, essential for debugging issues.  
* **Dependency Traversal**: Automatically discovers and collects data for resources related to a specified VM, such as its ports, volumes, network, subnets, image, and flavor.  
* **Standalone Binary**: Packaged as a single executable for macOS, Linux, and Windows, allowing users to run it without installing Python or any dependencies.  
* **Organized Output**: Saves all collected data into a timestamped directory, with subfolders for each service, making the information easy to navigate.  
* **Archive Option**: Includes a \--zip flag to automatically create a compressed archive of the collected data, ready for sharing.

---

## **Prerequisites**

While the script itself is a standalone binary, it relies on the following command-line tools being installed and configured on the machine where it is run:

* **openstack client**: Authenticated and configured to connect to your PCD cloud. (Ensure your rc file is sourced).  
* **kubectl**: Authenticated and configured to connect to your Kubernetes cluster. (This is only required in case of a mysql dump).  
* **yq**: A command-line YAML processor, used for parsing data from Consul.

---

## **Installation 💻**

Download the correct binary for your operating system from the latest GitHub Release.

[**➡️ Go to the Latest Releases Page**](https://www.google.com/search?q=https://github.com/platform9/PCDDebugger/releases/latest)

---

### **macOS & Linux**

Download the Binary  
From the latest release page, download the asset for your OS (e.g., PCDdebugger-v1.0.1-macos or PCDdebugger-v1.0.1-linux).  
Alternatively, you can use curl from your terminal with the specific version tag.

```
# For macOS (example with v1.0.1)
curl -LO https://github.com/platform9/PCDDebugger/releases/download/v1.0.1/PCDdebugger-v1.0.1-macos
# For Linux (example with v1.0.1)
curl -LO https://github.com/platform9/PCDDebugger/releases/download/v1.0.1/PCDdebugger-v1.0.1-linux
```

Make it Executable  
After downloading, rename the file for convenience and make it executable.

```
# Example for macOSmv
PCDdebugger-v1.0.1-macos PCDdebugger
# Add execute permissionchmod +x PCDdebugger
```

(Optional) Move to Your PATH  
To run PCDdebugger from any directory, move it to a location in your system's PATH.

```
sudo mv PCDdebugger /usr/local/bin/
```

---

### **Windows**

Download the Binary  
Method A: Using a Web Browser  
From the latest release page, download the .exe asset (e.g., PCDdebugger-v1.0.1-windows.exe).  
Method B: Using curl (Command Line)  
Open Command Prompt or PowerShell and use curl to download the file. curl is included in modern versions of Windows 10 and 11\.

```
# Example with v1.0.1
curl -L https://github.com/platform9/PCDDebugger/releases/download/v1.0.1/PCDdebugger-v1.0.1-windows.exe -o PCDdebugger.exe
```

1. Place it in a Folder  
   Move the downloaded PCDdebugger.exe file to a memorable location, for example, C:\\Tools\\.

2. (Optional) Add to PATH  
   To run the tool from any command prompt, add the folder to your system's PATH environment variable.  
   1. Search for "Edit the system environment variables" in the Start Menu.  
   2. Click the "Environment Variables..." button.  
   3. Under "System variables", find and select the Path variable, then click "Edit...".  
   4. Click "New" and add the path to your folder (e.g., C:\\Tools).  
   5. Click OK on all windows to save.

You can now run PCDdebugger.exe from PowerShell or Command Prompt.

---

## **Usage**

The basic command structure is:

```
./PCDdebugger [RESOURCE_FLAG] [OPTIONS]
```

*(Note: On Windows, use PCDdebugger.exe instead of ./PCDdebugger)*

### **Examples**

**Collect all information for a specific VM:**

```
./PCDdebugger --vm <VM_ID_OR_NAME>
```

**Collect details for a specific Glance image:**

.

```
/PCDdebugger --image <IMAGE_ID_OR_NAME>
```

**Collect details for a Neutron network and its subnets:**

```
./PCDdebugger --network <NETWORK_ID>
```

**Perform a MySQL dump from a Kubernetes cluster:**  
**The \--namespace flag is required for this operation.**

```
./PCDdebugger --mysql-dump --namespace <K8S_NAMESPACE>
```

**Note:** For the MySQL dump to work, you must run this tool on a management cluster node and ensure your KUBECONFIG environment variable is exported correctly for that cluster.

**Combine multiple flags and create a zip archive:**

```
./PCDdebugger --vm <VM_ID> --mysql-dump --namespace <K8S_NAMESPACE> --zip
```

**Specify a custom output directory and create a zip archive:**

```
./PCDdebugger --vm <VM_ID> --output ./my-debug-session --zip
```

---

## 

## **What It Collects**

All output is saved to a directory named PCDdebugger-\<TIMESTAMP\> by default.

#### **General Health Checks (/health)**

* compute\_services.txt: pcd compute service list \--long  
* network\_agents.txt: pcd network agent list \--long  
* And more...

#### **Nova (/nova)**

* server\_show.txt: pcd server show \<VM\_ID\>  
* server\_events.txt: pcd server event list \<VM\_ID\>  
* And more...

*(The rest of the sections for Glance, Neutron, Cinder, etc. remain the same)*

---

## **Building from Source**

If you want to build the binary yourself, you can do so with PyInstaller.

Clone the repository:

```
git clone https://github.com/platform9/PCDDebugger.git
cd PCDDebugger
```

Install dependencies:

```
pip install pyinstaller
```

Build the binary:

```
pyinstaller --onefile --name PCDdebugger pcddebugger.py
```

The final executable for your current operating system will be located in the dist/ directory.
