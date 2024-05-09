import signal
import time

from bokeh.server.server import Server
from bokeh.io import curdoc

from streamAcq.pages.main_page import PageMain
from streamAcq.pages.config_page import PageConfig
from streamAcq.utils.config import read_config
from streamAcq.app_hooks import on_server_loaded
from streamAcq.processing.interface import Processing

# doc = curdoc()

def bkapp(doc):
    args = doc.session_context.request.arguments

    if 'setting' in args or read_config()['global'] == {}:
        page_config = PageConfig()
        doc.add_root(page_config())
    else:
        page_main = PageMain()
        doc.add_root(page_main())
        doc.add_periodic_callback(page_main.update,100)

    doc.title = "streamAcq"
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())),"\tNew connection opened")

def signal_handler(signal, frame):
    """
    ctrl+c
    """
    print("\nInterrupted, shutting down")
    Processing.stop()
    server.io_loop.stop()

if __name__ == "__main__":
    server = Server({'/streamAcq': bkapp}, num_procs=1)
    server.start()
    on_server_loaded(curdoc().session_context)
    
    print('Opening application on http://localhost:5006/streamAcq')

    signal.signal(signal.SIGINT, signal_handler)

    server.io_loop.add_callback(server.show, "/streamAcq")
    server.io_loop.start()