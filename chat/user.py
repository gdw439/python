import sys
import time
import random
import socket
import pymysql
import threading
import PyQt5.QtCore
import PyQt5.QtGui
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

#addr = ('120.78.169.8', 3300)
addr = ('127.0.0.1', 3300)


class Login(QDialog):
    # 登录窗口

    def __init__(self):
        super().__init__()
        self.setFixedSize(420, 240)
        self.setWindowFlags(Qt.FramelessWindowHint)
        palette1 = QPalette()
        palette1.setBrush(self.backgroundRole(), QBrush(QPixmap('login.png')))
        self.setPalette(palette1)

        self.headlab = QLabel(self)
        self.nameldt = QLineEdit(self)
        self.keysldt = QLineEdit(self)
        self.logbtn = QPushButton('登录', self)
        self.regbtn = QPushButton('注册', self)
        self.headlab.setPixmap(QPixmap('logo.png'))

        # 排列控件
        self.headlab.move(130, 50)
        self.logbtn.move(105, 200)
        self.regbtn.move(245, 200)
        self.nameldt.move(105, 120)
        self.keysldt.move(105, 160)
        self.logbtn.setFixedSize(70, 27)
        self.regbtn.setFixedSize(70, 27)
        self.nameldt.setFixedSize(210, 27)
        self.keysldt.setFixedSize(210, 27)

        self.nameldt.setPlaceholderText('你的昵称')
        self.keysldt.setPlaceholderText('你的密码')
        self.keysldt.setEchoMode(QLineEdit.Password)
        self.show()

    # 登录数据检查
    def formatcheck(self):
        name = self.nameldt.text()
        keyword = self.keysldt.text()
        if name == '':
            print('请输入用户名')
            return False
        elif keyword == '':
            print('请输入密码')
            return False
        else:
            return True

    def mousePressEvent(self, event):
        self.last = event.globalPos()

    def mouseMoveEvent(self, event):
        dot = event.globalPos()
        dx = dot.x() - self.last.x()
        dy = dot.y() - self.last.y()
        self.last = dot
        self.move(self.x() + dx, self.y() + dy)

    def mouseReleaseEvent(self, event):
        dot = event.globalPos()
        dx = dot.x() - self.last.x()
        dy = dot.y() - self.last.y()
        self.move(self.x() + dx, self.y() + dy)


class Box(QWidget):
    # 构建窗口
    row = 0
    listnum = {}

    def __init__(self):
        super().__init__()
        self.BoxInit()

    def flushmessage(self):
        word = self.oute.text()
        self.oute.clear()
        # 显示在信息主面板
        self.inte.setAlignment(Qt.AlignRight)
        self.inte.setTextColor(Qt.gray)
        self.inte.insertPlainText(':我\n')
        self.inte.setTextColor(Qt.blue)
        self.inte.insertPlainText(word + ' ' * 4 + '\n')

    def showmessage(self, name, mess):
        # ? 光标问题处理
        self.inte.setAlignment(Qt.AlignLeft)
        self.inte.setTextColor(Qt.gray)
        self.inte.insertPlainText(name + ':\n')
        self.inte.setTextColor(Qt.red)
        self.inte.insertPlainText(' ' * 4 + mess + '\n')

    def flushlist(self, namelist):
        for name in namelist:
            self.listnum[name] = self.row
            self.row += 1
        self.lit.addItems(namelist)

    def addlist(self, name):
        self.lit.addItem(name)
        self.listnum[name] = self.row
        self.row += 1

    def sublist(self, name):
        self.lit.takeItem(self.listnum[name])
        self.listnum.pop(name)
        self.row -= 1

    def BoxInit(self):
        self.resize(500, 300)
        self.setFixedSize(self.width(), self.height())
        self.setWindowTitle('Vortex')

        self.sendbtn = QPushButton()
        self.sendbtn.setText('发送')
        self.lab = QLabel()
        self.lab.setText('在线好友')
        self.lit = QListWidget()
        self.lit.setFixedSize(100, 250)
        self.inte = QTextEdit()
        self.oute = QLineEdit()
        grid = QGridLayout()

        grid.addWidget(self.lab, 0, 0, 1, 1)
        grid.addWidget(self.lit, 1, 0, 9, 1)
        grid.addWidget(self.inte, 1, 1, 8, 2)
        grid.addWidget(self.oute, 9, 1, 1, 1)
        grid.addWidget(self.sendbtn, 9, 2, 1, 1)
        self.setLayout(grid)

        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())


