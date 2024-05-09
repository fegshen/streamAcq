import asyncio
import concurrent.futures
from functools import partial
from collections import deque
import itertools

from ..utils.data_structure import AcquireData, get_data_structure, get_channels_in_group, process_ret_structure
from ..utils.config import get_config_params
from ..acquisition.acSerial import Acserial

class Processing:
    data = {
        'originalV':None,
        'originalIdx':None,
        'channel_times': []
        }
    sample_times_maps = []
    ncache = 1000
    sample_periods = []

    processed_data:list[list[tuple]] = []
    processed_dataIdx: list[list] = []
    process_pool = None
    stopped = False

    def __init__(self, data_queue, save_data_queue, process_fun = None):
        self.data_queue = data_queue
        self.process_fun = process_fun
        Processing.stopped = False
        self.save_data_queue = save_data_queue

    async def init_everything(self):
        stru = get_data_structure()
        while stru == {}:
            await asyncio.sleep(1)
            stru = get_data_structure()
        
        paras = get_config_params()
        self.nchannels = stru['nchannels']
        
        Processing.ncache = paras['ncache']
        Processing.sample_times_maps = stru['sample_times_maps']

        self.need_time = []

        Processing.data['originalV'] = [deque(maxlen=Processing.ncache) for _ in range(stru['nchannels'])]
        Processing.data['originalIdx'] = [0] * self.nchannels

        j = 0
        for i in stru['sample_times_maps']:
            if i >= j:
                Processing.data['channel_times'].append(deque(maxlen=Processing.ncache))
                j += 1
                self.need_time.append(True)
            else:
                self.need_time.append(False)

        # idx of the maximum sampling rate
        self.maxsamp_idx = 0
        for i,channel_span in enumerate(stru['channels_struct']):
            if channel_span[1] - channel_span[0] > stru['channels_struct'][self.maxsamp_idx][1]-stru['channels_struct'][self.maxsamp_idx][0]:
                self.maxsamp_idx = i

        # initialize the period
        self.sample_periods = [0] *  len(Processing.data['channel_times'])
        Processing.sample_periods = self.sample_periods #weak reference
        
        # ----------------------------------------------------------
        # user-processing data structure
        usr_pro_stru = process_ret_structure()
        Processing.processed_data = [
            [(deque(maxlen=Processing.ncache),deque(maxlen=Processing.ncache)) for _ in s['output_channel_name']] 
            for s in usr_pro_stru]
        Processing.processed_dataIdx = [
            [0 for _ in s['output_channel_name']]
            for s in usr_pro_stru
        ]
        self.usr_pro_stru = usr_pro_stru
        self.dque_need_process = [
            asyncio.Queue(maxsize=Processing.ncache) for _ in usr_pro_stru 
        ]


    def get_data(channels = [0], afteridx = 0):
        """
        Thread-save routine for getting data.
        
        Paraments
        ---------
        channels: list[int]
            The sample frequency in channels must be the same
        afteridx: int
            getting all data after `afteridx`, which is the number of the whole received data

        Return
        -----
        data, data_time:milliseconds-since-epoch, index of the next data
        """
        last_n = Processing.data['originalIdx'][channels[0]]
        ncache = min(Processing.ncache, last_n) # the length of data in deque
        sample_times_maps = Processing.sample_times_maps

        ret = []

        for channel in channels:
            tmp_data = Processing.data['originalV'][channel]
            ret.append(
                list(itertools.islice(tmp_data, max(ncache - last_n + afteridx, 0), ncache))
            )
        
        time_pos = sample_times_maps[channels[0]]
        ret_times = list(itertools.islice(Processing.data['channel_times'][time_pos], max(ncache - last_n + afteridx, 0), ncache))

        return ret, ret_times, last_n
    
    def get_user_processed_data(class_idx, channel_idx ,afteridx = 0):
        """
        Thread-save routine for getting data.
        
        Paraments
        ---------
        class_idx: int
        channel_idx: int
        afteridx: int
            getting all data after `afteridx`, which is the number of the whole received data

        Return
        -----
        data, data_time:milliseconds-since-epoch, index of the next data
        """
        last_n = Processing.processed_dataIdx[class_idx][channel_idx]
        ncache = min(Processing.ncache, last_n) # the length of data in deque

        tmp_data = Processing.processed_data[class_idx][channel_idx]
        ret_times = list(itertools.islice(tmp_data[0], max(ncache - last_n + afteridx, 0), ncache))
        ret = list(itertools.islice(tmp_data[1], max(ncache - last_n + afteridx, 0), ncache))

        return ret, ret_times, last_n

    async def process(self):
        # init
        await self.init_everything()
        # start user-defined processor
        self._start_usr_processor()

        # for user-processing module
        res_data = [ [([],[]) for _ in stru]
                    for stru in self.usr_pro_stru]
        
        # for saver module
        sample_times_maps = Processing.sample_times_maps
        gropus = get_channels_in_group(sample_times_maps)        
        tmp_idx = [0] *  len(Processing.data['channel_times'])
        tmpmax_idx = 0

        t_i = 0
        while not Processing.stopped:
            # assemble receiving data
            values = await self.data_queue.get()
            each_fram = self._adaptive_concatenate(values)

            # send to saver module
            if Processing.data['originalIdx'][self.maxsamp_idx] - tmpmax_idx > min(
                Processing.ncache / 2, 1000/(self.sample_periods[sample_times_maps[self.maxsamp_idx]]+1e-7)
                ):
                save_struct = []
                for i in range(len(tmp_idx)):
                    ret, ret_times, last_n = Processing.get_data(gropus[i],tmp_idx[i])
                    tmp_idx[i] = last_n
                    save_struct.append((ret_times,ret))

                self.save_data_queue.put(save_struct)
                tmpmax_idx = Processing.data['originalIdx'][self.maxsamp_idx]

            # update the sampling rate
            t_i += 1
            if t_i%20 == 0:
                await self.update_sample_periods()

            # send data to the user-defined processing
            new_data, res_data = self._assembel_user_process_data(each_fram, res_data)
            for each_data,each_dq in zip(new_data,self.dque_need_process):
                if each_data is not None:
                    await each_dq.put(each_data)

    def _adaptive_concatenate(self, values:AcquireData):
        each_fram = []
        for i in range(self.nchannels):
            ch_data = values.list_channels[i]
            Processing.data['originalV'][i].extend(ch_data)
            n_tmp = len(ch_data)
            Processing.data['originalIdx'][i] += n_tmp

            tmp_i = Processing.sample_times_maps[i]
            if self.need_time[i]:
                ch_time = [values.time*1000 + i*self.sample_periods[tmp_i] for i in range(n_tmp)] # milliseconds-since-epoch
                Processing.data['channel_times'][tmp_i].extend(
                    ch_time
                )

                each_fram.append([ch_time,ch_data])
            else:
                each_fram.append([each_fram[tmp_i][0],ch_data])
        
        return each_fram
            

    async def update_sample_periods(self):
        for i in range(len(self.sample_periods)):
            tmp = Processing.data['channel_times'][i]
            if len(tmp)>1:
                self.sample_periods[i] = 0.1*self.sample_periods[i] + 0.9*(tmp[-1] - tmp[0]) / (len(tmp)-1)

    def _assembel_user_process_data(self, new_data, res_data):
        if new_data is not None:
            res_data = [ 
                [(r[0] + new_data[i][0],r[1] + new_data[i][1]) 
                for i,r in zip(stru['input_channels'],rd) ]
                for stru,rd in zip(self.usr_pro_stru,res_data) ]
        ret = []
        new_res_data = []
        for stru,rd in zip(self.usr_pro_stru,res_data):
            if len(rd[0][0]) >= stru["win_length"]:
                ret.append(
                    [(r[0][:stru["win_length"]],r[1][:stru["win_length"]]) for r in rd]
                )
                new_res_data.append(
                    [(r[0][stru["hop_length"]:],r[1][stru["hop_length"]:]) for r in rd]
                )
            else:
                ret.append(None)
                new_res_data.append(rd)
        
        return ret, new_res_data
    
    async def _call_user_processing(self, 
                                    pool:concurrent.futures.ProcessPoolExecutor, 
                                    data_queue:asyncio.Queue, 
                                    fun,
                                    processed_data:list[tuple[deque]],
                                    processed_dataidx:list[int]):
        loop = asyncio.get_running_loop()
        while not Processing.stopped:
            data = await data_queue.get()
            # # user-defined complex function will be called in another process
            result_data = await loop.run_in_executor(
                pool, partial(fun,data,Acserial.write_to_sensor))
            
            for i,d in enumerate(result_data):
                processed_dataidx[i]+=len(d[0])
                processed_data[i][0].extend(d[0])
                processed_data[i][1].extend(d[1])


    def _start_usr_processor(self):
        print('number of workers for usr-defined processing:', min(len(self.usr_pro_stru),4))
        if len(self.usr_pro_stru) > 0:
            usr_pro_stru = self.usr_pro_stru # process_ret_structure()
            process_pool = concurrent.futures.ProcessPoolExecutor(max_workers=min(len(usr_pro_stru),4))
            Processing.process_pool = process_pool

            self.user_tasks = []
            for us,data_queue,processed_data,processed_dataidx in zip(usr_pro_stru,self.dque_need_process,Processing.processed_data,Processing.processed_dataIdx):
                fun = us['class']()
                self.user_tasks.append(
                    asyncio.create_task(self._call_user_processing(
                        process_pool, data_queue, fun, processed_data, processed_dataidx
                    ))
                )


    def start(self):
        Processing.stopped = False
        # acquisation and saver
        self.task = asyncio.create_task(self.process())

    def stop():
        Processing.stopped = True
        if Processing.process_pool is not None:
            Processing.process_pool.shutdown(wait=False)


def shutdown(loop, executor):
    executor.shutdown()
    for task in asyncio.Task.all_tasks():
        task.cancel()
    loop.stop()