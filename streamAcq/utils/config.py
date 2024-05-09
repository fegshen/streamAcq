import random
import toml
from os.path import join, dirname,exists

def read_config():
    ret = {
        'global':{},
        'serial':{}
    }
    
    if not exists(join(dirname(__file__),'config.toml')):
        return ret

    with open(join(dirname(__file__),'config.toml'), 'r') as f:
        ret.update(toml.load(f))
    return ret

def write_config(save_dict):
    with open(join(dirname(__file__),'config.toml'), 'w') as f:
        toml.dump(save_dict, f)

def get_config_params():
    '''addtional params will be added'''
    stru = {
        'ncache': 1000,
        'save_dir': "",
        'save_prefix_name':""
    }

    ret = read_config()
    stru['save_dir'] = ret['global'].get('save_dir',"")
    stru['save_prefix_name'] = ret['global'].get('save_prefix_name',"")
    stru['tplot'] = ret['global'].get('tplot', 20) # the time range in the plots with second as unit 

    if ret['serial'] != {}:
        stru.update(ret['serial'])

    return stru

random.seed(0)
def RandomColor():
    c1 = random.randint(16,255)
    c2 = random.randint(16,255)
    c3 = random.randint(16,255)
    return '#' + hex(c1)[2:] + hex(c2)[2:] + hex(c3)[2:]

colors = [RandomColor() for _ in range(100)]

def getLineColor(channel:int):
    return colors[channel%100]