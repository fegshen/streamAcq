from os.path import dirname, join
import time

from bokeh.models import Div, ColumnDataSource, MultiChoice, Tooltip, RELATIVE_DATETIME_CONTEXT,CustomJS
from bokeh.plotting import figure
from bokeh.layouts import column, row
from bokeh.models import Button, LegendItem, TextInput, Spacer, BuiltinIcon, Switch
from bokeh.models import PreText

from ..processing.interface import Processing
from ..acquisition.acSerial import Acserial
from ..utils.config import getLineColor
from ..utils.data_structure import get_data_structure, process_ret_structure
from ..utils.config import get_config_params
from ..processing.saving import Saving

class PageMain:
    def __init__(self) -> None:
        '''
        construct the layout and the Widgets
        '''

        self.PLOTARGS = dict(tools="", toolbar_location=None, outline_line_color='#595959',sizing_mode="stretch_both")
        filename = join(dirname(__file__), "description.html")
        desc = Div(text=open(filename).read(), render_as_text=False,align ='center')
        
        self.stru = stru = get_data_structure()
        self.parms = get_config_params()
        self.scale = dict(zip(self.stru['name_channels'],self.stru['scale']))
        self.offset = dict(zip(self.stru['name_channels'],self.stru['offset']))
        # construc ColumnDataSources for data with different sampling rates
        self.dataMaps = dataMaps = {}
        for idx in set(stru['sample_times_maps']):
            groups,gname_channels = [],[]
            for j in range(len(stru['sample_times_maps'])):
                if stru['sample_times_maps'][j] == idx:
                    groups.append(j)
                    gname_channels.append(stru['name_channels'][j])

            dataMaps[tuple(groups)] = [
                # data, counted number of receive data, name of each channel, number of points for plotting
                ColumnDataSource(
                    data={
                        't':[],
                        **{gname:[] for gname in gname_channels}
                    }
                ),
                0,
                gname_channels,
                1000
            ]
        noneData = ColumnDataSource(data={'t':[],**{gname:[] for gname in stru['name_channels']}})
        # construct ColumnDataSources for user's processed data
        # the structure of userProcesdataMaps is different from that of dataMaps
        self.userProcesdataMaps = userProcesdataMaps = {}
        usr_pro_stru = process_ret_structure()
        num_tmp = 0
        for i,usr_stru in enumerate(usr_pro_stru):
            userProcesdataMaps[i] = [
                [   
                # data, counted number of receive data, name, number of points for plotting, sequence number
                ColumnDataSource(
                    data={
                        't':[],
                        name:[]
                    }
                ),
                0,
                name,
                1000,
                num_tmp+j
                ]
                for j, name in enumerate(usr_stru["output_channel_name"])
            ]
            num_tmp = userProcesdataMaps[i][-1][4] + 1

        #-----------------------
        # each singal plots
        #-----------------------
        self.signal_plot = signal_plot = figure(
            width=600, height=200, x_axis_type="datetime",
            outline_line_color='#595959',sizing_mode="stretch_both") # tools="", toolbar_location=None, 
        signal_plot.xaxis.formatter.context = RELATIVE_DATETIME_CONTEXT()

        # user's processed data plot
        if len(usr_pro_stru)>0:
            self.user_signal_plot = user_signal_plot = figure(
                width=600, height=200, x_axis_type="datetime",
                outline_line_color='#595959',sizing_mode="stretch_both") # tools="", toolbar_location=None, 
            user_signal_plot.xaxis.formatter.context = RELATIVE_DATETIME_CONTEXT()
        else:
            user_signal_plot = None

        lines = [[signal_plot.line(
            x="t", y=dataMaps[key][2][j], 
            line_color = getLineColor(key[j]),
            line_width = 2,
            source=dataMaps[key][0],
            muted_alpha = 0.2,
            legend_label=dataMaps[key][2][j])
            for j in range(len(key))]
            for key in dataMaps]
        if len(usr_pro_stru)>0:
            lines += [[user_signal_plot.line(
                x="t", y=userProcesdataMaps[key][j][2],
                line_color = getLineColor(userProcesdataMaps[key][j][4]),
                line_width = 2,
                source=userProcesdataMaps[key][j][0],
                muted_alpha = 0.2,
                legend_label=userProcesdataMaps[key][j][2])
                for j in range(len(userProcesdataMaps[key]))]
                for key in userProcesdataMaps]
        
        for plot in [signal_plot, user_signal_plot]:
            if plot is not None:
                plot.legend.label_text_font = "times"
                plot.legend.label_text_font_style = "italic"
                plot.legend.label_text_color = "navy"
                # plot.legend.background_fill_color = "navy"
                plot.legend.background_fill_alpha = 0.2
                plot.legend.click_policy="mute"


        # Tooltip
        OPTIONS = sum([dataMaps[key][2] for key in dataMaps],[]) # using sum to unfold the list
        OPTIONS += sum([[up_[2] for up_ in userProcesdataMaps[key]] for key in userProcesdataMaps],[])
        OPTIONS_MAP = {
            'legends':signal_plot.legend.items + (user_signal_plot.legend.items if user_signal_plot is not None else []),
            'nonedata':noneData,
            'lines': sum(lines,[]),
            'datas': [l.data_source for l in sum(lines,[])]
        }
        tooltip_multi_choice = Tooltip(content="Choose any number of the items", position="right")
        multi_choice = MultiChoice(value=OPTIONS, options=OPTIONS, title="Choose channels:", description=tooltip_multi_choice)
        callback = CustomJS(
            args = OPTIONS_MAP,
            code = "\n const selected_chs = cb_obj.value; \n " +
            '\n '.join([f"lines[{i}].visible=selected_chs.includes('{op}');" for i,op in zip(range(len(OPTIONS)),OPTIONS)]) + '\n ' +
            '\n '.join([f"legends[{i}].visible=selected_chs.includes('{op}');" for i,op in zip(range(len(OPTIONS)),OPTIONS)]) + 
            "\n" + 
            """
            for(var i=0;i<legends.length;i++){
                if(legends[i].visible){
                    lines[i].data_source = datas[i];
                }else{
                    lines[i].data_source = nonedata;
                }
            }
            """
            )
        multi_choice.js_on_change("value", callback)

        # saving data plot
        self.saving_time_source = ColumnDataSource(data={'t':[],'lw':[]})
        signal_plot.vspan(x='t',line_width='lw',line_color="black", source = self.saving_time_source)

        # switch-save data
        pre_switch_text = "Save"
        self.switch_save = switch_save = Switch(active=not Saving._stop_sig, align='end',margin=[0,0,12,0])
        self.pre_switch = pre_switch = PreText(text=pre_switch_text,align='end')
        swtichp_save = row(
            [switch_save,pre_switch],sizing_mode="stretch_both",margin=[0,0,0,50]
        )
        switch_save.on_change("active", self.__switch_save_handler)

        # button-send data
        button_send = Button(label="send", button_type="primary",align='end')
        self.text_input = text_input = TextInput(placeholder="Enter string", title="Signal to Sensor")
        spacer = Spacer(width=100,sizing_mode="stretch_width")
        button_send.on_event("button_click", self._send_button_handler)

        # button-config
        icon = BuiltinIcon("settings", size="1.2em", color="black")
        button_config = Button(label="CONFIG", icon=icon, button_type="light",align='end')
        js_callback = CustomJS(args=dict(), code="""
            window.open('./streamAcq?setting', '_blank');
        """)
        button_config.js_on_event('button_click', js_callback)

        if user_signal_plot is not None:
            plots_1 = column([
                row([multi_choice, button_config, swtichp_save, spacer,
                    row([button_send,text_input])
                    ],sizing_mode="stretch_width", margin=[0,20,0,0]),
                signal_plot,user_signal_plot],sizing_mode="stretch_both")
        else:
            plots_1 = column([
                row([multi_choice, button_config, swtichp_save, spacer,
                    row([button_send,text_input])
                    ],sizing_mode="stretch_width", margin=[0,20,0,0]),
                signal_plot],sizing_mode="stretch_both")
        self.page = column([desc,plots_1],sizing_mode="stretch_both")

        # some varible
        self.globalv = 0
        self.start_saving = False
        self.stop_saving = False
        self.is_saving = not Saving._stop_sig


    def __call__(self):
        return self.page

    def _send_button_handler(self, e):
        Acserial.write_to_sensor(self.text_input.value.encode())

    def __switch_save_handler(self,e,old,new):
        if new and Saving._stop_sig:
            # check any ColumnDataSource, if there is no data, then don't save
            datasource = self.dataMaps[tuple(self.dataMaps.keys())[0]][0]
            if len(datasource.data['t']) == 0:
                self.pre_switch.text = "Cannot save before the data acquisition"
                self.switch_save.active = False
                return
            
            Saving.start()
            if Saving._stop_sig:
                self.switch_save.active = False
                self.pre_switch.text = "Cannot save... Please chech out the configuration!"
            else:
                self.pre_switch.text = "Save"
                self.save_start_time = time.time() * 1000
                self.start_saving = True
                self.is_saving = True
        elif not new and not Saving._stop_sig:
            Saving.stop()
            self.save_stop_time = time.time() * 1000
            self.stop_saving = True
            self.is_saving = False

    def update(self):
        dataMaps = self.dataMaps
        self.globalv +=1
        idx = 0
        # update the plots
        for key in dataMaps:
            datas,datas_times,last_n = Processing.get_data(key,dataMaps[key][1])
            if len(datas_times) == 0:
                continue
            dataMaps[key][1] = last_n

            if self.globalv % 20 == 0:
                # get sampling rate (milliseconds)
                sampling_rate = Processing.sample_periods[
                    Processing.sample_times_maps[key[0]]
                ]
                # update the number of plots
                if sampling_rate > 0:
                    dataMaps[key][3] = int(self.parms['tplot'] * 1000 / sampling_rate)
                    # update the sampling rate in legend
                    for j in range(len(key)):
                        self.signal_plot.legend.items[idx].label = LegendItem(label=f'{dataMaps[key][2][j]}({round(1000 / sampling_rate)}Hz)').label
                        idx += 1

            new_data = {
                't': datas_times,
                **dict(zip(
                    dataMaps[key][2],
                    [
                        [(d+self.offset[namec])*self.scale[namec] for d in data] 
                        for namec, data in zip(dataMaps[key][2],datas)
                    ]
                ))
            }
            dataMaps[key][0].stream(new_data,rollover = dataMaps[key][3])

        # update the plots of user's processed data
        userProcesdataMaps = self.userProcesdataMaps
        for key in userProcesdataMaps:
            for i,userData in enumerate(userProcesdataMaps[key]):
                datas,datas_times,last_n = Processing.get_user_processed_data(key,i,userData[1])

                if len(datas_times) == 0:
                    continue
                userData[1] = last_n

                new_data = {
                    't': datas_times,
                    userData[2]: datas
                }
                userData[0].stream(new_data,rollover = userData[3])
        
        # mark the saving time
        if self.start_saving:
            self.saving_time_source.stream(
                {
                    't':[self.save_start_time],
                    'lw':[1]
                }
            )
            self.start_saving = False
        if self.stop_saving:
            self.saving_time_source.stream(
                {
                    't':[self.save_stop_time],
                    'lw':[1]
                }
            )
            self.stop_saving = False
        if self.is_saving and Saving._stop_sig:
            # another thread stopped the saving
            self.switch_save.active = False
            self.is_saving = False
            self.stop_saving = True
            self.save_stop_time = time.time() * 1000
        elif not self.is_saving and not Saving._stop_sig:
            # another thread started the saving
            self.switch_save.active = True
            self.is_saving = True
            self.start_saving = True
            self.save_start_time = time.time() * 1000
        save_time_data = self.saving_time_source.data
        if len(save_time_data['t']) > 0  and save_time_data['t'][0] < (time.time() - self.parms['tplot']) * 1000:
            self.saving_time_source.data = {
                't':save_time_data['t'][1:],
                'lw':save_time_data['lw'][1:]
            }
