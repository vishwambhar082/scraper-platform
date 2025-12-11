@echo off
REM Convenience launcher for the AlfaBeta pipeline on Windows.
REM Usage: double-click or run `run_alfabeta.bat [run_type] [environment]`
REM Defaults: FULL_REFRESH prod

setlocal

REM Move to repo root (directory of this script)
pushd %~dp0

set RUN_TYPE=%1
if "%RUN_TYPE%"=="" set RUN_TYPE=FULL_REFRESH

set ENVIRONMENT=%2
if "%ENVIRONMENT%"=="" set ENVIRONMENT=prod

echo Running AlfaBeta pipeline with run_type=%RUN_TYPE% env=%ENVIRONMENT%...

REM If you use a virtualenv, activate it here by uncommenting:
REM call .venv\Scripts\activate.bat

python -m src.entrypoints.run_pipeline ^
  --source alfabeta ^
  --run-type %RUN_TYPE% ^
  --environment %ENVIRONMENT%

set EXITCODE=%ERRORLEVEL%
popd

if %EXITCODE% neq 0 (
  echo Pipeline finished with errors (exit code %EXITCODE%).
) else (
  echo Pipeline completed successfully.
)

exit /b %EXITCODE%

