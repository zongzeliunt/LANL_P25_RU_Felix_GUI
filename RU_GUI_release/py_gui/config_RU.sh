./testbench1.py rdo i2c-gbtx gbtx-config ../../modules/gbt/software/GBTx_configs/GBTx0_Config_RUv1_1.xml
#./testbench2.py rdo i2c-gbtx gbtx-config ../../modules/gbt/software/GBTx_configs/GBTx0_Config_RUv1_1.xml
./testbench1.py rdo dctrl set-dclk-mask 0; 
#./testbench2.py rdo dctrl set-dclk-mask 0
#./testbench1.py powerunit initialize
#./testbench1.py powerunit setup-power-IBs 1.8 1.5 1.8 1.5 0 None [0,1,2,3]
#./testbench1.py powerunit power-on-IBs [0,1,2,3]
./testbench1.py rdo dctrl set-dclk-mask 0x1f; 
#./testbench2.py rdo dctrl set-dclk-mask 0x1f
./testbench1.py setup_sensors
#./testbench2.py setup_sensors
./testbench1.py setup_readout 
#./testbench2.py setup_readout
