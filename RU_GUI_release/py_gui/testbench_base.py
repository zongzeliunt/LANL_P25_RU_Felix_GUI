#Zongze Li added for GUI
#===========================================
#import os
#import sys
#directory = "RU_GUI_external_opts"
#if os.path.exists(directory):
#    sys.path.append(directory)
#    import RU_GUI_external_opts
#===========================================

import json
default_parameter_dict = {}
default_parameter_dict["PULSE_VPULSEH"] 			= 170
default_parameter_dict["PULSE_VPULSEL"] 			= 100
default_parameter_dict["IBIAS"] 					= 64
default_parameter_dict["VRESETD"] 					= 147
default_parameter_dict["VCASN"] 					= 50 
default_parameter_dict["VCASP"] 					= 86
default_parameter_dict["VCLIP"] 					= 0
default_parameter_dict["VCASN2"] 					= 57
default_parameter_dict["IDB"]						= 29
default_parameter_dict["ITHR"] 						= 50
default_parameter_dict["ITHR_commitTransaction"] 	= "True"

class SensorMatrixPattern(enum.IntEnum):
    EMPTY = 0
    IMAGE = 1


class Testbench(object):
    """Testbench for executing different tests"""

    def __init__(self,use_usb_comm=USE_USB_COMM):
        # setup comms
        self.logger = None
        self.serv = None
        self.comm_cru = None
        self.comm_rdo = None
        self.cru = None
        self.rdo = None
        self.powerunit = None

        self.use_usb_comm = use_usb_comm

        self.chips = [None for i in range(9)]

        self.logger = logging.getLogger(TBNAME)
        if STANDALONE_RUN:
            self.setup_standalone()

    def tg_notification(self, message):
        self.logger.debug("sending message to tg: \"{0}\"".format(message))
        os.system('telegram-send "{0}"'.format(message))

    def version(self, get_pa3=False):
        git_hash_cru = self.cru.status.get_git_hash()
        git_hash_rdo = self.rdo.status.get_git_hash()
        if get_pa3:
            pa3_version = self.cru.pa3.get_version()

        self.logger.info("CRU Version: {0:07X}".format(git_hash_cru))
        self.logger.info("RDO Version: {0:07X}".format(git_hash_rdo))
        if get_pa3:
            self.logger.info("PA3 Version: {0:04X}".format(pa3_version))

    def setup_standalone(self):
        self.setup_logging()
        self.setup_comms()
        self.setup_boards()

    def setup_logging(self):
        # Logging folder
        self.logdir = os.path.join(
            os.getcwd(),
            'logs/Testbench')
        try:
            os.makedirs(self.logdir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
        # setup logging
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        log_file = os.path.join(self.logdir, TBNAME+".log")
        log_file_errors = os.path.join(self.logdir,
                                       TBNAME+"_errors.log")

        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)

        fh2 = logging.FileHandler(log_file_errors)
        fh2.setLevel(logging.ERROR)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        fh.setFormatter(formatter)
        fh2.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(fh2)
        logger.addHandler(ch)

        self.logger = logger

    def setup_comms(self,cru_ctlOnly=False):
        """Setup Communication interfaces for CRU and RDO"""
        if USE_CRU:
            self.setup_comm_cru(ctlOnly=cru_ctlOnly)
        self.setup_comm_rdo(ctlOnly=cru_ctlOnly)

    def setup_comm_cru(self,ctlOnly=False):
        """Setup Communication interfaces for CRU"""
        if self.use_usb_comm:
            self.serv = communication.UsbCommServer(
                USB_COMM_EXEC, serial=SERIAL_CRU)
            self.serv.start()
            time.sleep(0.1)
            comm = communication.NetUsbComm(ctlOnly=ctlOnly, Timeout=0.5)
            comm.set_server(self.serv)
            comm = communication.PrefetchCommunication(comm)
            comm.enable_rderr_exception()
            time.sleep(0.2)
            self.logger.debug(self.serv.read_messages())
        else:
            comm = communication.PyUsbComm(serialNr=SERIAL_CRU)
        self.comm_cru = comm

    def setup_comm_rdo(self,ctlOnly=True):
        """Setup Communication interfaces for RDO"""
        if USE_RDO_USB:
            if self.use_usb_comm:
                raise NotImplementedError
            else:
                self.comm_rdo = communication.PyUsbComm(serialNr=SERIAL_RDO,dipswitch=DIPSWITCH)
                #self.comm_rdo = communication.PyUsbComm(serialNr=SERIAL_RDO)
        else:
            self.comm_rdo = self.comm_cru

    def stop(self):
        if USE_CRU:
            self.comm_cru.stop()
        self.comm_rdo.stop()
        if self.use_usb_comm:
            self.serv.stop()

    def setup_cru(self):
        self.cru = ru_board.RUv0_CRU(self.comm_cru)

    def setup_rdo(self, connector_nr=4, num_gth=9):
        self.rdo = ru_board.RUv1(self.comm_rdo, num_gth)

        self.set_dctrl_connector(connector_nr)
        self.rdo.enable_chip2connector_lut(False)

        self.chips = [Alpide(self.rdo, chipid=i) for i in range(9)]
        return self

    def set_dctrl_connector(self,connector_nr,force=False):
        lut = {i: connector_nr for i in range(9)}
        self.rdo.set_chip2connector_lut(lut)
        if force:
            self.rdo.dctrl.set_input(connector_nr,force=True)

    def setup_powerunit(self, i2c_connector_on_ruv1=1):
        if i2c_connector_on_ruv1 == 1:
            self.powerunit = self.rdo.powerunit_1
        elif i2c_connector_on_ruv1 == 2:
            self.powerunit = self.rdo.powerunit_2
        else:
            raise NotImplementedError

    def setup_boards(self):
        """Setup board classes"""
        self.setup_cru()
        self.setup_rdo(num_gth=NUM_GTH)
        self.setup_powerunit()
        self.gth_subset(GTH_SUBSET)

    def initialize_boards(self):
        #self.cru.initialize()
        self.rdo.initialize()
        self.powerunit.initialize()

    def gpio_subset(self,transceivers):
        self.rdo.gpio.set_transceivers(transceivers)
        for idx in transceivers:
            if idx in GPIO_SENSOR_MASK:
                self.rdo.gpio.set_lane_chip_mask(idx,GPIO_SENSOR_MASK[idx])
            else:
                self.logger.warning("GPIO subset, Lane %d has no sensor mask defined",idx)
        self.rdo.datapathmon_gpio.set_lanes(transceivers)
        self.rdo.gbt_packer_gpio.update_masks(transceivers)
        return self

    def gth_subset(self,transceivers):
        self.rdo.gth.set_transceivers(transceivers)
        self.rdo.datapathmon.set_lanes(transceivers)
        self.rdo.gbt_packer_gth.update_masks(transceivers)
        return self

    def test_readout_gpio_routine(self, connector=0, scan_idelay=False, nr_triggers=10):
        self.rdo.gpio.enable_data(False)
        self.setup_rdo(connector)
        self.gpio_subset(list(range(7*connector,7*connector+7)))
        if scan_idelay:
            self.scan_idelay_gpio(stepsize=10,waittime=0.1)
        self.setup_sensors(LinkSpeed=0)
        self.setup_readout_gpio()
        self.cru.send_start_of_triggered()
        self.logger.setLevel(logging.WARNING)
        i = 0

        triggers_sent = 0
        total_events = 0
        total_errors = 0
        try:

            while True:
                events, errors = self.test_readout_gpio(nr_triggers,dump_data=False)
                total_events += events
                total_errors += errors
                triggers_sent += nr_triggers
                print('.',end='', flush=True)
                i += 1
                if i % 20 == 0:
                    self.logger.setLevel(logging.INFO)
                    msg = 'Sent: {0} triggers total, Received {1} events, {2} errors'.format(triggers_sent,total_events,total_errors)
                    print(msg)
                    self.logger.info(msg)
                    cru_adc_vals = self.cru.read_adcs_conv()
                    print(cru_adc_vals)
                    self.logger.info(cru_adc_vals)
                    self.logger.setLevel(logging.WARNING)
        except KeyboardInterrupt as ki:
            self.logger.setLevel(logging.INFO)
            self.logger.info("Done")
            msg = 'Sent: {0} triggers total, Received {1} events, {2} errors'.format(triggers_sent,total_events,total_errors)
            self.logger.info(msg)
            self.cru.send_end_of_triggered()

    def read_maskfile(self,filename):
        maskdict = {}
        with open(filename,"r") as f:
            data = f.readlines()
            for line in data:
                splitline = line.split(',')
                if len(splitline)!=4 or line[0]=="#":
                    continue
                chipcoords = (int(splitline[0]),int(splitline[1]))
                pixelcoords = (int(splitline[2]),int(splitline[3]))
                if chipcoords not in maskdict:
                    maskdict[chipcoords] = [pixelcoords]
                else:
                    maskdict[chipcoords].append(pixelcoords)
        return maskdict
        #print(maskdict)

    def parameter_dict_read_from_json_file (self):
        result_dict = {} 
        file_name = "./parameter.json"
        try:
            fl = open(file_name, "r")
            result_dict = json.load(fl)
            for arg in result_dict:
                if not arg == "ITHR_commitTransaction":
                        result_dict[arg] = int(result_dict[arg])
            fl.close()
        except:
            #default values
            result_dict = default_parameter_dict 
        return result_dict
    
    def read_sensors(self,enable_strobe_generation=0,LinkSpeed=3,disable_manchester=1, pattern=SensorMatrixPattern.EMPTY):
        maskdict = self.read_maskfile("masklist_"+TBNAME+".txt")
        #do GRST at the beginning, since it's global
        self.rdo.dctrl.set_dctrl_mask(0x1F) #restore broadcast to all connectors
        #ch_broadcast = Alpide(self.rdo, chipid=0x0F)
        #ch_broadcast.reset()
       
        #for connector,chipid in CHIP_MAP:
        connector = 0
        chipid = 1
        self.rdo.dctrl.set_dctrl_mask(1<<connector)
        self.rdo.dctrl.set_input(connector,force=True)
        ch = Alpide(self.rdo, chipid=chipid)
        
        #=================================
        read_parameter_dict = {}

        read_parameter_dict["PULSE_VPULSEH"] = ch.getreg_VPULSEH(commitTransaction = True)[0] 
        read_parameter_dict["PULSE_VPULSEL"] = ch.getreg_VPULSEL(commitTransaction = True)[0] 
        read_parameter_dict["IBIAS"] = ch.getreg_IBIAS  (commitTransaction = True)[0] 
        read_parameter_dict["VRESETD"] = ch.getreg_VRESETD(commitTransaction = True)[0] 
        read_parameter_dict["VCASN"] = ch.getreg_VCASN  (commitTransaction = True)[0] 
        read_parameter_dict["VCASP"] = ch.getreg_VCASP  (commitTransaction = True)[0] 
        read_parameter_dict["VCLIP"] = ch.getreg_VCLIP  (commitTransaction = True)[0] 
        read_parameter_dict["VCASN2"] = ch.getreg_VCASN2 (commitTransaction = True)[0] 
        read_parameter_dict["IDB"] = ch.getreg_IDB    (commitTransaction = True)[0] 
        read_parameter_dict["ITHR"] = ch.getreg_ITHR   (commitTransaction = True)[0] 
        read_parameter_dict["ITHR_commitTransaction"] = "True"
        file_name = "./read_parameter.json"
        fl = open(file_name, "w")
        json.dump(read_parameter_dict, fl)
        fl.close()

        #=================================


    def setup_sensors(self,enable_strobe_generation=0,LinkSpeed=3,disable_manchester=1, pattern=SensorMatrixPattern.EMPTY):
        maskdict = self.read_maskfile("masklist_"+TBNAME+".txt")
        #do GRST at the beginning, since it's global
        self.rdo.dctrl.set_dctrl_mask(0x1F) #restore broadcast to all connectors
        ch_broadcast = Alpide(self.rdo, chipid=0x0F)
        ch_broadcast.reset()
        for connector,chipid in CHIP_MAP:
            self.rdo.dctrl.set_dctrl_mask(1<<connector)
            self.rdo.dctrl.set_input(connector,force=True)
            ch = Alpide(self.rdo, chipid=chipid)
            self.rdo.gth.initialize(check_reset_done=False)
            ch.initialize(disable_manchester=disable_manchester, grst=False, cfg_ob_module=False)
            ch.setreg_dtu_dacs(PLLDAC=8, DriverDAC=0x8, PreDAC=0x8)
            
            #this is added by Zongze Li for GUI
            parameter_dict = self.parameter_dict_read_from_json_file()
            ch.setreg_VPULSEH (VPULSEH=parameter_dict["PULSE_VPULSEH"])
            ch.setreg_VPULSEL (VPULSEL=parameter_dict["PULSE_VPULSEL"])
            ch.setreg_IBIAS (IBIAS=parameter_dict["IBIAS"])
            ch.setreg_VRESETD (VRESETD=parameter_dict["VRESETD"])
            ch.setreg_VCASN (VCASN=parameter_dict["VCASN"])
            ch.setreg_VCASP (VCASP=parameter_dict["VCASP"])
            ch.setreg_VCLIP (VCLIP=parameter_dict["VCLIP"])
            ch.setreg_VCASN2(VCASN2=parameter_dict["VCASN2"])
            ch.setreg_IDB (IDB=parameter_dict["IDB"])
            ch.setreg_ITHR (ITHR=parameter_dict["ITHR"],\
                    commitTransaction=parameter_dict["ITHR_commitTransaction"])
            
            """
            #this is original version
            ch.setreg_VPULSEH(VPULSEH=PULSE_VPULSEH)
            ch.setreg_VPULSEL(VPULSEL=PULSE_VPULSEL)
            ch.setreg_IBIAS(IBIAS=64)
            ch.setreg_VRESETD(VRESETD=147)
            ch.setreg_VCASN(VCASN=50)
            #ch.setreg_VCASN(VCASN=60)#tweak to lower threshold
            ch.setreg_VCASP(VCASP=86)
            ch.setreg_VCLIP(VCLIP=0)
            #ch.setreg_VCASN2(VCASN2=117)
            ch.setreg_VCASN2(VCASN2=57)
            #ch.setreg_IDB(IDB=29)
            ch.setreg_IDB(IDB=29)
            ch.setreg_ITHR(ITHR=50,commitTransaction=True)
            #ch.setreg_ITHR(ITHR=30,commitTransaction=True)#tweak to lower threshold
            """

            for pll_off_sig in [0, 1, 0]:
                ch.setreg_dtu_cfg(VcoDelayStages=1,
                                  PllBandwidthControl=1,
                                  PllOffSignal=pll_off_sig,
                                  SerPhase=8,
                                  PLLReset=0,
                                  LoadENStatus=0)

            ch.setreg_fromu_cfg_1(
                MEBMask=0,
                EnStrobeGeneration=enable_strobe_generation,
                EnBusyMonitoring=1,
                PulseMode=PULSE_ANOTD,
                EnPulse2Strobe=1,
                EnRotatePulseLines=0,
                TriggerDelay=0)

            # Duration of a Strobe Frame (Trigger)
            #ch.setreg_fromu_cfg_2(FrameDuration=0x3) # (3+1)*25ns
            ch.setreg_fromu_cfg_2(FrameDuration=80) # from MOSAIC. default for testbeam
            # Gap between Strobes (internal Trigger, when EnStrobeGeneration=1)
            ch.setreg_fromu_cfg_3(FrameGap=0x9) # (9+1)*25ns
            # Duration of PULSE window
            #ch.setreg_fromu_pulsing_2(PulseDuration=0x8) # 8*25ns
            ch.setreg_fromu_pulsing_2(PulseDuration=500) # copied from MOSAIC test_threshold - for analog pulsing this value must be large, since the (capacitively coupled) charge injection happens at edges of the pulse and you don't want to see the falling edge
            # Delay between Start of PULSE and start of STROBE (when EnPulse2Strobe=1)
            #ch.setreg_fromu_pulsing1(PulseDelay=0x1) # (1+1)*25ns
            ch.setreg_fromu_pulsing1(PulseDelay=PULSE_DELAY)

            #self.setup_sensor_matrix(ch,pattern=pattern)
            self.setup_sensor_matrix_list(ch,(connector,chipid),maskdict) #mask all pixels listed in the text file

            # ChipModeSelector determines the trigger mode:
            # 0=disabled, 1=triggered, 2=continuous
            ch.setreg_mode_ctrl(ChipModeSelector=1,
                                EnClustering=1, #enable clustering
                                #EnClustering=0, #disable clustering (simpler data format)
                                MatrixROSpeed=1,
                                IBSerialLinkSpeed=LinkSpeed,
                                EnSkewGlobalSignals=1,
                                EnSkewStartReadout=1,
                                EnReadoutClockGating=1,
                                EnReadoutFromCMU=0)
            self.rdo.dctrl.flush()
        self.rdo.dctrl.set_dctrl_mask(0x1F) #restore broadcast to all connectors
        #do RORST at the end, since it's global
        ch_broadcast.board.write_chip_opcode(Opcode.RORST)

	#read_tem=False; 
    def readback_sensors(self,read_temp=True):
        for connector,chipid in CHIP_MAP:
            print("testing connector {0}, chipid {1}".format(connector,chipid))
            ch = Alpide(self.rdo, chipid=chipid)
            self.rdo.dctrl.set_dctrl_mask(1<<connector)
            self.rdo.dctrl.set_input(connector,force=True)
            print(ch.getreg_mode_ctrl())
            if read_temp:
                print(ch.read_temperature())
        self.rdo.dctrl.set_dctrl_mask(0x1F) #broadcast to all connectors

    def suppress_stdout():
        with open(os.devnull, "w") as devnull:
            old_stdout = sys.stdout
            sys.stdout = devnull
            try:
                yield
            finally:
                sys.stdout = old_stdout

