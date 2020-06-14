from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ipv4
from ryu.lib.packet import ether_types

VLC_FRAME     = 0x2050              # VLC FRAME
VLC_REG_FRAME = bytes(b'\x01\x02')  # up-link register 
VLC_FBK_FRAME = bytes(b'\x03\x04')  # up-link feedback
VLC_DAT_FRAME = bytes(b'\x05\x06')  # down-link data stream
VLC_ARK_FRAME = bytes(b'\x07\x08')  # down-link ueid stream
VLC_BUF_FRAME = bytes(b'\x09\x10')  # down-link buff stream

led_mac_table = {1:'00:02:00:04:00:06',}
vlc_port      = 1
wifi_port     = 2
router_port   = 3
LED_MAX       = 12      # limit of LED AP number
UE_MAX        = 40      # limit of join's user number

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}

        self.ue_mac_table   = {}
        self.feedback_ledid = {}        # LED near UE
        self.feedback_tslot = {}        # UE using's slot
        self.ue_count = 0
        self.ue_tree = {}

        # interference table
        self.vaildslot = {}
        for i in range(LED_MAX):
            self.vaildslot[i+1] = 0
            self.ue_tree[i+1]   = []


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)


    def _send_packet(self, datapath, port, pkt):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        pkt.serialize()
        self.logger.info("packet-out %s" % (pkt,))
        data = pkt.data 

        actions = [parser.OFPActionOutput(port=port)]
        out = parser.OFPPacketOut(  datapath=datapath,
                                    buffer_id=ofproto.OFP_NO_BUFFER,
                                    in_port=ofproto.OFPP_CONTROLLER,
                                    actions=actions,
                                    data=data)
        datapath.send_msg(out)

    # manage user mobily and intenet speed
    def management(self, ueid, ledid, src=None):
        vaildslot = self.vaildslot[ledid[0]] | self.vaildslot[ledid[1]] | self.vaildslot[ledid[2]]

        # if user is regitered
        if src == None or src in self.ue_mac_table:
            if src != None:
                ueid = self.ue_mac_table[src]

            # if the localation, delelate old tabel
            if ledid[0] != self.feedback_ledid[ueid]:
                self.ue_tree[self.feedback_ledid[ueid]].remove(ueid)

                for ue in self.ue_tree[ledid[0]]:
                    result = vaildslot | (1 << self.feedback_tslot[ue])

                for i in range(4):
                    if result & (1 << i) == 0:
                        self.feedback_tslot[ueid] = i
                        self.feedback_ledid[ueid] = ledid[0]
                        self.ue_tree[ledid[0]].append(ueid)
                        break
                    ######
                    ##    if invaild slot, how to deal?
    
        # if user is first come   
        else:
            self.ue_count = self.ue_count + 1
            ueid          = self.ue_count
            self.ue_mac_table[src] = ueid

            for ue in self.ue_tree[ledid[0]]:
                result = vaildslot | (1 << self.feedback_tslot[ue])

            for i in range(4):
                if result & (1 << i) == 0:
                    self.feedback_tslot[ueid] = i
                    self.feedback_ledid[ueid] = ledid[0]
                    self.ue_tree[ledid[0]].append(ueid)
                    break
                self.feedback_tslot[ueid] = None
            
        return ueid
                ######
                ##    if invaild slot, how to deal?

        #####
        ## del tabel when user go far
            
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return
        dst = eth.dst
        src = eth.src

        mark = eth.ethertype
        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        self.logger.info("packet in %s %s %s %s,  %s", dpid, src, dst, in_port, len(msg.data))

        # every echo includes a parameter
        self.ue_mac_table[ofproto.OFPP_FLOOD] = 0xFFFF

###     
        if mark == VLC_FRAME:
            data   = msg.data[14:]
            vtype  = data[0:2]      # vlc_ctl frame type

            ledid1 = int.from_bytes(data[6:8 ], 'big')
            rssmx1 = int.from_bytes(data[8:10], 'big')

            if ledid1 > LED_MAX or ledid1 < 1 or rssmx1 <100:   
                self.logger.info('bad LEDID')
                return
            ledid = [ledid1,]

            ledid2 = int.from_bytes(data[10:12], 'big')
            rssmx2 = int.from_bytes(data[12:14], 'big')

            if ledid2 <= LED_MAX and ledid2 > 0 and rssmx2 > 0:
                ledid.append(ledid2)

                ledid3 = int.from_bytes(data[14:16], 'big')
                rssmx3 = int.from_bytes(data[16:18], 'big')
                if ledid3 <= LED_MAX and ledid3 > 0 and rssmx3 > 0:
                    ledid.append(ledid3)

            if vtype == VLC_REG_FRAME:
                vueid = self.management(None, ledid, src=src)
                ts = self.feedback_tslot[vueid]
                
                src_bytes = msg.data[6:13]
                # build ack packet: type | length | LEDID | timeslot | UEID | UE-MAC 
                vlchead = VLC_ARK_FRAME + bytes([0, 16]) + bytes([0, ledid[0]]) + bytes([0, ts]) + bytes([0, vueid]) + src_bytes

                pkt = packet.Packet()

                ethhead = ethernet.ethernet(dst='ff:00:ff:00:ff:00', src='aa:00:aa:00:aa:00', ethertype=VLC_FRAME)
                pkt.add_protocol(ethhead)
                pkt.add_protocol(vlchead)

                self._send_packet(datapath, vlc_port, pkt)
                return

    ## update table
            elif vtype == VLC_FBK_FRAME:
                self.management(vueid, ledid)
                return

    ## unknow vlc frame
            else:
                self.logger.info('LOG: unexpected vlc frame type')
                return
###
        elif in_port == router_port:

    ## for data to specific user
            if dst in self.ue_mac_table:
                vueid  = self.ue_mac_table[dst]
                if vueid == 0xFFFF:
                    ledid = 0
                    tslot = 0
                else:
                    ledid = self.feedback_ledid[vueid]
                    tslot = self.feedback_tslot[vueid]

                pkt  = packet.Packet()
                lens = len(msg.data)
                self.logger.info('lens: %d', lens)
                # build data packet: type | length | LEDID | timeslot | UEID | SrvFlag 
                vlchead = VLC_DAT_FRAME + lens.to_bytes(2,'big') + bytes([0, ledid]) + bytes([0, tslot]) + bytes([0, vueid]) + bytes([0, 0, 0, 0])

                ethhead = ethernet.ethernet(dst= led_mac_table[ledid], ethertype=VLC_FRAME)
                pkt.add_protocol(ethhead)
                pkt.add_protocol(vlchead)
                pkt.add_protocol(msg.data[14:])

                self._send_packet(datapath, vlc_port, pkt)
                return
    
    ## drop frame
            else:
                self.logger.info('R: dst not in reg_user_table')
                return

## deal with up-link data

        elif in_port == wifi_port:
            actions = [parser.OFPActionOutput(port = router_port)]
            out = parser.OFPPacketOut(  datapath=datapath,
                                        buffer_id=ofproto.OFP_NO_BUFFER,
                                        in_port=ofproto.OFPP_CONTROLLER,
                                        actions=actions,
                                        data=msg.data)
            datapath.send_msg(out)