class Chat:
    myname = ''
    user_list = []

    def __init__(self):
        self.box = Box()
        self.login = Login()
        self.login.logbtn.clicked.connect(self.loginemit)
        self.login.regbtn.clicked.connect(self.registeremit)
        self.sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        t = threading.Thread(target=self.hostlink)
        t.start()

    # 连接服务器
    def hostlink(self):
        self.login.logbtn.setDisabled(True)
        self.login.regbtn.setDisabled(True)
        while True:
            try:
                self.sk.connect(addr)
                break
            except:
                time.sleep(1)
                print('再次尝试连接')
        print("已连接服务器")
        self.login.logbtn.setDisabled(False)
        self.login.regbtn.setDisabled(False)

    def hostchat(self):
        while True:
            data = self.sk.recv(1024).decode('utf-8')

            # 删除好友列表
            if data.find('$$DEL:') != -1:
                name = data.split(':')[1]
                self.box.sublist(name)
            # 添加好友列表
            elif data.find('$$ADD:') != -1:
                name = data.split(':')[1]
                self.box.addlist(name)
            # 接收好友信息
            else:
                time.sleep(0.5)
                name = data.split('$')[1]
                mess = data.split('$')[2]
                self.box.showmessage(name, mess)

    # 执行登录命令
    def loginemit(self):
        if self.login.formatcheck():
            name = self.login.nameldt.text()
            keyword = self.login.keysldt.text()
            if self.loginhost(name, keyword) == True:
                print('登录成功')
                self.myname = name
                self.login.close()
                self.box.show()
                self.box.sendbtn.clicked.connect(self.emitmessage)
                self.box.flushlist(self.user_list)
        else:
            print('输入格式错误')

    # 执行注册命令
    def registeremit(self):
        if self.login.formatcheck():
            name = self.login.nameldt.text()
            keyword = self.login.keysldt.text()
            if self.registeruser(name, keyword) == True:
                self.myname = name
                print('登录成功')
        else:
            print('输入格式错误')

    # 执行发送命令
    def emitmessage(self):
        word = self.box.oute.text()
        self.box.flushmessage()
        name = self.box.lit.currentItem().text()
        if name != None:
            data = name + '$' + self.myname + '$' + word
            self.sk.send(data.encode('utf-8'))

    # 登录服务器时发送数据
    def loginhost(self, name, keyword):
        data = '$$INFO,' + name + ',' + keyword + ',' + 'Login'
        self.sk.send(data.encode('utf-8'))
        try:
            data = self.sk.recv(1024).decode('utf-8')
            if data == '$$USERAT':
                print('存在用户冲突')
                return False
            elif data == '$$UNREG':
                print('该用户未注册')
                return False
            elif data == '$$KEYERR':
                print('密码不匹配')
                return False
            elif data == '$$LIST':
                print('正在接收名单')
                while True:
                    data = self.sk.recv(1024).decode('utf-8')
                    if data == '$$END':
                        print('接收完毕')
                        t = threading.Thread(target=self.hostchat)
                        t.start()

                        return True
                        break
                    print(data)
                    self.user_list.append(data)
            else:
                print('无意义数据')
        except:
            print('回应异常')
            return False

    # 注册时发送给服务器
    def registeruser(self, name, keyword):
        data = '$$INFO,' + name + ',' + keyword + ',' + 'Regis'
        self.sk.send(data.encode('utf-8'))
        try:
            data = self.sk.recv(1024).decode('utf-8')
            if data == '$$USERAT':
                print('注册失败')
                return False

            elif data == '$$LIST':
                print('正在接收名单')
                while True:
                    data = self.sk.recv(1024).decode('utf-8')
                    if data == '$$END':
                        print('接收完毕')
                        return True
                        break
                    print(data)
                    self.user_list.append(data)
        except:
            print('等待回应异常')
            return False

# 主函数
if __name__ == '__main__':
    app = QApplication(sys.argv)
    m = Chat()
    sys.exit(app.exec_())
