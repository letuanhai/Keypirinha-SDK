@echo off
setlocal

set PACKAGE_NAME=DevDocs
set INSTALL_DIR=%APPDATA%\Keypirinha\InstalledPackages

if "%1"=="" goto help
if "%1"=="-h" goto help
if "%1"=="--help" goto help
if "%1"=="help" (
    :help
    echo Usage:
    echo   make help
    echo   make clean
    echo   make build
    echo   make install
    echo   make dev
    echo   make py [python_args]
    goto end
)

if "%BUILD_DIR%"=="" set BUILD_DIR=%~dp0build
if "%KEYPIRINHA_SDK%"=="" (
    echo ERROR: Keypirinha SDK environment not setup.
    echo        Run SDK's "kpenv" script and try again.
    exit /b 1
)

if "%1"=="clean" (
    if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
    goto end
)

if "%1"=="build" (
    if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
    pushd "%~dp0"
    call "%KEYPIRINHA_SDK%\cmd\kparch" ^
        "%BUILD_DIR%\%PACKAGE_NAME%.keypirinha-package" ^
        -r LICENSE* README* src
    popd
    goto end
)

if "%1"=="install" (
    echo Installing %PACKAGE_NAME% to %INSTALL_DIR%
    if not exist "%BUILD_DIR%\%PACKAGE_NAME%.keypirinha-package" (
        echo Package not found. Run "make build" first.
        exit /b 1
    )
    if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
    copy /Y "%BUILD_DIR%\%PACKAGE_NAME%.keypirinha-package" "%INSTALL_DIR%\"
    echo Installed successfully. Restart Keypirinha or reload the catalog.
    goto end
)

if "%1"=="dev" (
    call :build
    if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
    copy /Y "%BUILD_DIR%\%PACKAGE_NAME%.keypirinha-package" "%INSTALL_DIR%\"
    echo Development build installed. Restart Keypirinha or reload the catalog.
    goto end
)

if "%1"=="py" (
    call "%KEYPIRINHA_SDK%\cmd\kpy" %2 %3 %4 %5 %6 %7 %8 %9
    goto end
)

echo Unknown command: %1
goto help

:end
