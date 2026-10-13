@echo off
setlocal enabledelayedexpansion
rem ===========================================================================
rem OPAL-OKB — сборка нативного C++ ядра _opal_native.pyd ОДНОЙ командой.
rem
rem   native\build.bat
rem
rem Каскад тулчейнов (первый найденный побеждает):
rem   1. MSVC BuildTools (vcvars64: VS 18/17/16) + Ninja;
rem   2. портативный MinGW-w64 в %LOCALAPPDATA%\opal-native-toolchain\mingw64
rem      (без прав администратора; bootstrap: см. native\README.md);
rem   3. g++ из PATH.
rem Ninja и cmake берутся из pip (py -3 -m pip install cmake ninja pybind11).
rem Результат: _opal_native.pyd в КОРНЕ репозитория.
rem ===========================================================================
set "REPO=%~dp0.."
pushd "%REPO%" || exit /b 1

echo [build] repo: %CD%

rem --- утилиты сборки (тихо; уже установленные не трогаем) ---
py -3 -m pip install --quiet --disable-pip-version-check cmake ninja pybind11
if errorlevel 1 goto :fail

for /f "usebackq delims=" %%i in (`py -3 -c "import cmake; print(cmake.CMAKE_BIN_DIR)"`) do set "CMAKE_BIN=%%i"
for /f "usebackq delims=" %%i in (`py -3 -c "import ninja; print(ninja.BIN_DIR)"`) do set "NINJA_BIN=%%i"
for /f "usebackq delims=" %%i in (`py -3 -c "import pybind11; print(pybind11.get_cmake_dir())"`) do set "PYBIND11_DIR=%%i"
for /f "usebackq delims=" %%i in (`py -3 -c "import sys; print(sys.executable)"`) do set "PY_EXE=%%i"
if not defined PYBIND11_DIR goto :fail
set "PATH=%CMAKE_BIN%;%NINJA_BIN%;%PATH%"

set "CFG_ARGS=-S native -B native\build -G Ninja -DCMAKE_MAKE_PROGRAM=ninja -DCMAKE_BUILD_TYPE=Release -Dpybind11_DIR="%PYBIND11_DIR%" -DPython_EXECUTABLE="%PY_EXE%""

set "DONE="

rem --- 1. MSVC (vcvars64) ----------------------------------------------------
set "VCVARS="
if exist "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if not defined VCVARS if exist "C:\Program Files\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" set "VCVARS=C:\Program Files\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if not defined VCVARS if exist "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" set "VCVARS=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
if not defined VCVARS if exist "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"

if defined VCVARS (
    echo [build] toolchain: MSVC (!VCVARS!)
    call "!VCVARS!" >nul 2>&1
    if errorlevel 1 goto :mingw
    cmake %CFG_ARGS%
    if errorlevel 1 goto :mingw
    set "DONE=1"
)

rem --- 2. портативный MinGW-w64 ------------------------------------------------
:mingw
if defined DONE goto :dobuild
set "MINGW=%LOCALAPPDATA%\opal-native-toolchain\mingw64\bin"
if exist "%MINGW%\g++.exe" (
    echo [build] toolchain: MinGW-w64 (%MINGW%)
    cmake %CFG_ARGS% -DCMAKE_C_COMPILER="%MINGW%\gcc.exe" -DCMAKE_CXX_COMPILER="%MINGW%\g++.exe"
    if errorlevel 1 goto :fail
    set "DONE=1"
    goto :dobuild
)

rem --- 3. g++ из PATH ----------------------------------------------------------
where g++.exe >nul 2>&1
if %errorlevel%==0 (
    echo [build] toolchain: MinGW из PATH
    cmake %CFG_ARGS%
    if errorlevel 1 goto :fail
    set "DONE=1"
    goto :dobuild
)

echo [build] ERROR: компилятор C++ не найден (нет MSVC vcvars64, нет MinGW). См. native\README.md
goto :fail

:dobuild
cmake --build native\build --config Release
if errorlevel 1 goto :fail

set "PYD="
for %%f in (native\build\_opal_native*.pyd) do set "PYD=%%f"
if not defined PYD for %%f in (native\build\Release\_opal_native*.pyd) do set "PYD=%%f"
if not defined PYD (
    echo [build] ERROR: _opal_native.pyd не найден после сборки
    goto :fail
)
copy /y "%PYD%" "_opal_native.pyd" >nul
if errorlevel 1 goto :fail

py -3 -c "import sys; sys.path.insert(0, '.'); import _opal_native as n; print('[build] import OK, EPSILON =', n.EPSILON)"
if errorlevel 1 goto :fail

popd
echo [build] ГОТОВО: %REPO%\_opal_native.pyd
exit /b 0

:fail
popd
echo [build] FAIL
exit /b 1
