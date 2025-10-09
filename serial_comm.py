import serial
import serial.tools.list_ports
import time
from threading import Thread, Event

class SerialComm:
    def __init__(self):
        self.serial_port = None
        self.is_open = False
        self.read_thread = None
        self.stop_event = Event()
        self.callback = None
        
    def get_ports(self):
        """获取所有可用的串口列表"""
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(port.device)
        return ports
    
    def open_port(self, port, baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=1):
        """打开串口"""
        try:
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
            self.start_read_thread()
            return True, "串口打开成功"
        except Exception as e:
            return False, f"串口打开失败: {str(e)}"
    
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
    
    def _read_data(self):
        """读取数据的线程函数"""
        while not self.stop_event.is_set() and self.is_open:
            try:
                if self.serial_port.in_waiting:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    if data and self.callback:
                        self.callback(data)
            except Exception as e:
                print(f"读取数据错误: {str(e)}")
            time.sleep(0.01)  # 短暂休眠，减少CPU占用
    
    def set_callback(self, callback):
        """设置数据接收回调函数"""
        self.callback = callback