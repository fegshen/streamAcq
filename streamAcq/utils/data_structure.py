"""
Define the structure of the data in different processes.
"""
from .config import read_config
from ..processing import userProcess as up

class AcquireData:
    def __init__(self, list_channels: list[list], time: float):
        """
        Data from different channels should be splited into different list 
        so that they can have distinct lengths to meet different sampling rates.
        """
        self.list_channels = list_channels
        self.time = time

class DataStructure:
    stru = {}
    dtype_to_fea ={
        'signed char(1)':[1,'b'], 
        'unsigned char(1)':[1,'B'],
        'short(2)':[2,'h'],
        'unsigned short(2)':[2,'H'],
        'int(4)':[4,'i'],
        'unsigned int(4)':[4,'I'],
        'long long(8)':[8,'q'],
        'unsigend long long(8)':[8,'Q'],
        'float(4)':[4,'f'],
        'double(8)':[8,'d']
    }

    def update():
        config = read_config()
        if config['serial'] == {}:
            return

        head = config['serial']['head']
        DataStructure.stru['headpattern'] = int(head,16).to_bytes(length=int((len(head)-2)/2), byteorder='big')

        nbytesl = [DataStructure.dtype_to_fea[dtype][0] for dtype in config['serial_chsource']["dtype"]]
        unpackl = [DataStructure.dtype_to_fea[dtype][1] for dtype in config['serial_chsource']["dtype"]]

        DataStructure.stru['nbytes_frame'] = sum(nbytesl) + len(DataStructure.stru['headpattern'])
        if config['serial_chsource']['endian'][0] == 'big':
            DataStructure.stru['unpack'] = '!' + ''.join(unpackl)
        else:
            DataStructure.stru['unpack'] = ''.join(unpackl)
        
        name_channels = []
        channels_struct = []
        scale,offset=[],[]
        for i, chname in enumerate(config['serial_chsource']['chname']):            
            if chname in name_channels and chname == name_channels[-1]:
                channels_struct[-1][1] += 1
            else:
                name_channels.append(chname)
                channels_struct.append([i,i+1])
                scale.append(config['serial_chsource']['scale'][i])
                offset.append(config['serial_chsource']['offset'][i])
        DataStructure.stru['name_channels'] = name_channels
        DataStructure.stru['channels_struct'] = channels_struct
        DataStructure.stru['nchannels'] = len(name_channels)

        sample_times_maps = []
        diffs = []
        idx = 0
        for dif in [cs[1]-cs[0] for cs in channels_struct]:
            if dif not in diffs:
                diffs.append(dif)
                sample_times_maps.append(idx)
                idx += 1
            else:
                diffs.append(dif)
                sample_times_maps.append(sample_times_maps[diffs.index(dif)])
        DataStructure.stru['sample_times_maps'] = sample_times_maps
        DataStructure.stru['scale'] = scale
        DataStructure.stru['offset'] = offset
        

def get_data_structure():
    # stru = {
    #     'pattern': b'\x01\x02',
    #     'nbytes_frame': 18, # bytes each frame (with head data)
    #     'unpack': "!ffff",
    #     'nchannels': 3,
    #     'name_channels': ['ch1','ch2','ch3'],
    #     'channels_struct': [[0,2],[2,3],[3,4]],
    #     'sample_times_maps': [0,1,1]
    # }
    return DataStructure.stru

def get_channels_in_group(sample_times_maps):
    gropus = []
    for i in range(len(set(sample_times_maps))):
        gs = []
        for j,j_v in enumerate(sample_times_maps):
            if i == j_v: gs.append(j)
        gropus.append(gs)

    return gropus

def process_ret_structure():
    """similar to `get_data_structure` with the data structure of user porcesses"""
    strus = []
    for k in dir(up):
        if k.startswith("process_") and type(getattr(up,k)) is type:
            stru = {}
            stru['classname'] = k
            stru['class'] = getattr(up,k)
            stru['hop_length'] = getattr(stru['class'],'hop_length')
            stru['win_length'] = getattr(stru['class'],'win_length')
            stru['input_channels'] = getattr(stru['class'],'input_channels')
            stru['output_channel_name'] = getattr(stru['class'],'output_channel_name')
            strus.append(stru)
    return strus
    
