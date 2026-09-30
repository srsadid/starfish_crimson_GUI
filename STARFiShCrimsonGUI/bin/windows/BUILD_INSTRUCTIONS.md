# Windows Build Instructions for NetlistEditor

If the pre-built `CRIMSONBCT.exe` is missing from this directory, you can build it from scratch using the source code provided in `STARFiShCrimsonGUI/NetlistEditor`.

## Prerequisites
1. **Visual Studio** (with C++ Desktop Development workload)
2. **CMake**
3. **vcpkg** (C++ Library Manager)

## Step 1: Install Dependencies
Open a Command Prompt and use vcpkg to install the required Qt and Boost libraries:
```cmd
vcpkg install qt5-base qt5-svg qwt boost
```

## Step 2: Configure and Build
Open a **Developer Command Prompt for Visual Studio** and navigate to the `STARFiShCrimsonGUI/NetlistEditor` directory:
```cmd
cd path\to\STARFiShCrimsonGUI\NetlistEditor
mkdir build
cd build

cmake -DCMAKE_TOOLCHAIN_FILE="[path-to-your-vcpkg]\scripts\buildsystems\vcpkg.cmake" -G "Visual Studio 17 2022" -A x64 ..

cmake --build . --config Release
```

## Step 3: Deploy
Once compiled, copy the resulting executable (`bin\Release\CRIMSONBCT.exe`) into **this directory** (`STARFiShCrimsonGUI/bin/windows/`). 
You will also need to copy the Qt5 and Qwt `.dll` files (like `Qt5Core.dll`, `Qt5Gui.dll`, `qwt.dll`) from your vcpkg installation into this directory alongside the executable so it can run independently.