# 0x04 is READ_STATUS, could be used just before breaking loop to clear lingering commands
    def monitor_temp(self):
        stdscr = curses.initscr()
        stdscr.nodelay(True)
        init_temp = [] #store temperature readings at initialization
        for connector,chipid in CHIP_MAP:
            if stdscr.getch() == ord('q'):
                break
            ch = Alpide(self.rdo, chipid=chipid)
            self.rdo.dctrl.set_input(connector,force=True)
            temperature = ch.read_temperature()
            init_temp.append(round(temperature['C'],3))
            print("\rStave {0}, Chip {1}. T(Init.) = {2} ".format(connector, chipid, round(temperature['C'],3)))
        while True:
            i = 0
            if stdscr.getch() == ord('q'):
                break
            for connector,chipid in CHIP_MAP:
                ch = Alpide(self.rdo, chipid=chipid)
                #self.rdo.dctrl.set_input(connector,force=True)
                temp_dict = ch.read_temperature()
                temp_celc = round(temp_dict['C'],3)
                sys.stdout.write("\rStave {0}, Chip {1}. T(Curr.) = {2}, T(Curr.) - T(Init.) = {3} ".format(connector, chipid, temp_celc, round(temp_celc - init_temp[i],3)))
                sys.stdout.flush()
                time.sleep(1)
                i+=1
            self.rdo.dctrl.set_dctrl_mask(0x1F) #broadcast to all connectors


    def setup_sensor_matrix(self,ch,pattern = SensorMatrixPattern.EMPTY):
        if pattern == SensorMatrixPattern.EMPTY:
            ch.pulse_all_pixels_disable()
            ch.mask_all_pixels()
        elif pattern == SensorMatrixPattern.IMAGE:
            self.setup_sensor_matrix_image(self,ch,image='sensor_pattern.bmp')
        else:
            raise NotImplementedError("Pattern not defined")


    def setup_sensor_matrix_image(self,ch,img_path):
        image= imageio.imread(img_path)
        ch.pulse_all_pixels_disable()
        ch.mask_all_pixels()
        coords = []
        for (row,col), value in numpy.ndenumerate(image):
            if value == 0:
                coords.append( (col,row) )
        ch.unmask_pixel(coords,readback=False,log=False,commitTransaction=False)
        ch.pulse_pixel_enable(coords,readback=False,log=False,commitTransaction=True)
        self.logger.debug("Unmask {0} pixels per image pattern".format(len(coords)))

    def setup_sensor_matrix_hardcoded(self,ch):
        ch.pulse_all_pixels_disable()
        ch.mask_all_pixels()
        coords = []
        for i in range(0,10):
            coords.append( (i,0) )
        ch.unmask_pixel(coords,readback=False,log=False,commitTransaction=False)
        ch.pulse_pixel_enable(coords,readback=False,log=False,commitTransaction=True)
        self.logger.debug("Unmask {0} pixels per image pattern".format(len(coords)))

    def setup_sensor_matrix_list(self,ch,chipcoords,maskdict):
        ch.pulse_all_pixels_disable()
        if SETUP_PULSE:
            coords = []
            for i in range(0,10):
                coords.append( (i,0) )
            ch.pulse_pixel_enable(coords,readback=False,log=False,commitTransaction=True)
        ch.unmask_all_pixels()
        if chipcoords in maskdict:
            print("masking {0} pixels on chip {1}".format(len(maskdict[chipcoords]),chipcoords))
            ch.mask_pixel(maskdict[chipcoords],readback=False,log=False,commitTransaction=True)

    def setup_pulser(self, chip=0x8):
        chip = Alpide(self.rdo, chipid=chip)
        # unmask one column
        #chip.unmask_col(1)
        #chip.unmask_row(500)

        # unmask single pixels
        # Modify the unmasking register, set the value to 0
        chip.setreg_pixel_cfg(PIXCNFG_REGSEL=0, PIXCNFG_DATA=0)
        #px = 5 # set pixel column
        py = 5 # set pixel row
        for px in  range(0,1024,16):
            # set the previously configured register value for the pixel with given address
            chip._address_pixel(px, py)

    def clear_pulser(self):
        ch = Alpide(self.rdo, chipid=0x0F)  # global broadcast
        ch.mask_all_pixels()

    def setup_prbs_test(self,chips):
        for i in chips:
            ch = Alpide(self.rdo,chipid=i)
            ch.propagate_prbs()
        self.rdo.gth.initialize()
        self.rdo.gth.enable_prbs(enable=True, commitTransaction=True)
        self.rdo.gth.reset_prbs_counter()

    def setup_prbs_test_gpio(self,SENSORS):
        self.rdo.gpio.enable_data(False)
        for i in SENSORS:
            ch = Alpide(self.rdo,chipid=i)
            ch.setreg_mode_ctrl(IBSerialLinkSpeed=2)
            ch.propagate_prbs(PrbsRate=1)
        self.rdo.gpio.enable_prbs(enable=True, commitTransaction=True)
        self.rdo.gpio.reset_prbs_counter()


    def scan_idelay_gpio(self,stepsize=10,waittime=1, set_optimum=True):
        self.setup_prbs_test_gpio()

        self.rdo.gpio.scan_idelays(stepsize,waittime,set_optimum,True)

        for ch in self.chips:
            ch.setreg_mode_ctrl(IBSerialLinkSpeed=0)
            ch.propagate_data()

    def chips_propagate_clock(self,first=0,last=8):
        for i in range(first,last+1):
            ch = Alpide(self.rdo,chipid=i)
            ch.propagate_clock()

    def get_counters(self,commitTransaction=True):
        outdict = {}
        outdict.update(self.rdo.trigger_handler_monitor.get_counters())
        outdict.update(self.rdo.gbtx_flow_monitor.read_counters())
        return outdict

    def reset_counters(self,commitTransaction=True):
        self.rdo.datapathmon.reset_counters(commitTransaction=False)
        self.rdo.datapathmon_gpio.reset_counters(commitTransaction=False)
        self.rdo.gbt_packer_monitor_gth.reset_counters(commitTransaction=False)
        self.rdo.gbt_packer_monitor_gpio.reset_counters(commitTransaction=False)
        self.rdo.trigger_handler_monitor.reset_counters(commitTransaction=False)
        self.rdo.gbtx_flow_monitor.reset_counters(commitTransaction=commitTransaction)

    def setup_readout(self,max_retries=10):
        self.rdo.gbt_packer_gpio.set_settings(enable_data_forward=0)
        self.rdo.gbt_packer_gth.set_settings(enable_data_forward=1)

        self.rdo.gth.initialize(commitTransaction=True,
                                check_reset_done=True)
        self.rdo.wait(10000)
        initialized = self.rdo.gth.is_reset_done()
        result = True
        if not initialized:
            self.logger.error("Could not initialize GTH transceivers")
            result = False
        self.rdo.wait(1000)
        locked = self.rdo.gth.is_cdr_locked()
        if False in locked:
            self.logger.error(
                "Could not lock to all sensor clocks: %s", locked)
            result = False
        aligned = self.rdo.gth.align_transceivers(check_aligned=True)
        retries = 0
        while not aligned and retries < max_retries:
            print(self.rdo.gth.is_aligned())
            retries +=1
            self.logger.info("Not Aligned, retry %d/%d",retries,max_retries)
            self.setup_sensors()
            aligned=self.rdo.gth.align_transceivers(check_aligned=True)
        if not aligned:
            self.logger.error("Could not align all transceivers to comma: %r", self.rdo.gth.is_aligned())
            result = False
        else:
            self.logger.info("All Transceivers aligned to comma")
            self.rdo.gth.enable_data()
        self.rdo.datapathmon.reset_counters()

        return result

    def setup_readout_gpio(self):
        self.rdo.gbt_packer_gpio.set_settings(enable_data_forward=1)
        self.rdo.gbt_packer_gth.set_settings(enable_data_forward=0)

        self.rdo.gpio.initialize()
        aligned = self.rdo.gpio.align_transceivers(check_aligned=True)
        result=True
        if not aligned:
            self.logger.error("Could not align all transceivers to comma")
            result = False
        else:
            self.logger.info("All Transceivers aligned to comma")
            self.rdo.gpio.enable_data()
        self.rdo.datapathmon_gpio.reset_counters()

        return result

    def setup_trigger_handler_continuous(self, trigger_frequency=10000,send_pulses=False):
        base_freq = 160000000
        trigger_period=int(base_freq/trigger_frequency)
        assert trigger_period < 2**16, "Given pulse frequency not reachable with trigger handler (too slow)"
        self.rdo.trigger_handler.set_trigger_period(trigger_period,False)
        self.rdo.trigger_handler.set_trigger_minimum_distance(1)
        if send_pulses:
            self.rdo.trigger_handler.configure_to_send_pulses()
        else:
            self.rdo.trigger_handler.configure_to_send_triggers()

    def chip(self, nr):
        """Return a chip with given number"""
        assert nr in range(9), "Chip {0} not in range(9)".format(nr)
        return self.chips[nr]

    def test_chips(self, nrfirst=0, nrlast=8,nrtests=100, verbose=True):
        """Perform a chip test on chips [first,last]"""
        start_time = time.time()
        total_errors = {}
        if verbose:
            self.logger.info("Test Chips %d to %d. Nr of RD/WR: %d",nrfirst,nrlast,nrtests)
        for chipid in range(nrfirst, nrlast + 1):
            assert chipid in range(
                9), "Chip {0} not in range(9)".format(chipid)
            if verbose:
                self.logger.info("Test Chip %d", chipid)
            errors = 0
            for j in range(nrtests):
                pattern = 0x0A+j
                self.chips[chipid].write_reg(0x19, pattern, readback=False)
                try:
                    rdback = self.chips[chipid].read_reg(0x19)
                    if rdback != pattern:
                        errors += 1
                        self.logger.error("Readback failure for Chip {0}".format(chipid))
                except:
                    errors += 1
                    self.logger.error("Readback failure for Chip {0}".format(chipid))
            if verbose:
                self.logger.info("Done. Errors: %d", errors)
            total_errors[chipid] = errors
        elapsed_time = time.time() - start_time
        if verbose:
            self.logger.info("Elapsed time {0}s".format(elapsed_time))
        return total_errors, elapsed_time

    def test_chips_fast(self, nrfirst=0, nrlast=8, nrtests=100):
        """Perform a chip test on chips [first,last]"""
        # reads once to set the correct connector to read from
        try:
            self.chips[0].read_reg(0)
        except:
            pass
        min_tests = 10
        if nrtests%min_tests != 0:
            self.logger.info("rounding up number of tests to a multiple of {0}".format(min_tests))
            nrtests = ((nrtests//min_tests)+1)*min_tests
        self.logger.info("Test Chips %d to %d. Nr of RD/WR: %d",
                         nrfirst,
                         nrlast,
                         nrtests)
        self.logger.info("expected run time is {0:.2f}s".format(3.59 + 0.00195*(nrtests - min_tests)))
        total_time = 0
        total_errors = {chipid: 0 for chipid in range(nrfirst, nrlast+1)}

        self.comm_rdo.start_recording()
        errors, elapsed_time = self.test_chips(nrfirst=nrfirst, nrlast=nrlast, nrtests=min_tests, verbose=False)
        total_time += elapsed_time
        total_errors = {chipid: total_errors[chipid]+errors[chipid] for chipid in total_errors.keys()}

        sequence = self.comm_rdo.stop_recording()
        if nrtests > min_tests:
            for i in range((nrtests//min_tests) -1):
                self.comm_rdo.load_sequence(sequence)
                self.comm_rdo.prefetch()
                errors, elapsed_time = self.test_chips(nrfirst=nrfirst, nrlast=nrlast, nrtests=min_tests, verbose=False)
                total_time += elapsed_time
                total_errors = {chipid: total_errors[chipid]+errors[chipid] for chipid in total_errors.keys()}

        for chipid in range(nrfirst, nrlast+1):
            self.logger.info("Chipid %d, Errors: %d", chipid, total_errors[chipid])
        self.logger.info("Elapsed time {0}s".format(total_time))
        return total_errors, total_time

    def test_chips_continuous(self, nrfirst=0, nrlast=8):
        """Perform a chip test on chips [first,last]"""
        # reads once to set the correct connector to read from
        PRINT_INTERVAL = 10
        try:
            self.chips[0].read_reg(0)
        except:
            pass
        min_tests = 10
        self.logger.info("Test Chips %d to %d",
                         nrfirst,
                         nrlast)
        total_time = 0
        total_errors = {chipid: 0 for chipid in range(nrfirst, nrlast+1)}

        # record sequence
        self.comm_rdo.start_recording()
        errors, elapsed_time = self.test_chips(nrfirst=nrfirst, nrlast=nrlast, nrtests=min_tests, verbose=False)
        total_time += elapsed_time
        total_errors = {chipid: total_errors[chipid]+errors[chipid] for chipid in total_errors.keys()}
        sequence = self.comm_rdo.stop_recording()

        has_failed = False
        start_time = last_read = time.time()
        try:

            while True:
                self.comm_rdo.load_sequence(sequence)
                self.comm_rdo.prefetch()
                errors, elapsed_time = self.test_chips(nrfirst=nrfirst, nrlast=nrlast, nrtests=min_tests, verbose=False)
                total_time += elapsed_time
                total_errors = {chipid: total_errors[chipid]+errors[chipid] for chipid in total_errors.keys()}
                if(time.time() - last_read) > PRINT_INTERVAL:
                    last_read = time.time()
                    self.logger.info("Total errors {0}, in {1:.2f}s".format(total_errors, last_read-start_time))
                    if sum([errors[chipid] for chipid in total_errors.keys()]) > 0:
                        has_failed = False
                        self.tg_notification("Errors detected: {0} at {1:.2f} s. Execution paused".format(total_errors, last_read-start_time))
                        input("press a key to continue...")

        except KeyboardInterrupt as ki:
            self.logger.info("Ctrl-c")

        for chipid in range(nrfirst, nrlast+1):
            self.logger.info("Chipid %d, Errors: %d", chipid, total_errors[chipid])
        self.logger.info("Elapsed time {0}s".format(time.time() - start_time))

    def test_dclk_phases(self, nrtests=1000, connector=None, manchester_tx_en=False):
        BASE_CONNECTOR = 4
        FIRST = 0
        LAST = 8
        if connector is None:
            connector = 4
        else:
            assert connector in range(5)
        if manchester_tx_en:
            self.rdo.dctrl.enable_manchester_tx()
        phase_list = self.rdo.dctrl.phase_dict.keys()
        errors_dict = {}
        initial_phase = self.rdo.dctrl.get_dclk_parallel(index=connector)
        total_time = 0
        self.rdo.dctrl.logger.setLevel(logging.CRITICAL)
        self.logger.setLevel(logging.CRITICAL)
        for phase in phase_list:
            self.rdo.dctrl.set_dclk_parallel(index=connector, phase=phase)
            self.setup_sensors()
            errors, elapsed_time = self.test_chips_fast(nrfirst=FIRST, nrlast=LAST, nrtests=nrtests)
            errors_dict[phase] = errors
            total_time += elapsed_time
        self.rdo.dctrl.set_dclk_parallel(index=connector, phase=initial_phase)
        if manchester_tx_en:
            self.rdo.dctrl.disable_manchester_tx()
        self.rdo.dctrl.logger.setLevel(logging.INFO)
        self.logger.setLevel(logging.INFO)
        self.setup_sensors()
        for phase in errors_dict.keys():
            self.logger.info("Phase \t{0}\ttotal errors \t{1}".format(phase, sum(errors_dict[phase].values())))
        return errors_dict, total_time


    def test_prbs(self, runtime=10):
        self._test_prbs(frontend=self.rdo.gth,runtime=runtime)

    def test_prbs_gpio(self,runtime=10):
        self._test_prbs(frontend=self.rdo.gpio,runtime=runtime)

    def _test_prbs(self,frontend,runtime=10):
        frontend.enable_data(False)
        for ch in self.chips:
            ch.propagate_prbs(PrbsRate=0)

        frontend.enable_prbs(enable=True, commitTransaction=True)
        frontend.reset_prbs_counter()

        self.logger.info("Chip + Board setup for PRBS run.")
        self.logger.info("Wait for %d s", runtime)
        time.sleep(runtime)

        prbs_errors = frontend.read_prbs_counter(self)
        all_errors = 0
        for cnt, link in zip(prbs_errors, frontend.transceivers):
            if cnt > 0:
                self.logger.error(
                    "Link %d: %d PRBS Errors observed", link, cnt)
            all_errors += cnt
        self.logger.info("PRBS run finished. Total Errors: %d", all_errors)

        for ch in self.chips:
            ch.propagate_data()

    def _test_readout(self, dpmon, nr_triggers=10, dump_data=False):

        dpmon.reset_counters()
        self.cru.comm.discardall_dp2()

        self.rdo.dctrl.reset_counters()

        time.sleep(0.1)

        self.logger.info(
            "Counters reset. Send %d triggers over CRU", nr_triggers)
        for i in range(nr_triggers):
            self.cru.send_trigger(orbit=i)
            self.cru.wait(1000)
        self.logger.info(
            "All Triggers sent. Start checking counters + readback")
        events_received = False
        retries = 0

        while not events_received and retries < 20:
            event_counters = dpmon.read_counter(None,counter="EVENT_COUNT")
            if not isinstance(event_counters,collections.Iterable):
                event_counters = [event_counters]

            events_received = all(
                [trig == nr_triggers for trig in event_counters])
            retries += 1
            if not events_received:
                time.sleep(0.25)
        counters = dpmon.read_all_counters()
        for lane,r in enumerate(counters):
            for name, val in counters[lane].items():
                expected_val = 0
                any_val = False
                if name == 'EVENT_COUNT':
                    expected_val = nr_triggers
                elif name == 'IDLE_WORD_COUNT':
                    any_val = True
                if not any_val and val != expected_val:
                    self.logger.error("Lane %d, counter '%s': Counter value '%d' not as expected (%d)",
                                      lane, name, val, expected_val)
                #self.logger.info("Lane %d, counter '%s': value: %d",lane,name,val)

        if dump_data:
            self.logger.info(pprint.pformat(counters))

        self.logger.info("Events received: %r", event_counters)
        self.logger.info("Event counters read and checked.")

        dctrl_counters = self.rdo.dctrl.get_counters()
        self.logger.info(dctrl_counters)
        if dctrl_counters['trigger_sent'] != nr_triggers:
            self.logger.error(
                "dctrl: Not all Triggers sent: {0}/{1}".format(dctrl_counters['trigger_sent'], nr_triggers))

        return self.check_event_readout(nr_triggers,nr_triggers, dpmon.lanes, dump_data)


    def test_readout(self,nr_triggers=10,dump_data=False):
        return self._test_readout(self.rdo.datapathmon,nr_triggers,dump_data)

    def test_readout_gpio(self,nr_triggers=10,dump_data=False):
        return self._test_readout(self.rdo.datapathmon_gpio,nr_triggers,dump_data)

    def test_pa3_read_loop(self, nrTests = 100):
        self.comm_cru.start_recording()
        self.cru.pa3.dump_config()
        sequence = self.comm_cru.stop_recording()
        for i in range(nrTests):
            self.comm_cru.load_sequence(sequence)
            self.comm_cru.prefetch()
            self.cru.pa3.dump_config()

    def test_usb_performance_read(self,packets_per_train=1000,nr_trains=1000,test_cru=True,test_rdo=True):
        self.logger.info("Test USB Performance: Read (usb_comm: %r)",self.use_usb_comm)
        assert test_cru or test_rdo, "At least CRU or RDO must be set to True"
        if test_cru and test_rdo:
            packet_range = range(packets_per_train//2)
        else:
            packet_range = range(packets_per_train)
        start = time.time()
        for i in range(nr_trains):
            for j in packet_range:
                if test_cru:
                    self.cru.read(0x41,1,False)
                if test_rdo:
                    self.rdo.read(1,1,False)
            self.cru.flush()
            results = self.cru.read_all()
            if len(results) != packets_per_train:
                self.logger.error("Train %d: Not all packets received: %d/%d",i,len(results),packets_per_train)
        end = time.time()
        duration = end-start
        mbit_sent = packets_per_train*nr_trains*32/(1024*1024)
        data_rate = mbit_sent/duration
        self.logger.info("Test finished in %.4f seconds. Raw data rate (Send/Receive): %.4f Mbps", duration,data_rate)

        self.logger.info("Test USB Performance done")

        return mbit_sent, duration

    def test_usb_performance_write(self,packets_per_train=1000,nr_trains=1000,test_cru=True,test_rdo=True):
        self.logger.info("Test USB Performance: Write")
        assert test_cru or test_rdo, "At least CRU or RDO must be set to True"
        if test_cru and test_rdo:
            packet_range = range(packets_per_train//2 - 2)
        else:
            packet_range = range(packets_per_train - 1)
        start = time.time()
        for i in range(nr_trains):
            for j in packet_range:
                if test_cru:
                    self.cru.master.write(3,False)
                if test_rdo:
                    self.cru.master.write(3,False)
            if test_cru:
                self.cru.read(0x41,1,False)
            if test_rdo:
                self.rdo.read(1,1,False)
            self.cru.flush()
            results = self.cru.read_all()
            if len(results) != test_rdo + test_cru:
                self.logger.error("Train %d: Read synchronisation not received: %d/%d",i,len(results),packets_per_train)
        end = time.time()
        duration = end-start
        mbit_sent = packets_per_train*nr_trains*32/(1024*1024)
        data_rate = mbit_sent/duration
        self.logger.info("Test finished in %.4f seconds. Raw data rate (Send/Receive): %.4f Mbps", duration,data_rate)

        self.logger.info("Test USB Performance done")

        return mbit_sent, duration

    def check_event_readout(self, nr_events,nr_empty_triggers, lanes, verbose=False, raw_data_file=None):
        return events.check_event_readout(self.cru,nr_events,nr_empty_triggers,lanes,verbose=verbose,
                                          raw_data_file=raw_data_file)

    def test_usb_endurance(self):
        TEST_PER_RUN = 30
        PRINT_INTERVAL = 10
        testlist_cru = [(65,0),(65,1)]*75
        testlist_rdo = [(3,i) for i in range(150)]
        start = time.time()
        total_transactions_rdo = 0
        total_transactions_cru = 0
        last_read = start
        try:
            while True:
                for i in range(TEST_PER_RUN):
                    for addr_cru,addr_rdo in zip(testlist_cru,testlist_rdo):
                        self.cru.read(addr_cru[0],addr_cru[1],False)
                        self.cru.read(addr_rdo[0],addr_rdo[1],False)
                    self.cru.flush()

                results = self.cru.comm.read_results()
                result_set = {}
                for addr,data in results:
                    if addr not in result_set:
                        result_set[addr] = 0
                    result_set[addr] += 1
                # check nr of transactions
                for mod,addr in testlist_cru[0:2]:
                    full_addr = (mod<<8)|addr
                    total_transactions_cru += result_set[full_addr]
                    assert result_set[full_addr] == 75*TEST_PER_RUN, "Address {0:04X}: nr. Result mismatch".format(full_addr)
                for mod,addr in testlist_rdo:
                    full_addr = (mod<<8)|addr
                    total_transactions_rdo += result_set[full_addr]
                    assert result_set[full_addr] == TEST_PER_RUN, "Address {0:04X}: nr. Result mismatch".format(full_addr)

                if(time.time() - last_read) > PRINT_INTERVAL:
                    last_read = time.time()
                    self.logger.info("Total Transactions: {0:.3e} RDO, {1:.3e} CRU. Runtime: {2:.2f}s".format(total_transactions_rdo,
                                                                                       total_transactions_cru,
                                                                                       last_read-start))
        except Exception as e:
            self.logger.info("Test stopped with %s", e)
            self.logger.info("Total Transactions: {0:.3e} RDO, {1:.3e} CRU. Runtime: {2:.2f}s".format(total_transactions_rdo,
                                                                                          total_transactions_cru,
                                                                                          last_read-start))
    def monitor_gbtx_lock_loss(self,intervall=600,Test=False):
        cnt = 0
        while True:
            lock_loss = self.rdo.read(8,28)
            if lock_loss or Test:
                #reset
                self.rdo.write(8,28,1)
                #print
                cnt += 1
                msg = "{0} : Loss of Lock encountered: Nr, {1}".format(datetime.utcnow(),cnt)
                print(msg)
                with open("loss_lock.txt",'a') as f:
                    f.write(msg + "\n");
                time.sleep(intervall)

    def test_usb_rdo_read(self):
        TEST_PER_RUN = 3000
        PRINT_INTERVAL = 10
        testlist_rdo = [(2,3), (4,1), (4,2)]
#        for i in range(2,0xC):
#            testlist_rdo.append( (8,i) )
#            testlist_rdo.append( (9,i) )
        start = time.time()
        total_transactions_rdo = 0
        total_transactions_cru = 0
        last_read = start
        WRITE_VAL = 0xAAAA

        data_mismatch = collections.defaultdict(int)

        for mod,addr in testlist_rdo:
            self.cru.write(mod,addr,WRITE_VAL)

        try:
            while True:
                for i in range(TEST_PER_RUN):
                    for addr_rdo in testlist_rdo:
                        self.cru.read(addr_rdo[0],addr_rdo[1],False)
                    self.cru.flush()

                results = self.cru.comm.read_results()
                result_set = collections.defaultdict(int)
                for addr,data in results:
                    result_set[addr] += 1
                    if data != WRITE_VAL:
                        data_mismatch[addr] += 1
                        self.logger.info("Address %04x, Mismatch. Value read: %04x",addr,data)
                # check nr of transactions
                for mod,addr in testlist_rdo:
                    full_addr = (mod<<8)|addr
                    total_transactions_rdo += result_set[full_addr]
                    assert result_set[full_addr] == TEST_PER_RUN, "Address {0:04X}: nr. Result mismatch".format(full_addr)

                if(time.time() - last_read) > PRINT_INTERVAL:
                    last_read = time.time()
                    self.logger.info("Total Transactions: {0:.3e} RDO, {1:.3e} CRU. Runtime: {2:.2f}s".format(total_transactions_rdo,
                                                                                       total_transactions_cru,
                                                                                       last_read-start))
                    for addr, mismatch in data_mismatch.items():
                        if mismatch > 0:
                            self.logger.info("Address %04x, Mismatch count: %d",addr,mismatch)
        except Exception as e:
            self.logger.info("Test stopped with %s", e)
            self.logger.info("Total Transactions: {0:.3e} RDO, {1:.3e} CRU. Runtime: {2:.2f}s".format(total_transactions_rdo,
                                                                                          total_transactions_cru,
                                                                                          last_read-start))

    def test_sca_endurance(self):
        TEST_PER_RUN = 30
        PRINT_INTERVAL = 10
        start = time.time()
        total_tests = 0
        last_read = start
        try:
            while True:
                for i in range(TEST_PER_RUN):
                    adc_vals = self.cru.read_adcs()
                    gpio_vals = self.cru.sca.read_gpio()
                    total_tests += 1

                if(time.time() - last_read) > PRINT_INTERVAL:
                    last_read = time.time()
                    self.logger.info("Number of Tests: %d", total_tests)
        except Exception as e:
            self.logger.info("Test stopped with %s", e)
            self.logger.info("Number of Tests: %d", total_tests)


    def test_microprocessor_arch(self):
        NUMBER_REGS = 12
        try:
            while True:
                counters = self.cru.get_microprocessor_counters(NUMBER_REGS)
                for i in range(NUMBER_REGS):
                    print("Micro Reg {0}:\t {1}".format(i, counters[i]))
        except Exception as e:
            self.logger.info("Test stopped with %s", e)
            self.logger.info("Number of Tests: %d", total_tests)


if __name__ == "__main__":
    STANDALONE_RUN = True
    tb = Testbench()
    try:
        fire.Fire(tb)
    except:
        raise
    finally:
        tb.stop()
