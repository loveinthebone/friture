
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 Timoth?Lecomte

# This file is part of Friture.
#
# Friture is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as published by
# the Free Software Foundation.
#
# Friture is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Friture.  If not, see <http://www.gnu.org/licenses/>.

import logging

from PyQt5 import QtWidgets
from PyQt5.QtQuickWidgets import QQuickWidget

from numpy import log10, where, sign, arange, zeros, ones, sin, array,float64,amax

from friture.store import GetStore
from friture.audiobackend import SAMPLING_RATE
from friture.scope_data import Scope_Data
from friture.curve import Curve
from friture.qml_tools import qml_url, raise_if_error
from friture.audioproc import audioproc  # audio processing class
from friture.spectrum_settings import (Spectrum_Settings_Dialog,  # settings dialog
                                       DEFAULT_FFT_SIZE,
                                       DEFAULT_FREQ_SCALE,
                                       DEFAULT_MAXFREQ,
                                       DEFAULT_MINFREQ,
                                       DEFAULT_SPEC_MIN,
                                       DEFAULT_SPEC_MAX,
                                       DEFAULT_WEIGHTING,
                                       DEFAULT_RESPONSE_TIME,
                                       DEFAULT_SHOW_FREQ_LABELS)



SMOOTH_DISPLAY_TIMER_PERIOD_MS = 25
DEFAULT_TIMERANGE = 2 * SMOOTH_DISPLAY_TIMER_PERIOD_MS

