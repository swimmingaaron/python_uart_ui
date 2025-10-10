# 1. 首先添加datetime模块的导入
import serial
import serial.tools.list_ports
import time
from datetime import datetime  # 添加datetime导入
from threading import Thread, Event
from PyQt5.QtCore import QObject, pyqtSignal

class SerialComm(QObject):
    # 创建数据接收信号
    data_received = pyqtSignal(bytes)
    
    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.is_open = False
        self.read_thread = None
        self.stop_event = Event()
        self.callback = None
        self.read_timeout = 1.0  # 读超时默认1000ms
        self.packet_timeout = 0.01  # 分包超时默认10ms
        self.last_receive_time = 0  # 上次接收数据的时间
        self.current_packet = b''  # 当前正在接收的数据包
        self.show_timestamp = False  # 新增：时间戳选项，默认为False
    
    # 添加设置时间戳选项的方法
    def set_timestamp_enabled(self, enabled):
        """设置是否启用时间戳显示"""
        self.show_timestamp = enabled
    
    # 辅助方法：生成当前时间戳字符串
    def _get_current_timestamp(self):
        """获取当前时间戳字符串"""
        return datetime.now().strftime("[%Y-%m-%d %H:%M:%S.%f]")[:-3]
    
    # 修改open_port方法，重置数据包
    def open_port(self, port, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=1):
        """打开串口"""
        try:
            self.read_timeout = timeout  # 设置读超时
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=bytesize,
                parity=parity,
                stopbits=stopbits,
                timeout=timeout
            )
            self.is_open = True
            self.stop_event.clear()
            # 重置数据包相关变量
            self.current_packet = b''
            self.last_receive_time = 0
            self.start_read_thread()
            return True, "串口打开成功"
        except Exception as e:
            return False, f"串口打开失败: {str(e)}"
    
    # 修改_read_data方法，添加时间戳功能
    def _read_data(self):
        """读取数据的线程函数（轮询方式）"""
        print("数据读取线程已启动")
        while not self.stop_event.is_set() and self.is_open:
            try:
                current_time = time.time()
                
                # 检查串口是否有数据可读
                if self.serial_port.in_waiting > 0:
                    # 读取所有可用数据
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    
                    # 检查是否需要开始一个新包（基于分包超时）
                    if self.last_receive_time > 0 and \
                       current_time - self.last_receive_time > self.packet_timeout and \
                       self.current_packet:  # 如果当前已有累积的数据包
                        # 生成时间戳前缀
                        timestamp_prefix = f"{self._get_current_timestamp()} " if self.show_timestamp else ""
                        # 处理之前累积的完整数据包
                        print(f"{timestamp_prefix}接收到数据: {len(self.current_packet)}字节 - {self.current_packet.hex() if len(self.current_packet) < 20 else self.current_packet.hex()[:40]+'...'}")
                        # 发射信号时保持原始数据不变，UI层可以根据需要添加时间戳
                        self.data_received.emit(self.current_packet)
                        if self.callback:
                            try:
                                self.callback(self.current_packet)
                            except Exception as callback_error:
                                print(f"回调函数执行错误: {str(callback_error)}")
                        # 开始新的数据包
                        self.current_packet = data
                    else:
                        # 追加到当前数据包
                        self.current_packet += data
                    
                    # 更新最后接收时间
                    self.last_receive_time = current_time
                # 修复serial_comm.py中的语法和缩进错误
                
                # 修复elif分支内的代码结构（大约第90-120行）：
                # 检查当前数据包是否已超过分包超时
                elif self.current_packet and \
                     self.last_receive_time > 0 and \
                     current_time - self.last_receive_time > self.packet_timeout:
                    # 生成时间戳前缀
                    timestamp_prefix = f"{self._get_current_timestamp()} " if self.show_timestamp else ""
                    # 处理超时的完整数据包
                    print(f"{timestamp_prefix}接收到数据: {len(self.current_packet)}字节 - {self.current_packet.hex() if len(self.current_packet) < 20 else self.current_packet.hex()[:40]+'...'}")
                    
                    # 正常的数据处理逻辑
                    self.data_received.emit(self.current_packet)
                    if self.callback:
                        try:
                            self.callback(self.current_packet)
                        except Exception as callback_error:
                            print(f"回调函数执行错误: {str(callback_error)}")
                    # 清空当前数据包
                    self.current_packet = b''
                
            except Exception as e:
                print(f"读取数据错误: {str(e)}")
                # 检查串口是否仍然打开
                if not self.serial_port.is_open:
                    print("串口已关闭，退出读取线程")
                    self.is_open = False
                    break
                
            # 短暂休眠，减少CPU占用
            time.sleep(0.001)  # 1ms休眠，比之前更频繁地检查
        
        print("数据读取线程已退出")
    
    # 添加设置超时参数的方法
    def set_timeouts(self, read_timeout, packet_timeout):
        """设置读超时和分包超时参数"""
        self.read_timeout = read_timeout
        self.packet_timeout = packet_timeout
        # 如果串口已打开，更新其超时设置
        if self.serial_port and self.is_open:
            self.serial_port.timeout = read_timeout
    
    def get_ports(self):
        """获取所有可用的串口列表"""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(port.device)
        return ports
    
    def close_port(self):
        """关闭串口"""
        if self.is_open and self.serial_port:
            self.stop_event.set()
            if self.read_thread:
                self.read_thread.join(timeout=1.0)
            self.serial_port.close()
            self.is_open = False
            return True, "串口关闭成功"
        return False, "串口未打开"
    
    def send_data(self, data, is_hex=False):
        """发送数据"""
        if not self.is_open or not self.serial_port:
            return False, "串口未打开"
        
        try:
            if is_hex:
                # 将十六进制字符串转换为字节
                hex_data = data.replace(" ", "")
                bytes_data = bytes.fromhex(hex_data)
            else:
                # 将字符串转换为字节
                bytes_data = data.encode('utf-8')
                
            self.serial_port.write(bytes_data)
            return True, f"发送成功: {len(bytes_data)}字节"
        except Exception as e:
            return False, f"发送失败: {str(e)}"
    
    def start_read_thread(self):
        """启动读取线程"""
        self.read_thread = Thread(target=self._read_data)
        self.read_thread.daemon = True
        self.read_thread.start()
    
    def set_callback(self, callback):
        """设置数据接收回调函数（保持向后兼容）"""
        self.callback = callback