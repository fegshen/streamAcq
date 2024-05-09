from threading import Thread
import asyncio
import queue

from .acquisition.acSerial import Acserial
from .processing.interface import Processing
from .processing.saving import Saving
from .utils.data_structure import DataStructure

def on_server_loaded(server_context):
    print('server running...')

    DataStructure.update()
    
    async def run_acquisition(save_data_queue):
        data_queue = asyncio.Queue(maxsize=1000)
        acq = Acserial(data_queue)
        pro = Processing(data_queue,save_data_queue)
        acq.start()
        pro.start()
        
        await acq.task
        await pro.task
        

    def thread_acq_fun(save_data_queue):
        asyncio.run(run_acquisition(save_data_queue))

    save_data_queue = queue.SimpleQueue()
    t = Thread(target=thread_acq_fun, args=(save_data_queue,))
    t.setDaemon(True)
    t.start()

    saver = Saving(save_data_queue)
    t1 = Thread(target=saver.runnig_forever, args=())
    t1.setDaemon(True)
    t1.start()
    