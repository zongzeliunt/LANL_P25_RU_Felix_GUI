open_hw
connect_hw_server
#open_hw_target [lindex [get_hw_targets -of_objects [get_hw_servers localhost]] 0]
open_hw_target [lindex [get_hw_targets] 0]
puts [lindex $argv 0]
set_property PROGRAM.FILE [lindex $argv 0] [lindex [get_hw_devices] 0]
#set_property PROBES.FILE {} [lindex [get_hw_devices] 0]
current_hw_device [lindex [get_hw_devices] 0]
#refresh_hw_device [lindex [get_hw_devices] 0]
program_hw_devices [lindex [get_hw_devices] 0]
#refresh_hw_device [lindex [get_hw_devices] 0]
close_hw_target
disconnect_hw_server
close_hw
