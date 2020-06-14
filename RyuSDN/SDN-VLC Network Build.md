## SDN-VLC Network Build

- #### problem & solution

```bash
Q: ovs-vsctl: unix:/usr/local/var/run/openvswitch/db.sock: database connection failed
# ovs 需要 the ovsdb, ovs-vswitchd, ovs-vsctl, 但是关机后它们会默认关闭

A: run as root
ovsdb-server --remote=punix:/usr/local/var/run/openvswitch/db.sock \
                     --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
                     --private-key=db:Open_vSwitch,SSL,private_key \
                     --certificate=db:Open_vSwitch,SSL,certificate \
                     --bootstrap-ca-cert=db:Open_vSwitch,SSL,ca_cert \
                     --pidfile --detach
ovs-vsctl --no-wait init
ovs-vswitchd --pidfile --detach
# refer : https://blog.csdn.net/xyq54/article/details/51371819

```

- #### ryu run demo

  

```
ryu-manager --ofp-tcp-listen-port 6634 demo.py
```



- #### linux commend

```bash
# 回车，如果你安装好了，就会显示文件安装的地址

whereis {$软件名称}
```

- #### Mininet

```bash
# build network
sudo mn --topo single,3 --mac --switch ovsk --controller remote -x

# watch packet in every computer
tcpdump -en -i h1-eth0
```

