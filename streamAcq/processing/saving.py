import queue
import os, time
from ..utils.data_structure import get_data_structure, get_channels_in_group
from ..utils.config import get_config_params

class Saving:
    _stop_sig = True
    _file = None

    def __init__(self, data_queue:queue.SimpleQueue):
        self.data_queue = data_queue

    def runnig_forever(self):
        while True:
            data = self.data_queue.get()

            if not Saving._stop_sig:
                self.save_to_file(data)
            elif Saving._file is not None:
                Saving._file = None

    def stop():
        Saving._stop_sig = True

    def start():
        params = get_config_params()
        _save_dir = params['save_dir']
        if os.path.exists(_save_dir):
            Saving._file = File(_save_dir, params['save_prefix_name'])
            Saving._stop_sig = False
        else:
            Saving._file = None
            Saving._stop_sig = True

    def save_to_file(self, data):
        if self._file is None:
            return
        Saving._file.write(data)
            
    def __del__(self):
        Saving._file = None

class File:
    def __init__(self, save_dir, save_prefix_name):
        stru = get_data_structure()
        gropus = get_channels_in_group(stru['sample_times_maps'])
        save_prefix_name = save_prefix_name if save_prefix_name =='' else save_prefix_name + '-'

        # create file
        file_sub = save_prefix_name + time.strftime('%Y-%m-%d-%H-%M-%S',time.localtime(time.time()))
        if len(gropus) == 1:
            self.filestreams = [open(os.path.join(save_dir, file_sub + '.csv'), 'w+')]
        else:
            self.filestreams = []
            if not os.path.exists(os.path.join(save_dir, file_sub)):
                os.mkdir(os.path.join(save_dir, file_sub))
            for g in gropus:
                self.filestreams.append(open(os.path.join(save_dir, file_sub, '-'.join(map(str,g))+'.csv'), 'a'))

        # init contents
        for i,g in enumerate(gropus):
            self.filestreams[i].write("time,"+ ",".join([stru['name_channels'][ci] for ci in g]) + "\n")
            self.filestreams[i].flush()

    def write(self, data):
        for fstream, each_data in zip(self.filestreams, data):
            period = (each_data[0][-1] - each_data[0][0])/(len(each_data[0])-1+1e-8)
            timestamps = [each_data[0][0]+i*period for i in range(len(each_data[0]))]

            each_data[1].insert(0, timestamps)
            L = list(map(list,zip(*each_data[1])))
            fstream.writelines(self.list_to_str(L))
            fstream.flush()
            os.fsync(fstream.fileno())
    
    def __del__(self):
        for fstream in self.filestreams:
            fstream.close()

    def list_to_str(self, ll):
        """must be a two dimentional list, the first is the time (milliseconds-since-epoch)"""
        return [
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(l[0]/1000)) + f".{int((l[0] % 1000) * 100):05d}," +\
            ",".join(map(str,l[1:])) + "\n"
            for l in ll
            ]