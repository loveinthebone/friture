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

from numpy import log10, where, sign, arange, zeros,floor,float64, argmin

from friture.store import GetStore
from friture.audiobackend import SAMPLING_RATE
from friture.scope_data import Scope_Data
from friture.curve import Curve
from friture.qml_tools import qml_url, raise_if_error

#################
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
import friture.plotting.frequency_scales as fscales

from friture.audiobackend import SAMPLING_RATE
from friture_extensions.exp_smoothing_conv import pyx_exp_smoothed_value_numpy

#####################

SMOOTH_DISPLAY_TIMER_PERIOD_MS = 25
DEFAULT_TIMERANGE = 2 * SMOOTH_DISPLAY_TIMER_PERIOD_MS

class Scope_Widget(QtWidgets.QWidget):

    def __init__(self, parent, engine):
        super().__init__(parent)

        self.logger = logging.getLogger(__name__)

        self.audiobuffer = None

#####################
        self.proc = audioproc()

        self.maxfreq = DEFAULT_MAXFREQ
        self.proc.set_maxfreq(self.maxfreq)
        self.minfreq = DEFAULT_MINFREQ
        self.fft_size = 2 ** DEFAULT_FFT_SIZE * 32
        self.proc.set_fftsize(self.fft_size)
        self.spec_min = DEFAULT_SPEC_MIN
        self.spec_max = DEFAULT_SPEC_MAX
        self.weighting = DEFAULT_WEIGHTING
        self.dual_channels = False
        self.response_time = DEFAULT_RESPONSE_TIME

        # self.update_weighting()
        self.freq = self.proc.get_freq_scale()

        self.timerange_s = DEFAULT_TIMERANGE
        self.canvas_width = 100.

        self.old_index = 0
        self.overlap = 3. / 4.
        # self.overlap_frac = Fraction(3, 4)
        self.dT_s = self.fft_size * (1. - self.overlap) / float(SAMPLING_RATE)
        self.update_display_buffers()

        self.buffer_length = 100
        self.buffer = zeros((2, self.buffer_length))
        self.buffer1 = zeros((2, self.buffer_length))
        
        self.setresponsetime(self.response_time)
#######################


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

    def on_status_changed(self, status):
        if status == QQuickWidget.Error:
            for error in self.quickWidget.errors():
                self.logger.error("QML error: " + error.toString())

    def update_display_buffers(self):
        self.dispbuffers1 = zeros(len(self.freq))
        self.dispbuffers2 = zeros(len(self.freq))

    # method
    def set_buffer(self, buffer):
        self.audiobuffer = buffer  #Kingson: here only prepare a buffer space in memory, still empty, no data in it.
        self.old_index = self.audiobuffer.ringbuffer.offset

    def setresponsetime(self, response_time):
        # time = SMOOTH_DISPLAY_TIMER_PERIOD_MS/1000. #DISPLAY
        # time = 0.025 #IMPULSE setting for a sound level meter
        # time = 0.125 #FAST setting for a sound level meter
        # time = 1. #SLOW setting for a sound level meter
        self.response_time = response_time

        # an exponential smoothing filter is a simple IIR filter
        # s_i = alpha*x_i + (1-alpha)*s_{i-1}
        # we compute alpha so that the N most recent samples represent 100*w percent of the output
        w = 0.65
        delta_n = self.fft_size * (1. - self.overlap)
        n = self.response_time * SAMPLING_RATE / delta_n
        N = 2 * 4096
        self.alpha = 1. - (1. - w) ** (1. / (n + 1))
        self.kernel = self.compute_kernel(self.alpha, N)

    def compute_kernel(self, alpha, N):
        kernel = (1. - alpha) ** arange(N - 1, -1, -1)
        return kernel

    def handle_new_data(self, floatdata):

        index = self.audiobuffer.ringbuffer.offset
        # self.last_data_time = self.audiobuffer.lastDataTime
        available = index - self.old_index

        if available < 0:
            # ringbuffer must have grown or something...
            available = 0
            self.old_index = index

        needed = self.fft_size * (1. - self.overlap)
        realizable = int(floor(available / needed))

        if realizable > 0:
            sp1n = zeros((len(self.freq), realizable), dtype=float64)
            sp2n = zeros((len(self.freq), realizable), dtype=float64)

            for i in range(realizable):
                floatdata = self.audiobuffer.data_indexed(self.old_index, self.fft_size)

                # first channel
                # FFT transform
                sp1n[:, i] = self.proc.analyzelive(floatdata[0, :])
                sp2n[:, i] = self.proc.analyzelive(floatdata[1, :])

                self.old_index += int(needed)
             # compute the widget data
            sp1 = pyx_exp_smoothed_value_numpy(self.kernel, self.alpha, sp1n, self.dispbuffers1)
            sp2 = pyx_exp_smoothed_value_numpy(self.kernel, self.alpha, sp2n, self.dispbuffers2)
            # store result for next computation
            self.dispbuffers1 = sp1 #Kingson: display buffer?
            self.dispbuffers2 = sp2    

            amp1=sp1[10]
            amp2=sp2[15]
            self.buffer1=self.buffer
            self.buffer[:, self.buffer_length-1]=[amp1, amp2]

            for i in range(self.buffer_length-1):
                self.buffer[:,i]=self.buffer1[:, i+1]

            x=list(range(self.buffer_length))
            self._curve_2.setData(x, self.buffer[0,:])
            self._curve.setData(x, self.buffer[1,:])



