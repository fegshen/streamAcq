from os.path import dirname, join
from bokeh.models import Div, ColumnDataSource,CustomJS
from bokeh.layouts import column, row
from bokeh.models import Button, TextInput
from bokeh.models import Select, InlineStyleSheet
from bokeh.models import NumericInput, DataTable, TableColumn,SelectEditor,NumberEditor
from bokeh.models import PreText

from tkinter import Tk
from tkinter.filedialog import askdirectory

from ..utils.config import write_config,read_config
from ..utils.data_structure import DataStructure
from ..acquisition.acSerial import get_all_serial_ports

class PageConfig:
    def __init__(self) -> None:
        '''
        construct the layout and the Widgets
        '''
        self.config_dict = read_config()

        # discription
        filename = join(dirname(__file__), "description_config.html")
        desc = Div(text=open(filename).read(), render_as_text=False,align ='center')
        self.stylesheet = InlineStyleSheet(css="""
            :host(.invalid-input) {
                color: red;
                border: 1px solid red!important;
                outline: none;
            }
            """)

        # select which communication is used
        trans = self.config_dict['global'].get('select_trans','Serial')
        self.select_trans = select_trans= Select(
            title="Transport Protocol:", value=trans,
            options=["Serial", "Bluetooth", "INET"])
        select_trans.on_change("value",self._select_transport_on_change_callback)

        self.serial_config = serial_config = self.__create_serial_config()
        self.bt_config = bt_config = self.__create_bluetooth_config()
        self.inet_config = inet_config = self.__create_inet_config()
        self._select_transport_on_change_callback(None,None,trans)

        # separator
        separator = Div(text="<hr><p>The configruation below can only be edited in browser of the same computer running the sever. </p>")
        self.server_config = server_config = self.__create_server_config()

        self.tplot_input = tplot_input = self.__create_plot_config()

        self.page = column([
            desc, select_trans, serial_config, bt_config, inet_config,
            separator,
            tplot_input,
            server_config
            ],sizing_mode="stretch_both")

    def __call__(self):
        return self.page
    
    def _select_transport_on_change_callback(self, attr, old, new):
        if new == 'Serial':
            self.serial_config.visible = True
            self.bt_config.visible = False
            self.inet_config.visible = False
        elif new == 'Bluetooth':
            self.serial_config.visible = False
            self.bt_config.visible = True
            self.inet_config.visible = False
        elif new == 'INET':
            self.serial_config.visible = False
            self.bt_config.visible = False
            self.inet_config.visible = True
        
    def _ch_num_on_change_callback(self, attr, old, new):
        if new is None:
            return
        
        data = self.chsource.data
        old = len(data['chname'])

        if new > old:
            # add
            newdata = dict(
                chname =[data['chname'][-1]+'_'+str(i) for i in range(new-old)],
                dtype = [data['dtype'][-1]] * (new-old),
                endian = [data['endian'][-1]] * (new-old),
                scale = [data['scale'][-1]] * (new-old),
                offset = [data['offset'][-1]] * (new-old)
            )
            self.chsource.stream(newdata)
        elif old > new:
            # del
            for key in data.keys():
                del(data[key][new-old:])
            self.chsource.data = data.copy()
    
    def __create_serial_config(self):
        self.input_head = input_head = TextInput(
            placeholder="Enter hexadecimal value:", title="Packet Header Input",
            stylesheets=[self.stylesheet], value = self.config_dict['serial'].get('head','')
            )
        input_head.js_on_change('value', CustomJS(code="""
            const input = cb_obj.value;
            const pattern = /^0[xX]([0-9a-fA-F]{2})*$/;
            const isValid = pattern.test(input);
            if (!isValid && input!="") {
                cb_obj.title = "Invalid input (hexadecimal started with 0x required)";
                cb_obj.css_classes = ["invalid-input"];
            }else{
                cb_obj.title = "Packet Header Input:";
                cb_obj.css_classes = [];
            }
        """))
        self.input_num_ch = input_num_ch = NumericInput(
            value = self.config_dict['serial'].get('num_ch',1),
            low=1, high=100, title="Enter the number of channels:")
        input_num_ch.on_change("value", self._ch_num_on_change_callback)

        self.all_ports = get_all_serial_ports()
        self.serial_select_port = serial_select_port = Select(
            title="Ports:", 
            value = self.get_serial_name_from_port(
                self.config_dict['serial'].get('serial_port',self.all_ports[0][0])
                ),
            options=[port[1] for port in self.all_ports])
        self.serial_input_baudrate = serial_input_baudrate = NumericInput(
            value=self.config_dict['serial'].get('serial_baudrate',9600), low=1, title="Baudrate:")
        self.serial_select_bytesize = serial_select_bytesize =  Select(
            title="Bytesize:", value=str(self.config_dict['serial'].get('serial_bytesize','8')), options=['8'])
        self.serial_select_stopbits = serial_select_stopbits = Select(
            title="Stopbits:", value=str(self.config_dict['serial'].get('serial_stopbits','1')), options=['1','2'])

        data = self.config_dict.get(
            'serial_chsource',
            dict(
                chname=['ch1'],
                dtype=['float(4)'],
                endian = ['big'],
                scale = [1.0],
                offset = [0.0]
            )
        ) 
        self.chsource = ColumnDataSource(data)
        columns = [
            TableColumn(field="chname", title="Chname"),
            TableColumn(field="dtype", title="Dtype", editor=SelectEditor(options=[
                'signed char(1)', 'unsigned char(1)','short(2)','unsigned short(2)',
                'int(4)', 'unsigned int(4)', 'long long(8)','unsigend long long(8)',
                'float(4)', 'double(8)'
                ])),
            TableColumn(field="endian", title="Endian",editor=SelectEditor(options=['big','small'])),
            TableColumn(field="scale", title="Scale", editor=NumberEditor()),
            TableColumn(field="offset", title="Offset", editor=NumberEditor())
        ]
        data_table = DataTable(source=self.chsource, columns=columns, editable=True,sizing_mode="stretch_height")

        return column([
            row([serial_select_port,serial_input_baudrate,serial_select_bytesize,serial_select_stopbits]),
            row([input_head,input_num_ch]),
            data_table
            ],sizing_mode="stretch_both")
    
    def __create_bluetooth_config(self):
        separator = Div(text="<hr><p>Coming soon.. </p>")
        return separator
    
    def __create_inet_config(self):
        separator = Div(text="<hr><p>Coming soon.. </p>")
        return separator
    
    def __create_plot_config(self):
        tplot_input = NumericInput(
            value=self.config_dict['global'].get('tplot',20), low=1, title="Time Range in Figure (s):")
        return tplot_input
        
    
    def __create_server_config(self):
        # save directory
        self.selected_path_tf = selected_path_tf = PreText(
            align='end',
            text = self.config_dict['global'].get('save_dir','')
            )
        def _dir_input_btn_on_push_callback():
            root = Tk()
            root.attributes('-topmost', True)
            root.withdraw()
            dirname = askdirectory()  # blocking
            if dirname:
                selected_path_tf.text = dirname

        dir_input_btn = Button(label="Select Directory",align='end')
        dir_input_btn.on_click(lambda x: _dir_input_btn_on_push_callback())
        # save dictory prefix-name
        self.dir_pretext_input = TextInput(value=self.config_dict['global'].get('save_prefix_name',''), title="Save Prefix Name")

        # save button
        self.ok_button_tf = ok_button_tf = PreText(align='end')
        ok_button_tf.styles = {'color': 'blue'}
        ok_button = Button(label="Save Config", button_type="success")
        ok_button.on_click(lambda x:self.__ok_button_on_push_callback())

        return column([
            row([self.dir_pretext_input, dir_input_btn,selected_path_tf]),
            row([ok_button,ok_button_tf])
        ])
    

    def __ok_button_on_push_callback(self):
        # check the valid of the input
        if self.input_head.value == '' and self.input_num_ch.value != 1:
            self.input_head.title = "Invalid input (only number of channels equal one can support the none-head)"
            self.input_head.css_classes = ["invalid-input"]
            self.ok_button_tf.text = ""
            return
        
        config_dict = {
            'title': "streamAcq configuration using Toml",
            'global': {
                "select_trans": self.select_trans.value,
                "save_dir":self.selected_path_tf.text,
                "save_prefix_name":self.dir_pretext_input.value,
                "tplot":self.tplot_input.value
            },
            'serial':{
                'head':self.input_head.value,
                'num_ch':int(self.input_num_ch.value),
                'serial_port' : self.get_port_from_serial_name(self.serial_select_port.value),
                'serial_baudrate':int(self.serial_input_baudrate.value),
                'serial_bytesize':int(self.serial_select_bytesize.value),
                'serial_stopbits':int(self.serial_select_stopbits.value),
            },
            'serial_chsource':self.chsource.data,
        }
        config_dict['serial_chsource']['scale'] = list(map(float,config_dict['serial_chsource']['scale']))
        config_dict['serial_chsource']['offset'] = list(map(float,config_dict['serial_chsource']['offset']))

        write_config(config_dict)
        
        self.ok_button_tf.text = "OK"

        # update the DataStructure
        DataStructure.update()


    def get_serial_name_from_port(self,port):
        for p,p_name in self.all_ports:
            if p==port:
                return p_name
        
        return ''
            
    def get_port_from_serial_name(self,serial_name):
        for p,p_name in self.all_ports:
            if p_name==serial_name:
                return p
            
        return ''

    