class Scope_Widget1(QtWidgets.QWidget):

    def __init__(self, parent, engine):
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)

        self.audiobuffer = None

        store = GetStore()
        self._scope_data = Scope_Data(store)
        store._dock_states.append(self._scope_data)
        state_id = len(store._dock_states) - 1

        self._curve = Curve()
        self._curve.name = "Ch1"
        self._scope_data.add_plot_item(self._curve)

        self._curve_2 = Curve()
        self._curve_2.name = "Ch2"

        self._scope_data.vertical_axis.name = "Signal"
        self._scope_data.vertical_axis.setTrackerFormatter(lambda x: "%#.3g" % (x))
        self._scope_data.horizontal_axis.name = "Time (ms)"
        self._scope_data.horizontal_axis.setTrackerFormatter(lambda x: "%#.3g ms" % (x))

        self.setObjectName("Scope_Widget")
        self.gridLayout = QtWidgets.QGridLayout(self)
        self.gridLayout.setObjectName("gridLayout")
        self.gridLayout.setContentsMargins(2, 2, 2, 2)

        self.quickWidget = QQuickWidget(engine, self)
        self.quickWidget.statusChanged.connect(self.on_status_changed)
        self.quickWidget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.quickWidget.setSource(qml_url("Scope.qml"))
        
        raise_if_error(self.quickWidget)

        self.quickWidget.rootObject().setProperty("stateId", state_id)

        self.gridLayout.addWidget(self.quickWidget)

        self.settings_dialog = Scope_Settings_Dialog(self)

        self.set_timerange(DEFAULT_TIMERANGE)

        self.time = zeros(10)
        self.y = zeros(10)
        self.y2 = zeros(10)



        # initialize the class instance that will do the fft
        self.proc = audioproc()
        # self.maxfreq = DEFAULT_MAXFREQ
        # self.proc.set_maxfreq(self.maxfreq)
        # self.minfreq = DEFAULT_MINFREQ
        self.fft_size = 2 ** DEFAULT_FFT_SIZE * 32 #8192
        self.proc.set_fftsize(self.fft_size)
        # self.spec_min = DEFAULT_SPEC_MIN
        # self.spec_max = DEFAULT_SPEC_MAX
        # self.weighting = DEFAULT_WEIGHTING
        # self.dual_channels = False
        # self.response_time = DEFAULT_RESPONSE_TIME
        self.freq = self.proc.get_freq_scale()

      
        self.buff1=zeros(self.fft_size)
        self.buff2=zeros(self.fft_size)
        self.buff0=zeros(self.fft_size)
        self.buff3=zeros(self.fft_size)

    def on_status_changed(self, status):
        if status == QQuickWidget.Error:
            for error in self.quickWidget.errors():
                self.logger.error("QML error: " + error.toString())

    # method
    def set_buffer(self, buffer):
        self.audiobuffer = buffer

    def handle_new_data(self, floatdata):
        
        floatdata = self.audiobuffer.data(self.fft_size)

        # time = self.timerange * 1e-3
        # width = int(time * SAMPLING_RATE)
        # # basic trigger capability on leading edge
        # floatdata = self.audiobuffer.data(2 * width)

        twoChannels = False
        if floatdata.shape[0] > 1:
            twoChannels = True

        if twoChannels and len(self._scope_data.plot_items) == 1:
            self._scope_data.add_plot_item(self._curve_2)
        elif not twoChannels and len(self._scope_data.plot_items) == 2:
            self._scope_data.remove_plot_item(self._curve_2)

        # # trigger on the first channel only
        # triggerdata = floatdata[0, :]
        # # trigger on half of the waveform
        # trig_search_start = width // 2
        # trig_search_stop = -width // 2
        # triggerdata = triggerdata[trig_search_start: trig_search_stop]

        # trigger_level = floatdata.max() * 2. / 3.
        # trigger_pos = where((triggerdata[:-1] < trigger_level) * (triggerdata[1:] >= trigger_level))[0]

        # if len(trigger_pos) == 0:
        #     return

        # if len(trigger_pos) > 0:
        #     shift = trigger_pos[0]
        # else:
        #     shift = 0
        # shift += trig_search_start

        # datarange = width
        # floatdata = floatdata[:, shift - datarange // 2: shift + datarange // 2] # the number of elements in floatdata become datarange here. select the portion of data that meet the trigger condition

        self.y = floatdata[0, :]
        if twoChannels:
            self.y2 = floatdata[1, :]
        else:
            self.y2 = None


        sp1n = zeros(self.fft_size, dtype=float64)
        sp2n = zeros(self.fft_size, dtype=float64)
        sp1n = self.proc.analyzelive(floatdata[0, :])
        if twoChannels:
            # second channel for comparison
            sp2n = self.proc.analyzelive(floatdata[1, :])

        if twoChannels:
            dB_spectrogram =  self.log_spectrogram(sp1n)
            dB_spectrogram2= self.log_spectrogram(sp2n)
        else:
            dB_spectrogram = self.log_spectrogram(sp1n) 

    ###########################################################################
        self.freq1=1000. # frequency I am interested in to extract fft amp ####
        self.freq2=1500.                                                   ####
    ###########################################################################
        self.freq_idx1=(abs(self.freq-self.freq1)).argmin()
        self.freq_idx2=(abs(self.freq-self.freq2)).argmin()
        #check self.freq[self.freq_idx1] , see if it is close to 1000

        data=dB_spectrogram[self.freq_idx1]
        

        self.buff0=self.buff1
        self.buff1[-1]=data
        for i in range(len(self.buff1)-1):
            self.buff1[i]=self.buff0[i+1]

        b=self.buff1
        a=arange(self.fft_size)




        scaled_a=a/self.fft_size

        range_min=0 #the minimum value that the target signal can reach at target frequency
        range_max=0.001
        # range_min=-200 #the minimum value that the target signal can reach at target frequency
        # range_max=-20
        range_middle=(range_min+range_max)/2
        range_length=range_max-range_min

        b=(b-range_middle)/(range_length/2)  #turn b into the range (-1, 1)

        # b=(b+140.)/60. #turn b into the range (-1, 1)
        scaled_b=1-(b+1)/2.  #turn scaled_b into the range (1,0)
        self._curve.setData(scaled_a, scaled_b)
