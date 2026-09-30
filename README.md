# STARFiSh-CRIMSON GUI

A dedicated graphical user interface for STARFiSh (Cardiovascular-Biomechanics), seamlessly integrated as a **3D Slicer Extension**.

This repository decouples the visual editor and data visualization components from the core STARFiSh simulation engine, allowing for independent development, cleaner tracking, and a more robust user experience.

## Features

- **VMTK Centerlines**: Extract centerlines from 3D vascular segmentations directly within Slicer, without leaving the module.
- **Model Builder**: An OS-agnostic launchpad for the `CRIMSONBCT` Netlist Editor, enabling users to construct and edit 1D vascular network topologies.
- **Result Visualization**: An interactive, PythonQt-safe Matplotlib rendering interface for exploring `.h5` / `.hdf5` STARFiSh simulation results. Includes options for time-series and spatial profile plotting.

## Installation

1. Open [3D Slicer](https://download.slicer.org/).
2. Navigate to **Edit** > **Application Settings** > **Modules**.
3. Under **Additional module paths**, click **Add** and select the `STARFiShCrimsonGUI` folder from this repository.
4. Restart Slicer. The module will now be available under the **STARFiSh-CRIMSON** category in the modules dropdown.

## Requirements

The extension will automatically attempt to install the following dependencies into Slicer's Python environment upon launch if they are missing:
- `h5py`
- `matplotlib`

## Building the Netlist Editor (Developers)

The extension relies on a pre-compiled C++ binary (`CRIMSONBCT`) to launch the Model Builder. 
Binaries should be placed in the respective `bin/` subdirectories (`bin/windows`, `bin/linux`, `bin/macos`).

If a binary is missing for your operating system, please refer to the `BUILD_INSTRUCTIONS.md` file located inside your OS-specific `bin/` folder for instructions on compiling the editor from source using CMake.

## Acknowledgements

Developed by Sadman Sadid (University of Michigan) for the STARFiSh Cardiovascular-Biomechanics project.
