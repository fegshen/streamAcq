# streamAcq
`StreamAcq` is a simple acquisition software in upper computer sides designed for **capturing, showing, saving, and processing** streaming sensor data in real-time. 

Many sensors work on streaming/online data, such as temperature, humidity, gyroscope, or physiological electrical signals. In most cases, a single chip microcomputer or a slave computer is connected to these sensors and sends collected data to an upper computer (or a server) through specific communication protocols like Serial or Bluetooth. It is necessary to show these data in real-time sometimes. 

`StreamAcq` can provide a general and easy-to-use visualization solution for sensor data without coding.

## Features
- Extensible acquisition interface (Now only support Serial)
- Save as CSV files
- Automatically calculate sample rate
- Interact with the lower computer
- Scalable and handy user-defined real time processing (This is an advanced feature but only requiring a few coding)

## Requirements
<table>
<tr>
  <td>Package</td>
  <td>
    <img src="https://img.shields.io/badge/python-3.11|3.12-blue" />
  </td>
  <td>
    <img src="https://img.shields.io/badge/bokeh-3.3.4-blue" />
  </td>
  <td>
    <img src="https://img.shields.io/badge/pyserial-3.5-blue" />
  </td>
  <td>
    <img src="https://img.shields.io/badge/pyserial_asyncio-0.6-blue" />
  </td>
  <td>
    <img src="https://img.shields.io/badge/toml-0.10.2-blue" />
  </td>
</tr>
</table>
Other versions may also work but without test.

## How to use
Follow these steps to run the project on your local machine:
1. To run the project locally, first **clone** this repository to your local machine.
    For example:

    ```bash
    git clone https://github.com/fegshen/streamAcq.git
    ```

2. After cloning the repository, **enter the folder** that contains the repository contents:
   ```bash
    cd streamAcq
   ```

3. User needs to install required packages and then **start** the software by running `main.py`:
   ```bash
    pip install bokeh, pyserial, pyserial_asyncio, toml
    python main.py
   ```
   
4. When open the software for the first time, a configuration web page will automatically open, like this
   
   ![image](https://github.com/fegshen/streamAcq/assets/32871840/e4888134-3009-4c81-9d51-a4512102e956)

   - `Transport Protocol`: Now only support Serial (which is a common choice when using MCU).
   - `Ports:` The serial port used for communicating with the slave computer.
   - `Packet Header Input`: When sending multi-channel data using serial (or UART) in a MCU, the structure of data must be `Header+Ch1+Ch2+...`. I am not sure if it is a good idea without check digits but it make sense in the laboratory stage. Users should code for the MCU themselves. For example, you can take two bytes like `0x01 0x02` as the `Header`, then in `Packet Header Input` you should use abbreviated hexadecimal `0x0102`.
   - `Enter the number of channels`: The number of the channels determine the number of rows in the table, where the content can be modified by double clicking the entry. `Chname` is the name of each channel. It should be unique string for different channels, otherwise it might be interpreted as the same channel (This may be userful if you want to assign different sampling rates for different channels or send multiple data frames with one header). `Dtype` is the type of the data in each channel. Although [Endian](https://en.wikipedia.org/wiki/Endianness) can be altered for each row, it has no actual effect that only the value in the first channel is valid. You can also change `Scale` and `Offset` if ranges of data in different channels show significant discrepancy.
   - `Time Range in Figure (s)` is the time span of the abscissa in seconds.
   - `Save Prefix Name` and `Select Directory` determine the name and location of the saved file. Saved files will automatically be suffixed with time.

   Please click `Save Config` to make the configuration valid. Actually, this action will create a file named 'config.toml' in `streamAcq/utils`. if there is any bug, just remove this file and reconfigure.

5. After the configuration, just refresh the browser and you can see the line chart
  ![image](https://github.com/fegshen/streamAcq/assets/32871840/b05ec389-e784-4fd1-bfe9-ec2e4f1ca8fa)

6. If you would like to process data in real time, please see `streamAcq/processing/userProcess.py`.