#####################################################
        if twoChannels:
            data2=dB_spectrogram2[self.freq_idx2]
            self.buff2=self.buff3
            self.buff3[-1]=data2
            for i in range(len(self.buff3)-1):
                self.buff3[i]=self.buff2[i+1]

            b=self.buff3
            a=arange(self.fft_size)

            scaled_a=a/self.fft_size

            # range_min=-200 #the minimum value that the target signal can reach at target frequency
            # range_max=-20
            # range_min=0 #the minimum value that the target signal can reach at target frequency
            # range_max=0.001
            # range_middle=(range_min+range_max)/2
            # range_length=range_max-range_min

            b=(b-range_middle)/(range_length/2)  #turn b into the range (-1, 1)
            scaled_b=1-(b+1)/2.
            self._curve_2.setData(scaled_a, scaled_b)

        # dBscope = False
        # if dBscope:
        #     dBmin = -50.
        #     self.y = sign(self.y) * (20 * log10(abs(self.y))).clip(dBmin, 0.) / (-dBmin) + sign(self.y) * 1.
        #     if twoChannels:
        #         self.y2 = sign(self.y2) * (20 * log10(abs(self.y2))).clip(dBmin, 0.) / (-dBmin) + sign(self.y2) * 1.
        #     else:
        #         self.y2 = None

        # self.time = (arange(len(self.y)) - datarange // 2) / float(SAMPLING_RATE)
        """
        datarange=240, datarange=width, width is number of samples.
                time = self.timerange * 1e-3  #self.timerange is the time set by user in ms.
                width = int(time * SAMPLING_RATE)

        len(self.y)=240
        SAMPLING_RATE=48000

        """

        # scaled_t = (self.time * 1e3 + self.timerange/2.) / self.timerange  #make sure in the end the x axis is going from 0 to 1
        # scaled_y = 1. - (self.y + 1) / 2.  # if the range of y is (-1:1),make sure in the end, the y axis range is (2:0)
        # self._curve.setData(scaled_t, scaled_y)
        # if self.y2 is not None:
        #     scaled_y2 = 1. - (self.y2 + 1) / 2.
        #     self._curve_2.setData(scaled_t, scaled_y2)       
       
       
       
        # a=arange(100)/100
        # b=sin(arange(100))
        # b=0.5*ones(100)
        # np.array([1, 2, 3])
################################################Kingson*************
        #The _curve function will only plot the data with x in the range of 0 to 1, and y in the range of -1 to 1, following code showed such an arrangement:
        # a=array([0, 0.5, 1])
        # b=array([-1,0.4, 1])
        # b=1-(b+1)/2.
        # self._curve.setData(a, b)
###############################################Kingson **************


    def log_spectrogram(self, sp):
        # Note: implementing the log10 of the array in Cython did not bring
        # any speedup.
        # Idea: Instead of computing the log of the data, I could pre-compute
        # a list of values associated with the colormap, and then do a search...
        # epsilon = 1e-30
        # return 10. * log10(sp + epsilon)
        return sp


    # method
    def canvasUpdate(self):
        return

    def pause(self):
        return

    def restart(self):
        return

    # slot
    def set_timerange(self, timerange):
        self.timerange = timerange
        self._scope_data.horizontal_axis.setRange(-self.timerange/2., self.timerange/2.)

    # slot
    def settings_called(self, checked):
        self.settings_dialog.show()

    # method
    def saveState(self, settings):
        self.settings_dialog.saveState(settings)

    # method
    def restoreState(self, settings):
        self.settings_dialog.restoreState(settings)


class Scope_Settings_Dialog(QtWidgets.QDialog):

    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("Scope settings")

        self.formLayout = QtWidgets.QFormLayout(self)

        self.doubleSpinBox_timerange = QtWidgets.QDoubleSpinBox(self)
        self.doubleSpinBox_timerange.setDecimals(1)
        self.doubleSpinBox_timerange.setMinimum(0.1)
        self.doubleSpinBox_timerange.setMaximum(1000.0)
        self.doubleSpinBox_timerange.setProperty("value", DEFAULT_TIMERANGE)
        self.doubleSpinBox_timerange.setObjectName("doubleSpinBox_timerange")
        self.doubleSpinBox_timerange.setSuffix(" ms")

        self.formLayout.addRow("Time range:", self.doubleSpinBox_timerange)

        self.setLayout(self.formLayout)

        self.doubleSpinBox_timerange.valueChanged.connect(self.parent().set_timerange)

    # method
    def saveState(self, settings):
        settings.setValue("timeRange", self.doubleSpinBox_timerange.value())

    # method
    def restoreState(self, settings):
        timeRange = settings.value("timeRange", DEFAULT_TIMERANGE, type=float)
        self.doubleSpinBox_timerange.setValue(timeRange)
