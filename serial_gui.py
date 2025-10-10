# 修复serial_gui.py文件，清理混乱的代码结构和注释
import sys
import time
import binascii
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QComboBox, QPushButton, QTextEdit, QLineEdit, QGroupBox,
                            QCheckBox, QGridLayout, QFileDialog, QMessageBox, QSpinBox,
                            QAction, QMenu, QTabWidget)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QIcon
from serial_comm import SerialComm
from data_logger import DataLogger

class SerialGUI(QMainWindow):
    # 在__init__方法中添加初始化
    def __init__(self):
        super().__init__()
        self.serial_comm = SerialComm()
        self.data_logger = DataLogger()
        self.init_ui()
        self.setup_connections()
        self.refresh_ports()
        self.received_data = b''
        self.current_data_timestamp = None
        self.logging_enabled = False
        self.current_session_dir = None
        self.last_receive_time = 0
        self.scroll_locked = False  # 初始化滚动锁定状态为未锁定
        
        # 添加这个新的数据结构初始化
        self.received_data_with_timestamp = []
        
        # 定时刷新串口列表
        self.port_timer = QTimer()
        self.port_timer.timeout.connect(self.refresh_ports)
        self.port_timer.start(3000)  # 每3秒刷新一次
        
    def init_ui(self):
        """初始化UI界面"""
        self.setWindowTitle('串口通信工具')
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 顶部控制区域
        control_layout = QHBoxLayout()
        
        # 串口设置组
        port_group = QGroupBox('串口设置')
        port_layout = QGridLayout()
        
        # 串口选择
        port_layout.addWidget(QLabel('串口:'), 0, 0)
        self.port_combo = QComboBox()
        port_layout.addWidget(self.port_combo, 0, 1)
        
        # 波特率选择
        port_layout.addWidget(QLabel('波特率:'), 1, 0)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(['9600', '19200', '38400', '57600', '115200'])
        port_layout.addWidget(self.baud_combo, 1, 1)
        
        # 数据位选择
        port_layout.addWidget(QLabel('数据位:'), 2, 0)
        self.data_bits_combo = QComboBox()
        self.data_bits_combo.addItems(['5', '6', '7', '8'])
        self.data_bits_combo.setCurrentIndex(3)  # 默认8位
        port_layout.addWidget(self.data_bits_combo, 2, 1)
        
        # 校验位选择
        port_layout.addWidget(QLabel('校验位:'), 3, 0)
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(['无 (N)', '奇校验 (O)', '偶校验 (E)', '标记 (M)', '空格 (S)'])
        port_layout.addWidget(self.parity_combo, 3, 1)
        
        # 停止位选择
        port_layout.addWidget(QLabel('停止位:'), 4, 0)
        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.addItems(['1', '1.5', '2'])
        port_layout.addWidget(self.stop_bits_combo, 4, 1)
        
        # 刷新和打开按钮
        self.refresh_btn = QPushButton('刷新')
        port_layout.addWidget(self.refresh_btn, 5, 0)
        self.open_btn = QPushButton('打开串口')
        port_layout.addWidget(self.open_btn, 5, 1)
        
        port_group.setLayout(port_layout)
        control_layout.addWidget(port_group)
        
        # 发送设置组
        send_group = QGroupBox('发送设置')
        send_layout = QVBoxLayout()
        
        # 发送区域
        self.send_text = QTextEdit()
        self.send_text.setPlaceholderText('在此输入要发送的数据...')
        send_layout.addWidget(self.send_text)
        
        # 发送选项
        send_options = QHBoxLayout()
        
        self.hex_send_check = QCheckBox('HEX发送')
        send_options.addWidget(self.hex_send_check)
        
        self.auto_send_check = QCheckBox('自动发送')
        send_options.addWidget(self.auto_send_check)
        
        send_options.addWidget(QLabel('间隔(ms):'))
        self.send_interval = QSpinBox()
        self.send_interval.setRange(10, 10000)
        self.send_interval.setValue(1000)
        send_options.addWidget(self.send_interval)
        
        self.send_btn = QPushButton('发送')
        send_options.addWidget(self.send_btn)
        send_layout.addLayout(send_options)
        send_group.setLayout(send_layout)
        control_layout.addWidget(send_group)
        
        main_layout.addLayout(control_layout)
        
        # 接收区域
        receive_group = QGroupBox('接收数据')
        receive_layout = QVBoxLayout()
        
        self.receive_text = QTextEdit()
        self.receive_text.setReadOnly(True)
        self.receive_text.setLineWrapMode(QTextEdit.WidgetWidth)  # 自动换行到窗口宽度
        receive_layout.addWidget(self.receive_text)
        
        # 接收选项
        receive_options = QHBoxLayout()
        
        self.hex_display_check = QCheckBox('HEX显示')
        receive_options.addWidget(self.hex_display_check)
        
        self.auto_line_check = QCheckBox('自动换行')
        receive_options.addWidget(self.auto_line_check)
        
        # 添加时间戳复选框
        self.show_timestamp_check = QCheckBox('显示时间戳')
        receive_options.addWidget(self.show_timestamp_check)
        
        # 添加滚动控制按钮
        self.scroll_to_bottom_btn = QPushButton('滚动到底部')
        receive_options.addWidget(self.scroll_to_bottom_btn)
        
        self.lock_scroll_check = QCheckBox('固定滚动')
        receive_options.addWidget(self.lock_scroll_check)
        
        # 读超时设置
        receive_options.addWidget(QLabel('读超时(ms):'))
        self.read_timeout_spin = QSpinBox()
        self.read_timeout_spin.setRange(1, 10000)
        self.read_timeout_spin.setValue(1000)  # 默认1000ms
        receive_options.addWidget(self.read_timeout_spin)
        
        # 分包超时设置
        receive_options.addWidget(QLabel('分包超时(ms):'))
        self.packet_timeout_spin = QSpinBox()
        self.packet_timeout_spin.setRange(1, 1000)
        self.packet_timeout_spin.setValue(10)  # 默认10ms
        receive_options.addWidget(self.packet_timeout_spin)
        
        # 应用超时设置按钮
        self.apply_timeout_btn = QPushButton('应用超时设置')
        receive_options.addWidget(self.apply_timeout_btn)
        
        # 清空和保存按钮
        self.clear_btn = QPushButton('清空')
        receive_options.addWidget(self.clear_btn)
        
        self.save_btn = QPushButton('保存')
        receive_options.addWidget(self.save_btn)
        
        receive_layout.addLayout(receive_options)
        receive_group.setLayout(receive_layout)
        main_layout.addWidget(receive_group)
        
        # 状态栏
        self.statusBar().showMessage('就绪')
        
        # 自动发送定时器
        self.auto_timer = QTimer()
        self.auto_timer.timeout.connect(self.send_data)
        
    # 在setup_connections方法中添加滚动控制按钮的信号连接
    def setup_connections(self):
        """设置信号连接"""
        self.refresh_btn.clicked.connect(self.refresh_ports)
        self.open_btn.clicked.connect(self.toggle_port)
        self.send_btn.clicked.connect(self.send_data)
        self.clear_btn.clicked.connect(self.clear_receive)
        self.save_btn.clicked.connect(self.save_receive)
        self.auto_send_check.stateChanged.connect(self.toggle_auto_send)
        self.hex_display_check.stateChanged.connect(self.update_receive_display)
        self.auto_line_check.stateChanged.connect(self.update_line_wrap_mode)
        self.show_timestamp_check.stateChanged.connect(self.toggle_timestamp)
        # 添加超时设置应用按钮的信号连接
        self.apply_timeout_btn.clicked.connect(self.apply_timeout_settings)
        # 添加滚动控制按钮的信号连接
        self.scroll_to_bottom_btn.clicked.connect(self.scroll_to_bottom)
        self.lock_scroll_check.stateChanged.connect(self.toggle_scroll_lock)
        # 设置串口数据接收信号连接
        self.serial_comm.data_received.connect(self.on_data_received)
    
    def update_line_wrap_mode(self):
        """根据自动换行设置更新文本编辑器的换行模式"""
        if self.auto_line_check.isChecked():
            # 启用自动换行，换行到窗口宽度
            self.receive_text.setLineWrapMode(QTextEdit.WidgetWidth)
        else:
            # 禁用自动换行
            self.receive_text.setLineWrapMode(QTextEdit.NoWrap)
    
    def refresh_ports(self):
        """刷新可用串口列表"""
        current_port = self.port_combo.currentText()
        self.port_combo.clear()
        
        ports = self.serial_comm.get_ports()
        if ports:
            self.port_combo.addItems(ports)
            # 尝试恢复之前选择的串口
            index = self.port_combo.findText(current_port)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)
        
    def toggle_port(self):
        """打开或关闭串口"""
        if not self.serial_comm.is_open:
            # 获取串口参数
            port = self.port_combo.currentText()
            if not port:
                QMessageBox.warning(self, '警告', '请选择串口')
                return
                
            baudrate = int(self.baud_combo.currentText())
            bytesize = int(self.data_bits_combo.currentText())
            
            parity_map = {'无 (N)': 'N', '奇校验 (O)': 'O', '偶校验 (E)': 'E', 
                         '标记 (M)': 'M', '空格 (S)': 'S'}
            parity = parity_map[self.parity_combo.currentText()]
            
            stopbits_map = {'1': 1, '1.5': 1.5, '2': 2}
            stopbits = stopbits_map[self.stop_bits_combo.currentText()]
            
            # 打开串口
            success, msg = self.serial_comm.open_port(
                port=port, 
                baudrate=baudrate, 
                bytesize=bytesize, 
                parity=parity, 
                stopbits=stopbits
            )
            
            if success:
                self.open_btn.setText('关闭串口')
                self.statusBar().showMessage(f'串口已打开: {port}')
                # 禁用串口设置控件
                self.port_combo.setEnabled(False)
                self.baud_combo.setEnabled(False)
                self.data_bits_combo.setEnabled(False)
                self.parity_combo.setEnabled(False)
                self.stop_bits_combo.setEnabled(False)
            else:
                QMessageBox.critical(self, '错误', msg)
        else:
            # 关闭串口
            success, msg = self.serial_comm.close_port()
            if success:
                self.open_btn.setText('打开串口')
                self.statusBar().showMessage('串口已关闭')
                # 启用串口设置控件
                self.port_combo.setEnabled(True)
                self.baud_combo.setEnabled(True)
                self.data_bits_combo.setEnabled(True)
                self.parity_combo.setEnabled(True)
                self.stop_bits_combo.setEnabled(True)
                # 停止自动发送
                if self.auto_timer.isActive():
                    self.auto_timer.stop()
                    self.auto_send_check.setChecked(False)
            else:
                QMessageBox.critical(self, '错误', msg)
    
    def send_data(self):
        """发送数据"""
        if not self.serial_comm.is_open:
            QMessageBox.warning(self, '警告', '请先打开串口')
            return
            
        data = self.send_text.toPlainText()
        if not data:
            return
            
        is_hex = self.hex_send_check.isChecked()
        
        # 如果是十六进制发送，检查格式
        if is_hex:
            try:
                # 移除所有空格
                hex_data = data.replace(" ", "")
                # 检查是否为有效的十六进制字符串
                int(hex_data, 16)
            except ValueError:
                QMessageBox.warning(self, '警告', '无效的十六进制格式')
                return
        
        success, msg = self.serial_comm.send_data(data, is_hex)
        self.statusBar().showMessage(msg)
    
    # 修复on_data_received方法的异常处理
    def on_data_received(self, data):
        """接收到数据的回调函数"""
        try:
            # 获取当前时间（毫秒）
            current_time = time.time() * 1000
            current_timestamp = datetime.now()  # 获取当前数据块的时间戳
            
            # 将时间间隔阈值从10ms减小到5ms，确保相关数据块连续显示在同一行
            if self.last_receive_time > 0 and current_time - self.last_receive_time > 5:
                # 这里我们将不再修改received_data，而是在数据块之间添加分隔符
                # 在数据列表中添加一个特殊标记表示换行
                self.received_data_with_timestamp.append(("NEWLINE", None))
            
            # 更新上次接收时间
            self.last_receive_time = current_time
            
            # 将数据和对应时间戳一起保存
            self.received_data_with_timestamp.append((data, current_timestamp))
            
            # 更新显示
            self.update_receive_display()
        except Exception as e:
            # 捕获所有异常，防止程序崩溃
            print(f"数据接收处理出错: {e}")
    
    # 1. 修复update_receive_display方法，移除对scroll_locked的引用，优化滚动处理
    def update_receive_display(self):
        """更新接收显示区域"""
        if not self.received_data_with_timestamp:
            self.receive_text.clear()
            return
            
        # 保存当前滚动条位置
        scrollbar = self.receive_text.verticalScrollBar()
        scroll_pos = scrollbar.value()
        max_scroll_pos = scrollbar.maximum()
        
        # 使用更宽松的底部判断条件，避免严格相等导致的滚动问题
        at_bottom = scroll_pos >= max_scroll_pos - 10 or max_scroll_pos == 0
        
        # 清空显示
        self.receive_text.clear()
        
        # 直接设置自动换行模式
        if self.auto_line_check.isChecked():
            self.receive_text.setLineWrapMode(QTextEdit.WidgetWidth)
        else:
            self.receive_text.setLineWrapMode(QTextEdit.NoWrap)
        
        display_text = ""
        
        # 遍历所有带时间戳的数据块
        for item in self.received_data_with_timestamp:
            if item[0] == "NEWLINE":
                display_text += "\n"
                continue
                
            data, timestamp = item
            chunk_text = ""
            
            # 根据显示模式处理数据
            if self.hex_display_check.isChecked():
                try:
                    # 转换为十六进制并格式化
                    hex_str = binascii.hexlify(data).decode('ascii')
                    formatted_hex = ' '.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)])
                    chunk_text = formatted_hex
                except Exception:
                    chunk_text = str(data)
            else:
                try:
                    chunk_text = data.decode('utf-8', errors='replace')
                except Exception:
                    chunk_text = str(data)
            
            # 添加时间戳（如果启用）
            if self.show_timestamp_check.isChecked() and timestamp:
                time_str = timestamp.strftime('[%Y-%m-%d %H:%M:%S.%f]')
                display_text += f"{time_str} {chunk_text}"
            else:
                display_text += chunk_text
        
        # 确保换行符格式正确
        display_text = display_text.replace('\r\n', '\n')
        display_text = display_text.replace('\r', '\n')
        
        # 使用信号阻塞减少刷新，避免抖动
        self.receive_text.blockSignals(True)
        
        # 显示文本
        self.receive_text.setPlainText(display_text)
        
        # 重新启用信号
        self.receive_text.blockSignals(False)
        
        # 只有之前在底部时才滚动到底部
        if at_bottom:
            # 异步滚动到底部，避免阻塞UI线程
            QTimer.singleShot(0, self.scroll_to_bottom)

