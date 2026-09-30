# macOS Build Instructions for NetlistEditor

If the pre-built `CRIMSON Boundary Condition Toolbox.app` is missing from this directory, you can build it from scratch using the source code provided in `STARFiShCrimsonGUI/NetlistEditor`.

## Prerequisites
The easiest way to install dependencies on macOS is via [Homebrew](https://brew.sh/).

## Step 1: Install Dependencies
Open Terminal and run:
```bash
brew install cmake qt@5 qwt-qt5 boost
```

## Step 2: Configure and Build
Navigate to the source code folder and use CMake:
```bash
cd path/to/STARFiShCrimsonGUI/NetlistEditor
mkdir build && cd build

# NOTE: If you are on an Apple Silicon Mac (M1/M2/M3), Homebrew installs to /opt/homebrew/ instead of /usr/local/
# For Intel Macs:
cmake -DCMAKE_PREFIX_PATH="/usr/local/opt/qt@5;/usr/local/opt/qwt-qt5" ..

# For Apple Silicon Macs:
# cmake -DCMAKE_PREFIX_PATH="/opt/homebrew/opt/qt@5;/opt/homebrew/opt/qwt-qt5" ..

make -j4
```

## Step 3: Deploy
Once compiled, CMake will generate a macOS App Bundle inside `bin/CRIMSON Boundary Condition Toolbox.app`. 
Copy that `.app` folder into **this directory** (`STARFiShCrimsonGUI/bin/macos/`). 
The Slicer extension will automatically detect it and launch the internal binary (`Contents/MacOS/CRIMSONBCT`).
