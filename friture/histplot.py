<<<<<<< HEAD
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 Timoth￩e Lecomte

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

from PyQt5 import Qt, QtWidgets
from numpy import zeros, ones, log10, array
from friture.histogramitem import HistogramItem
from friture.histplotpeakbaritem import HistogramPeakBarItem
from friture.plotting.scaleWidget import VerticalScaleWidget, HorizontalScaleWidget
from friture.plotting.scaleDivision import ScaleDivision
from friture.plotting.coordinateTransform import CoordinateTransform
from friture.plotting.canvasWidget import CanvasWidget
import friture.plotting.frequency_scales as fscales

# The peak decay rates (magic goes here :).
PEAK_DECAY_RATE = 1.0 - 3E-6

class HistPlot(QtWidgets.QWidget):

    def __init__(self, parent):
        super(HistPlot, self).__init__()

        self.verticalScaleDivision = ScaleDivision(-140, 0)
        self.verticalScaleTransform = CoordinateTransform(-140, 0, 100, 0, 0)

        self.verticalScale = VerticalScaleWidget(self, self.verticalScaleDivision, self.verticalScaleTransform)
        self.verticalScale.setTitle("PSD (dB A)")

        self.horizontalScaleDivision = ScaleDivision(44, 22000)
        self.horizontalScaleTransform = CoordinateTransform(44, 22000, 100, 0, 0)

        self.horizontalScale = HorizontalScaleWidget(self, self.horizontalScaleDivision, self.horizontalScaleTransform)
        self.horizontalScale.setTitle("Frequency (Hz)")

        self.canvasWidget = CanvasWidget(self, self.verticalScaleTransform, self.horizontalScaleTransform)
        self.canvasWidget.setTrackerFormatter(lambda x, y: "%d Hz, %.1f dB" % (x, y))

        plot_layout = QtWidgets.QGridLayout()
        plot_layout.setSpacing(0)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.addWidget(self.verticalScale, 0, 0)
        plot_layout.addWidget(self.canvasWidget, 0, 1)
        plot_layout.addWidget(self.horizontalScale, 1, 1)

        self.setLayout(plot_layout)

        self.needfullreplot = False

        self.horizontalScaleTransform.setScale(fscales.Logarithmic)
        self.horizontalScaleDivision.setScale(fscales.Logarithmic)

        # insert an additional plot item for the peak bar
        self.bar_peak = HistogramPeakBarItem()
        self.canvasWidget.attach(self.bar_peak)
        self.peak = zeros((1,))
        self.peak_int = 0
        self.peak_decay = PEAK_DECAY_RATE

        self.histogram = HistogramItem()
        self.histogram.set_color(Qt.Qt.darkGreen)
        self.canvasWidget.attach(self.histogram)

        # need to replot here for the size Hints to be computed correctly (depending on axis scales...)
        self.update()

    def setdata(self, fl, fh, fc, y):
        self.histogram.setData(fl, fh, fc, y)

        self.compute_peaks(y)
        self.bar_peak.setData(fl, fh, self.peak, self.peak_int, y)

        # only draw on demand
        # self.draw()

    def draw(self):
        if self.needfullreplot:
            self.needfullreplot = False

            self.verticalScaleTransform.setLength(self.canvasWidget.height())

            start_border, end_border = self.verticalScale.spacingBorders()
            self.verticalScaleTransform.setBorders(start_border, end_border)

            self.verticalScale.update()

            self.horizontalScaleTransform.setLength(self.canvasWidget.width())

            start_border, end_border = self.horizontalScale.spacingBorders()
            self.horizontalScaleTransform.setBorders(start_border, end_border)

            self.horizontalScale.update()

            x_major_tick = self.horizontalScaleDivision.majorTicks()
            x_minor_tick = self.horizontalScaleDivision.minorTicks()
            y_major_tick = self.verticalScaleDivision.majorTicks()
            y_minor_tick = self.verticalScaleDivision.minorTicks()
            self.canvasWidget.setGrid(array(x_major_tick),
                                      array(x_minor_tick),
                                      array(y_major_tick),
                                      array(y_minor_tick))

        self.canvasWidget.update()

    # redraw when the widget is resized to update coordinates transformations
    def resizeEvent(self, event):
        self.needfullreplot = True
        self.draw()

    def compute_peaks(self, y):
        if len(self.peak) != len(y):
            y_ones = ones(y.shape)
            self.peak = y_ones * (-500.)
            self.peak_int = zeros(y.shape)
            self.peak_decay = y_ones * 20. * log10(PEAK_DECAY_RATE) * 5000

        mask1 = (self.peak < y)
        mask2 = (~mask1)
        mask2_a = mask2 * (self.peak_int < 0.2)
        mask2_b = mask2 * (self.peak_int >= 0.2)

        self.peak[mask1] = y[mask1]
        self.peak[mask2_a] = self.peak[mask2_a] + self.peak_decay[mask2_a]

        self.peak_decay[mask1] = 20. * log10(PEAK_DECAY_RATE) * 5000
        self.peak_decay[mask2_a] += 20. * log10(PEAK_DECAY_RATE) * 5000

        self.peak_int[mask1] = 1.
        self.peak_int[mask2_b] *= 0.975

    def setspecrange(self, spec_min, spec_max):
        self.verticalScaleTransform.setRange(spec_min, spec_max)
        self.verticalScaleDivision.setRange(spec_min, spec_max)

        # notify that sizeHint has changed (this should be done with a signal emitted from the scale division to the scale bar)
        self.verticalScale.scaleBar.updateGeometry()

        self.needfullreplot = True
        self.update()

    def setweighting(self, weighting):
        if weighting == 0:
            title = "PSD (dB)"
        elif weighting == 1:
            title = "PSD (dB A)"
        elif weighting == 2:
            title = "PSD (dB B)"
        else:
            title = "PSD (dB C)"

        self.verticalScale.setTitle(title)
