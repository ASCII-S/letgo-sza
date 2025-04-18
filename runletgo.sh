#/bin/bash
# 使用 nohup 后台运行并将输出写入日志文件
nohup python3.8 letgo_wrapper.py > letgo_output.log 2>&1 &
echo "Script is running in the background. Logs are in letgo_output.log"
tail -f letgo_output.log