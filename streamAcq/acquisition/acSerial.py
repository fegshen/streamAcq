"""
Acquisition in serial.
"""
import asyncio
import re
import struct
import time

import serial_asyncio
from serial.tools.list_ports import comports

from .base import Acquisition
from ..utils.data_structure import AcquireData, get_data_structure
from ..utils.config import get_config_params

class Acserial(Acquisition):
    awriter = None
    
    def __init__(self, data_queue = None):
        self.data_queue = data_queue
        self.writer = None

    async def connect(self,*args,**kwds):
        """
        The arguments are all the usual arguments to serial_asyncio.open_serial_connection
        """
        self.reader, self.writer = await serial_asyncio.open_serial_connection(*args,**kwds)
        Acserial.awriter = self.writer

    def bind_to_queue(self, data_queue : asyncio.Queue):
        """
        bind the acquisition to a data_queue such that acquisition will send data into the data_queue.
        The data must be a instance from AcquireData.
        """
        self.data_queue = data_queue

    def start(self):
        """
        To start the acquisition in a asynchronous way.
        """
        self.task = asyncio.create_task(self.acquire())

    async def init_everything(self):
        stru = get_data_structure()
        while stru == {}:
            await asyncio.sleep(1)
            stru = get_data_structure()

        self.headpattern = re.compile(stru['headpattern'])
        self.nbytes_frame = stru['nbytes_frame']
        self.n = stru['nbytes_frame'] - len(stru['headpattern']) #length without head
        self.unpack = stru['unpack']
        self.n_channels = stru['nchannels']
        self.channels = stru['channels_struct']
        
        params = get_config_params()
        if params['serial_port'] == '':
            print('Serial configration is broken. Please config it again and restart the application!')
            return
        await self.connect(
            url = params['serial_port'],
            baudrate = params['serial_baudrate'],
            bytesize = params['serial_bytesize'],
            stopbits = params['serial_stopbits'],
        )


    def is_closing(self):
        """
        To check if the acquisition is running.
        """
        if self.writer is None:
            return True
        
        return self.writer.is_closing()
        

    async def stop(self):
        """
        To stop the acquisition.
        """
        self.writer.close()
        await self.task

    async def acquire(self):
        # init
        await self.init_everything()
        if self.writer is None or self.writer.is_closing():
            print('No connection!')
            return


        res_data = b''
        while True:
            rev_data = await self.reader.read(1000)
            rev_time = time.time()
            
            if rev_data == b'':
                print('The acquisition was stopped!')
                break

            data = res_data + rev_data

            values, res_data = self.parse(data)

            if len(res_data) < len(data):
                self.data_queue.put_nowait(AcquireData(values, rev_time))

    def parse(self,bdata):
        """
        To parse the data in bdata [bytes]
        """
        values = [[] for _,_ in self.channels]
        e2 = 0
        while len(bdata)>=self.nbytes_frame:

            find = self.headpattern.search(bdata)
            if find is not None:
                e1 = find.end()
                e2 = e1 + self.n
                if e2 <= len(bdata):
                    revdata = struct.unpack(self.unpack, bdata[e1:e2])

                    [values[i].extend(revdata[j[0]:j[1]]) for i,j in enumerate(self.channels)]
                    bdata = bdata[e2:]
                else:
                    break
            else:
                break
        
        return values, bdata
    
    async def write(data):
        Acserial.awriter.write(data)
        await Acserial.awriter.drain()

    def write_to_sensor(data):
        """can be called in another thread"""
        if len(data)==0:
            return
        
        loop = asyncio.get_running_loop()
        asyncio.run_coroutine_threadsafe(Acserial.write(data), loop)

def get_all_serial_ports():
    return [tuple(com)[:2] for com in comports()]