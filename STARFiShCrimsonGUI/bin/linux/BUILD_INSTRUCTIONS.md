# Linux Build Instructions for NetlistEditor

If the pre-built `CRIMSONBCT` executable is missing from this directory, you can build it from scratch using the source code provided in `STARFiShCrimsonGUI/NetlistEditor`.

## Step 1: Install Dependencies
Install the required development packages. On Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install build-essential cmake qtbase5-dev libqt5svg5-dev libqwt-qt5-dev libboost-dev
```

## Step 2: Configure and Build
Navigate to the source code folder and use CMake:
```bash
cd path/to/STARFiShCrimsonGUI/NetlistEditor
mkdir build && cd build

cmake ..
make -j4
```

## Step 3: Deploy
Once compiled, copy the resulting executable (`bin/CRIMSONBCT`) into **this directory** (`STARFiShCrimsonGUI/bin/linux/`).
Because Linux dynamic linker resolves Qt system libraries automatically, you usually do not need to bundle the Qt shared objects. The Slicer extension will automatically execute `CRIMSONBCT` from this folder.
