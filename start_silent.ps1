$ErrorActionPreference = "SilentlyContinue"

Write-Host "Killing old node and python processes..."
Stop-Process -Name "node" -Force
Get-WmiObject Win32_Process -Filter "name='python.exe' and CommandLine like '%bridge_server.py%'" | ForEach-Object { $_.Terminate() }
Get-WmiObject Win32_Process -Filter "name='python.exe' and CommandLine like '%Wake_Word_detection.py%'" | ForEach-Object { $_.Terminate() }
Get-WmiObject Win32_Process -Filter "name='python.exe' and CommandLine like '%background_monitor.py%'" | ForEach-Object { $_.Terminate() }

Start-Sleep -Seconds 2

Write-Host "Starting Bridge Server..."
Start-Process -FilePath "backend\venv\Scripts\python.exe" -ArgumentList "backend\bridge_server.py" -WindowStyle Hidden

Write-Host "Waiting for backend to initialize..."
Start-Sleep -Seconds 3

Write-Host "Starting Wake Word Listener..."
Start-Process -FilePath "backend\venv\Scripts\python.exe" -ArgumentList "backend\core\Wake_Word_detection.py" -WindowStyle Hidden

Write-Host "Starting Background Monitor..."
Start-Process -FilePath "backend\venv\Scripts\python.exe" -ArgumentList "backend\core\background_monitor.py" -WindowStyle Hidden

Write-Host "Starting Frontend Dashboard..."
Start-Process -FilePath "powershell.exe" -ArgumentList "-Command cd frontend; npm run dev" -WindowStyle Hidden

Write-Host "All services started in background!"
