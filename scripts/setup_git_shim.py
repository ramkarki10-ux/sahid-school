import os

shim_path = r'C:\Users\lenovo\AppData\Local\GitHubDesktop\bin\git.bat'
content = '@echo off\r\n"%~dp0\\..\\app-3.6.7\\resources\\app\\git\\cmd\\git.exe" %*\r\n'

with open(shim_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("git.bat shim created at", shim_path)

