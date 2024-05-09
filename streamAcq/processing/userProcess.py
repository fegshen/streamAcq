from typing import Callable

"""
Every class with prefix 'process_' is the user defined process to handle real-time signal.
Users need to implement the magic method '__call__' with two parameters `data` and `write_to_sensor`, where
`data` is the real-time signal which must be in a short-time window, `write_to_sensor` is a function with an input 
whose tpye is 'bytes | bytearray | memoryview' thus can be used to send data to sensor.

Every class with prefix 'process_' should have the following class variables:
`win_length`: number of points in each window
`hop_length`: number of points between any two adjacent short-time windows
`input_channels`: channels that would be processed
`output_channel_name`: the name of output, which also determines the number of output channels
"""

# Example 1: mean filters
# uncomment to enable the example
"""
class process_meanfilter:
    hop_length = 10
    win_length = 12
    input_channels = [0,1]
    output_channel_name = ['mean_0','mean_1','mean_0_1']

    def __init__(self) -> None:
        pass
    
    def __call__(self, data:list[tuple[list,list]], write_to_sensor:Callable) -> list[tuple[list,list]]:
        time_ch0, data_ch0 = data[0]
        time_ch1, data_ch1 = data[1]

        ret_ch0 = [sum(k)/3 for k in zip(data_ch0[:-2],data_ch0[1:-1],data_ch0[2:])]
        rettime_ch0 = time_ch0[1:-1]

        ret_ch1 = [sum(k)/3 for k in zip(data_ch1[:-2],data_ch1[1:-1],data_ch1[2:])]
        rettime_ch1 = time_ch1[1:-1]

        ret_add = [sum(k)/2 for k in zip(data_ch0[1:-1],data_ch1[1:-1])]
        rettime_add = rettime_ch0

        return [(rettime_ch0,ret_ch0),(rettime_ch1,ret_ch1),(rettime_add,ret_add)]
"""