#         # time = self.timerange * 1e-3
#         # width = int(time * SAMPLING_RATE)
#         # basic trigger capability on leading edge
#         floatdata = self.audiobuffer.data(2 * width)

# #        print(floatdata.shape) # Kingson : I added this line, the result is (2,4800)

#         twoChannels = False
#         if floatdata.shape[0] > 1:
#             twoChannels = True

#         if twoChannels and len(self._scope_data.plot_items) == 1:
#             self._scope_data.add_plot_item(self._curve_2)
#         elif not twoChannels and len(self._scope_data.plot_items) == 2:
#             self._scope_data.remove_plot_item(self._curve_2)

#         # trigger on the first channel only
#         triggerdata0 = floatdata[0, :]
#         # trigger on half of the waveform
#         trig_search_start = width // 2
#         trig_search_stop = -width // 2
#         triggerdata = self.new_method(triggerdata0, trig_search_start, trig_search_stop)

#         trigger_level = floatdata.max() * 2. / 3.
#         trigger_pos = where((triggerdata[:-1] < trigger_level) * (triggerdata[1:] >= trigger_level))[0]
#         # where() function returns the indices of elements in an input array where the given condition is satisfied.
        
#         if len(trigger_pos) == 0:
#             return

#         if len(trigger_pos) > 0:
#             shift = trigger_pos[0]
#         else:
#             shift = 0
#         shift += trig_search_start
#         datarange = width
#         floatdata = floatdata[:, shift - datarange // 2: shift + datarange // 2]

#         self.y = floatdata[0, :]
#         if twoChannels:
#             self.y2 = floatdata[1, :]
#         else:
#             self.y2 = None

#         dBscope = False
#         if dBscope:
#             dBmin = -50.
#             self.y = sign(self.y) * (20 * log10(abs(self.y))).clip(dBmin, 0.) / (-dBmin) + sign(self.y) * 1.
#             if twoChannels:
#                 self.y2 = sign(self.y2) * (20 * log10(abs(self.y2))).clip(dBmin, 0.) / (-dBmin) + sign(self.y2) * 1.
#             else:
#                 self.y2 = None

#         self.time = (arange(len(self.y)) - datarange // 2) / float(SAMPLING_RATE)

#         scaled_t = (self.time * 1e3 + self.timerange/2.) / self.timerange
#         scaled_y = 1. - (self.y + 1) / 2.
#         self._curve.setData(scaled_t, scaled_y)

#         if self.y2 is not None:
#             scaled_y2 = 1. - (self.y2 + 1) / 2.
#             self._curve_2.setData(scaled_t, scaled_y2)

    def new_method(self, triggerdata0, trig_search_start, trig_search_stop):
        triggerdata = triggerdata0[trig_search_start: trig_search_stop]
        return triggerdata

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