=======
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 Timoth￩e Lecomte

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
from numpy import zeros, ones, log10
import numpy
from friture.filled_curve import CurveType, FilledCurve
from friture.histplot_data import HistPlot_Data
from friture.plotting.coordinateTransform import CoordinateTransform
import friture.plotting.frequency_scales as fscales
from friture.qml_tools import qml_url, raise_if_error
from friture.store import GetStore

# The peak decay rates (magic goes here :).
PEAK_DECAY_RATE = 1.0 - 3E-6

class HistPlot(QtWidgets.QWidget):

    def __init__(self, parent, engine):
        super(HistPlot, self).__init__(parent)

        self.logger = logging.getLogger(__name__)

        store = GetStore()
        self._histplot_data = HistPlot_Data(store)
        store._dock_states.append(self._histplot_data)
        state_id = len(store._dock_states) - 1

        self._curve_peak = FilledCurve(CurveType.PEEK)
        self._histplot_data.add_plot_item(self._curve_peak)

        self._curve_signal = FilledCurve(CurveType.SIGNAL)
        self._histplot_data.add_plot_item(self._curve_signal)

        self._histplot_data.show_legend = False
        self._histplot_data.vertical_axis.name = "PSD (dB A)"
        self._histplot_data.vertical_axis.setTrackerFormatter(lambda x: "%.1f dB" % (x))
        self._histplot_data.horizontal_axis.name = "Frequency (Hz)"
        self._histplot_data.horizontal_axis.setTrackerFormatter(lambda x: "%.0f Hz" % (x))

        self._histplot_data.vertical_axis.setRange(0, 1)
        self._histplot_data.horizontal_axis.setRange(44, 22000)

        self.paused = False

        self.peak = zeros((3,))
        self.peak_int = zeros((3,))
        self.peak_decay = ones((3,)) * PEAK_DECAY_RATE

        self.normVerticalScaleTransform = CoordinateTransform(0, 1, 1, 0, 0)
        self.normHorizontalScaleTransform = CoordinateTransform(44, 22000, 1, 0, 0)

        self.normHorizontalScaleTransform.setScale(fscales.Logarithmic)
        self._histplot_data.horizontal_axis.scale_division.setScale(fscales.Logarithmic)
        self._histplot_data.horizontal_axis.coordinate_transform.setScale(fscales.Logarithmic)

        plotLayout = QtWidgets.QGridLayout(self)
        plotLayout.setSpacing(0)
        plotLayout.setContentsMargins(0, 0, 0, 0)

        self.quickWidget = QQuickWidget(engine, self)
        self.quickWidget.statusChanged.connect(self.on_status_changed)
        self.quickWidget.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.quickWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.quickWidget.setSource(qml_url("HistPlot.qml"))
        
        raise_if_error(self.quickWidget)

        self.quickWidget.rootObject().setProperty("stateId", state_id)

        plotLayout.addWidget(self.quickWidget)

        self.setLayout(plotLayout)

    def on_status_changed(self, status):
        if status == QQuickWidget.Error:
            for error in self.quickWidget.errors():
                self.logger.error("QML error: " + error.toString())

    def setdata(self, fl, fh, fc, y):
        if not self.paused:
            M = numpy.max(y)
            m = self.normVerticalScaleTransform.coord_min
            y_int = (y-m)/(numpy.abs(M-m)+1e-3)

            scaled_x_left = self.normHorizontalScaleTransform.toScreen(fl)
            scaled_x_right = self.normHorizontalScaleTransform.toScreen(fh)
            baseline = 1.
            scaled_y = 1. - self.normVerticalScaleTransform.toScreen(y)
            z = y_int

            self._curve_signal.setData(scaled_x_left, scaled_x_right, scaled_y, z, baseline)

            self.compute_peaks(y)
            scaled_peak = 1. - self.normVerticalScaleTransform.toScreen(self.peak)
            z_peak = self.peak_int
            self._curve_peak.setData(scaled_x_left, scaled_x_right, scaled_peak, z_peak, baseline)
            
            bar_label_x = (scaled_x_left + scaled_x_right)/2
            self._histplot_data.setBarLabels(bar_label_x, fc, scaled_y)

    def draw(self):
        return

    def pause(self):
        self.paused = True

    def restart(self):
        self.paused = False

    def canvasUpdate(self):
        return

    def compute_peaks(self, y):
        if len(self.peak) != len(y):
            y_ones = ones(y.shape)
            self.peak = y_ones * (-500.)
            self.peak_int = zeros(y.shape)
            self.peak_decay = y_ones * 20. * log10(PEAK_DECAY_RATE) * 5000

        mask1 = (self.peak < y)
        mask2 = (~mask1)
        mask2_a = mask2 * (self.peak_int < 0.2)
        mask2_b = mask2 * (self.peak_int >= 0.2)

        self.peak[mask1] = y[mask1]
        self.peak[mask2_a] = self.peak[mask2_a] + self.peak_decay[mask2_a]

        self.peak_decay[mask1] = 20. * log10(PEAK_DECAY_RATE) * 5000
        self.peak_decay[mask2_a] += 20. * log10(PEAK_DECAY_RATE) * 5000

        self.peak_int[mask1] = 1.
        self.peak_int[mask2_b] *= 0.975

    def setspecrange(self, spec_min, spec_max):
        if spec_min > spec_max:
            spec_min, spec_max = spec_max, spec_min

        self._histplot_data.vertical_axis.setRange(spec_min, spec_max)
        self.normVerticalScaleTransform.setRange(spec_min, spec_max)

    def setweighting(self, weighting):
        if weighting == 0:
            title = "PSD (dB)"
        elif weighting == 1:
            title = "PSD (dB A)"
        elif weighting == 2:
            title = "PSD (dB B)"
        else:
            title = "PSD (dB C)"

        self._histplot_data.vertical_axis.name = title
>>>>>>> 923f1a4e455571ef3f9a9007961200dc4fd89c7c
