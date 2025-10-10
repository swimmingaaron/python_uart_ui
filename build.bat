@echo off
echo 正在安装必要的依赖...
::pip install -i https://mirrors.aliyun.com/pypi/simple pyserial pyqt5 pyinstaller

echo 修改build.spec文件，移除图标引用...
powershell -Command "(Get-Content build.spec) -replace \"icon='icon.ico',\", \"\" | Set-Content build.spec"

echo 正在使用PyInstaller打包应用...
pyinstaller build.spec

echo 打包完成！可执行文件位于dist文件夹中。
pause