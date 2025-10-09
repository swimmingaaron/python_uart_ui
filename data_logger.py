import os
import time
import csv
import json
from datetime import datetime

class DataLogger:
    def __init__(self, log_dir='logs'):
        self.log_dir = log_dir
        # 确保日志目录存在
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    def log_data(self, data, data_type='raw'):
        """记录数据到文件"""
        timestamp = datetime.now()
        date_str = timestamp.strftime('%Y-%m-%d')
        time_str = timestamp.strftime('%H-%M-%S')
        
        # 创建日期目录
        date_dir = os.path.join(self.log_dir, date_str)
        if not os.path.exists(date_dir):
            os.makedirs(date_dir)
        
        # 根据数据类型选择不同的记录方式
        if data_type == 'raw':
            # 二进制数据直接保存
            filename = f"{time_str}_raw.bin"
            file_path = os.path.join(date_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(data)
        elif data_type == 'text':
            # 文本数据保存为txt
            filename = f"{time_str}_text.txt"
            file_path = os.path.join(date_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(data)
        elif data_type == 'hex':
            # 十六进制数据保存为txt
            filename = f"{time_str}_hex.txt"
            file_path = os.path.join(date_dir, filename)
            with open(file_path, 'w') as f:
                f.write(data)
        
        return file_path
    
    def start_session_log(self, port_info):
        """开始一个新的会话日志"""
        timestamp = datetime.now()
        date_str = timestamp.strftime('%Y-%m-%d')
        time_str = timestamp.strftime('%H-%M-%S')
        
        # 创建日期目录
        date_dir = os.path.join(self.log_dir, date_str)
        if not os.path.exists(date_dir):
            os.makedirs(date_dir)
        
        # 创建会话目录
        session_dir = os.path.join(date_dir, f"session_{time_str}")
        os.makedirs(session_dir)
        
        # 记录会话信息
        session_info = {
            'start_time': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'port_info': port_info
        }
        
        with open(os.path.join(session_dir, 'session_info.json'), 'w') as f:
            json.dump(session_info, f, indent=4)
        
        return session_dir
    
    def log_to_csv(self, session_dir, data_dict):
        """记录数据到CSV文件"""
        csv_path = os.path.join(session_dir, 'data_log.csv')
        
        # 检查文件是否存在，不存在则创建并写入表头
        file_exists = os.path.isfile(csv_path)
        
        with open(csv_path, 'a', newline='') as f:
            fieldnames = ['timestamp'] + list(data_dict.keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            # 添加时间戳
            data_dict['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            writer.writerow(data_dict)
        
        return csv_path