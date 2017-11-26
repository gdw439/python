'''
author: ywxk
target: realize the features of chat
2017.11.14
'''
import sys
import time
import socket
import pymysql
import threading
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

addr = ("127.0.0.1", 3300)


class Link:
    # 初始化TCP
    onlines = 0
    usersname = []  # 在线好友名字
    userssock = {}  # 在线好友地址

    def __init__(self, addr, db):
        self.db = db
        self.sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sk.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)   # 地址复用
        self.sk.bind(addr)
        self.sk.listen(1000)
        self.isrun = True       # 线程控制
        t = threading.Thread(target=self.LoopListen)
        t.start()

    # 线程监听
    def LoopListen(self):
        print('正在监听……')

        while self.isrun:
            sock, addr = self.sk.accept()
            t = threading.Thread(target=self.line, args=(sock, addr))
            t.start()

    # 处理子线程
    def line(self, sock, addr):
        while self.isrun:
            try:
                data = sock.recv(1024).decode('utf-8')
                # 判断是否下线
                if data == '$$END$$':
                    self.offline()
                    break

                # 添加用户信息
                elif data.find('$$INFO') != -1:
                    print('终端发来用户信息')
                    self.dealinfo(data, sock)
                # 转发消息
                else:
                    dataitem = data.split('$')
                    name1 = dataitem[0]
                    name2 = dataitem[1]
                    mess = dataitem[2]
                    print(name2 + '发给' + name1 + ':' + mess)
                    self.userssock[name1].send(data.encode('utf-8'))
            except:
                print('交换信息故障')
                self.offline()
                break

    def dealinfo(self, data, sock):
        info = data.split(',')
        name = info[1]
        keyword = info[2]
        aim = info[3]

        if aim == 'Login':
            if name in self.usersname:
                sock.send('$$USERAT'.encode('utf-8'))
                print('存在用户冲突')
                return False

            if name not in self.db.namekey:
                sock.send('$$UNREG'.encode('utf-8'))
                print('该用户未注册')
                return False

            if keyword != self.db.namekey[name]:
                sock.send('$$KEYERR'.encode('utf-8'))
                print('密码不匹配')
                return False
        elif aim == 'Regis':
            if name in self.db.namekey:
                sock.send('$$USERAT'.encode('utf-8'))
                print('该昵称已存在')
            else:
                userdata = (1, name, keyword, 'None')
                print('数据库写入……')
                self.db.insert_datarow(tuple(userdata))
                print('数据库写入成功')

        # 上线处理
        self.online(name, sock)
        return True

    # 下线处理
    def offline(self):
        if self.onlines != 0:
            self.onlines -= 1
            name = self.usersname.pop()
            print('%s已下线' % name)
            self.userssock.pop(name)  # 更新列表

            # 通知删除
            data = '$$DEL:' + name
            for user in self.usersname:
                self.userssock[user].send(data.encode('utf-8'))

    # 上线处理
    def online(self, name, sock):
        self.onlines += 1

        data = '$$ADD:' + name          # 通知添加列表
        for user in self.usersname:
            self.userssock[user].send(data.encode('utf-8'))
        print(name + '已上线')
        self.namelist_send(sock)
        self.usersname.append(name)
        self.userssock[name] = sock

    # 发送列表
    def namelist_send(self, sock):
        print('递送在线名单')
        sock.send('$$LIST'.encode('utf-8'))
        for item in self.usersname:
            print('正在发送：' + item)
            sock.send(str(item).encode('utf-8'))
            time.sleep(0.01)
        sock.send('$$END'.encode('utf-8'))

# 数据库连接


class Database:
    namekey = {}
    # 连接数据库

    def __init__(self):
        self.db = pymysql.connect(host='127.0.0.1', port=3306,
                                  user='root', passwd='ywxkgdw', db='chat')
        self.cursor = self.db.cursor()
        self.regrenew()

    def get_table_data(self):
        self.cursor.execute('SELECT * FROM users')
        results = self.cursor.fetchall()
        self.db.commit()
        self.cursor.execute('use chat')
        return results

    def insert_datarow(self, datalist):
        sql = 'insert into users values(1,"%s","%s","%s")'
        self.cursor.execute(sql % datalist)
        self.db.commit()
        slef.namekey.append(datalist[0])

    def regrenew(self):
        listdata = self.get_table_data()

        for data in listdata:
            self.namekey[data[1]] = data[2]
        return self.namekey


# 构建窗口
class Box(QWidget):

    def __init__(self):
        super().__init__()
        self.BoxInit()

    # 初始化窗口
    def BoxInit(self):

        self.resize(700, 500)
        self.setFixedSize(self.width(), self.height())
        self.setWindowTitle('Vortex Host')

        # 设置表格
        grid = QGridLayout()
        self.delbtn = QPushButton('删除')
        self.fixbtn = QPushButton('修改')

        self.listview = QTableWidget(0, 4)
        self.listview.setHorizontalHeaderLabels(
            ['ID', 'Name', 'KeyWord', 'IP'])
        self.listview.horizontalHeader().setStretchLastSection(True)         # 自适应窗口
        grid.addWidget(self.listview, 0, 0, 1, 2)
        grid.addWidget(self.delbtn, 1, 0)
        grid.addWidget(self.fixbtn, 1, 1)

        self.setLayout(grid)

        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        self.show()

    # 更新在线列表
    def listview_init(self, listdata):
        self.listrow = 0

        for row in listdata:
            self.listview.setRowCount(self.listrow + 1)
            for item in range(4):
                newItem = QTableWidgetItem(str(row[item]))
                self.listview.setItem(self.listrow, item, newItem)

            self.listrow += 1

    # 添加一行显示
    def add_datarow(self, listdata):

        self.listview.setRowCount(self.listrow + 1)
        for item in range(4):
            newItem = QTableWidgetItem(str(listdata[item]))
            self.listview.setItem(self.listcol, item, newItem)

        self.listrow += 1

    # 删除一行显示
    def sub_datarow(self, listdata):
        pass


# 主函数
if __name__ == '__main__':

    app = QApplication(sys.argv)
    ex = Box()
    dbdata = Database()
    link = Link(addr, dbdata)
    results = dbdata.get_table_data()
    ex.listview_init(results)

    sys.exit(app.exec_())