# 2. 修复scroll_to_bottom方法，移除对不存在组件的引用
    def scroll_to_bottom(self):
        """滚动到底部"""
        # 分步骤确保可靠滚动到底部
        # 1. 移动光标到文本末尾
        self.receive_text.moveCursor(QTextCursor.End)
        
        # 2. 处理滚动条确保可见性
        scrollbar = self.receive_text.verticalScrollBar()
        
        # 使用定时器异步设置滚动条位置，确保UI已更新完成
        def set_scrollbar():
            scrollbar.setValue(scrollbar.maximum())
        
        QTimer.singleShot(0, set_scrollbar)

# 3. 删除toggle_scroll_lock方法（整个方法）

# 4. 确保clear_receive方法正确（修复重复clear的问题）
    def clear_receive(self):
        """清空接收区域"""
        self.received_data = b''
        self.current_data_timestamp = None  # 重置时间戳
        self.receive_text.clear()
        self.data_packets = []  # 清空数据包包列表
        self.receive_text.clear()
    
    def save_receive(self):
        """保存接收数据到文件"""
        if not self.received_data:
            QMessageBox.information(self, '提示', '没有数据可保存')
            return
            
        filename, _ = QFileDialog.getSaveFileName(
            self, '保存数据', '', 
            '文本文件 (*.txt);;十六进制文件 (*.hex);;二进制文件 (*.bin);;所有文件 (*.*)'
        )
        
        if not filename:
            return
            
        try:
            if filename.endswith('.hex'):
                # 保存为十六进制文本
                hex_str = binascii.hexlify(self.received_data).decode('ascii')
                formatted_hex = ' '.join([hex_str[i:i+2] for i in range(0, len(hex_str), 2)])
                with open(filename, 'w') as f:
                    f.write(formatted_hex)
            elif filename.endswith('.txt'):
                # 保存为文本
                try:
                    text = self.received_data.decode('utf-8', errors='replace')
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(text)
                except Exception:
                    with open(filename, 'wb') as f:
                        f.write(self.received_data)
            else:
                # 保存为二进制
                with open(filename, 'wb') as f:
                    f.write(self.received_data)
                    
            QMessageBox.information(self, '成功', f'数据已保存到 {filename}')
        except Exception as e:
            QMessageBox.critical(self, '错误', f'保存失败: {str(e)}')
    
    def toggle_auto_send(self, state):
        """切换自动发送状态"""
        if state == Qt.Checked:
            if not self.serial_comm.is_open:
                QMessageBox.warning(self, '警告', '请先打开串口')
                self.auto_send_check.setChecked(False)
                return
                
            interval = self.send_interval.value()
            self.auto_timer.start(interval)
        else:
            if self.auto_timer.isActive():
                self.auto_timer.stop()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.serial_comm.is_open:
            self.serial_comm.close_port()
        event.accept()

    def apply_timeout_settings(self):
        """应用超时设置"""
        read_timeout = self.read_timeout_spin.value() / 1000.0  # 转换为秒
        packet_timeout = self.packet_timeout_spin.value() / 1000.0  # 转换为秒
        
        # 设置串口通信对象的超时参数
        self.serial_comm.set_timeouts(read_timeout, packet_timeout)
        
        # 更新状态栏提示
        self.statusBar().showMessage(f'已应用超时设置: 读超时={read_timeout}s, 分包超时={packet_timeout}s')

    # 其他方法保持不变...
    
    # 在apply_timeout_settings方法后添加toggle_timestamp方法
    def toggle_timestamp(self, state):
        """切换时间戳显示状态"""
        enabled = state == Qt.Checked
        self.serial_comm.set_timestamp_enabled(enabled)
        self.statusBar().showMessage(f'时间戳显示已{"启用" if enabled else "禁用"}')

    # 添加这个方法到SerialGUI类中
    # 增强scroll_to_bottom方法，确保滚动效果可靠
    def scroll_to_bottom(self):
        """滚动到底部"""
        self.receive_text.moveCursor(QTextCursor.End)
        # 额外步骤确保垂直滚动条也滚动到底部
        scrollbar = self.receive_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        # 解锁滚动锁定，确保能自由滚动
        self.lock_scroll_check.setChecked(False)
    
    # 修复toggle_scroll_lock方法，移除内部的信号连接代码
    def toggle_scroll_lock(self, state):
        """切换滚动锁定状态"""
        self.scroll_locked = state == Qt.Checked
        # 如果启用了滚动锁定，立即滚动到底部
        if self.scroll_locked:
            self.scroll_to_bottom()