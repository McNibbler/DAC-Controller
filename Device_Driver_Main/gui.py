#####################################
# DAC Driver GUI                    #
# Version: Beta 0.2.1               #
# Thomas Kaunzinger                 #
# May 18, 2018                      #
#                                   #
# A GUI for interfacing with the    #
# Arduino DAC controller.           #
#####################################

###################################################

#######################
# IMPORTING LIBRARIES #
#######################

import sys
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *

from pyduino import *
import controller


###################################################

########################
# QT GUI FUNCTIONALITY #
########################

class Application(QWidget):

    # Init me
    def __init__(self):
        super().__init__()

        ############
        # DAC SIDE #
        ############

        # Label for the DAC controller
        self.dac_title = QLabel()
        self.dac_title.setText('AD5732 DAC Controller')

        # Status text for the program
        self.status_text = QLabel()
        self.status_text.setText('Welcome!')

        # DAC initialization button
        self.setup_button = QPushButton('Initialize DAC')
        self.setup_button.setToolTip('Press to initialize the DAC')
        self.setup_button.clicked.connect(self.setup)

        # Selects bipolar mode
        self.bipolar_checkbox = QCheckBox('Bipolar')
        self.bipolar_checkbox.toggle()
        self.bipolar_checkbox.setToolTip('Toggle between monopolar and bipolar voltage ranges')
        self.bipolar_checkbox.stateChanged.connect(self.bipolar_toggle)

        # Connects the outputs together
        self.connect_sliders_checkbox = QCheckBox('Tie Outputs')
        self.connect_sliders_checkbox.setToolTip('Make the voltage of DAC B be the same as DAC A')
        self.connect_sliders_checkbox.stateChanged.connect(self.tie_outputs)

        # Sets the reference voltage
        self.reference_voltage = 2.5
        self.reference_label = QLabel()
        self.reference_label.setText('Ref (V):')
        self.reference_textbox = QLineEdit()
        self.reference_textbox.setText(str(self.reference_voltage))
        self.reference_textbox.returnPressed.connect(self.update_ranges)

        # Selectable gain modes
        self.gain = 2.0
        self.gain_label = QLabel()
        self.gain_label.setText('Gain:')
        self.gain_modes = [str(self.gain), str(4.0), str(4.32)]
        self.gain_select = QComboBox()
        self.gain_select.addItems(self.gain_modes)
        self.gain_select.activated[str].connect(self.update_ranges)

        # COM port select
        self.com_select = QComboBox()
        self.com_ports = list(controller.COM_PORTS_LIST)
        self.com_select.addItems(self.com_ports)

        initial_select = 0
        for i in range(0, len(self.com_ports)):
            if controller.com_port == self.com_ports[i]:
                initial_select = i

        self.com_select.setCurrentIndex(initial_select)
        self.com_select.activated[str].connect(self.change_com)

        # Voltage sliders
        self.iterator = 1 << 14
        self.bipolar_range = range(int(-1*self.gain*self.reference_voltage*self.iterator),
                                   int(self.gain*self.reference_voltage*self.iterator), 1)
        self.unipolar_range = range(0, int(self.gain*self.reference_voltage*self.iterator), 1)

        self.voltage_label_a = QLabel()
        self.voltage_label_a.setText('DAC A')
        self.voltage_textbox_a = QLineEdit()
        self.voltage_textbox_a.setText("%.5f" % 0.0)
        self.voltage_textbox_a.returnPressed.connect(self.update_sliders)
        self.voltage_slider_a = QSlider(Qt.Horizontal)
        self.voltage_slider_a.setRange(min(self.bipolar_range), max(self.bipolar_range))
        self.voltage_slider_a.valueChanged[int].connect(self.change_voltage)
        self.voltage_slider_a.sliderReleased.connect(self.send_slider)

        self.voltage_label_b = QLabel()
        self.voltage_label_b.setText('DAC B')
        self.voltage_textbox_b = QLineEdit()
        self.voltage_textbox_b.setText("%.5f" % 0.0)
        self.voltage_textbox_b.returnPressed.connect(self.update_sliders)
        self.voltage_slider_b = QSlider(Qt.Horizontal)
        self.voltage_slider_b.setRange(min(self.bipolar_range), max(self.bipolar_range))
        self.voltage_slider_b.valueChanged[int].connect(self.change_voltage)
        self.voltage_slider_b.sliderReleased.connect(self.send_slider)

        # Input text boxes for voltage
        self.only_double = QDoubleValidator()
        self.reference_textbox.setValidator(self.only_double)
        self.voltage_textbox_a.setValidator(self.only_double)
        self.voltage_textbox_b.setValidator(self.only_double)

        # Readback
        self.readback_label = QLabel()
        self.readback_label.setText('Voltage Readback:')
        self.readback_a = QLabel()
        self.readback_a.setText(str('DAC A: ' + str(0.0) + 'V'))
        self.readback_b = QLabel()
        self.readback_b.setText(str('DAC B: ' + str(0.0) + 'V'))

        # States
        self.is_bipolar = True
        self.is_tied = False

        ############
        # DDS SIDE #
        ############

        # Label for the DAC controller
        self.dds_title = QLabel()
        self.dds_title.setText('AD9910 DDS Controller')

        # Load data to the dds
        self.dds_load_button = QPushButton('Load to DDS')
        self.dds_load_button.setToolTip('Update the DDS by loading all selected parameters to the device')
        self.dds_load_button.clicked.connect(self.dds_load)

        # Digital ramp generation parameters
        self.drg_select_checkbox = QCheckBox('Digital Ramp Enable')
        self.drg_select_checkbox.setToolTip('Ramp through a range of either Amplitudes, Phases, or Frequencies')
        self.drg_select_checkbox.stateChanged.connect(self.drg_toggle)
        self.drg_enabled = False

        # Single Tone Sliders
        self.dds_max_frequency = 1<<30   # kind of arbitrary here so it means the slider wont be as precise; program
        self.dds_frequency_iterator = 0.01     # is way too slow if I give the proper slider precision (textbox is fine)
        self.dds_frequency_range = range(0, int(self.dds_frequency_iterator*self.dds_max_frequency))

        self.dds_frequency_label = QLabel()
        self.dds_frequency_label.setText('Frequency (Hz)')
        self.dds_frequency_slider = QSlider(Qt.Horizontal)
        self.dds_frequency_slider.setRange(min(self.dds_frequency_range), max(self.dds_frequency_range))
        self.dds_frequency_slider.sliderReleased.connect(self.update_frequency_slider)
        self.dds_desire_freq_label = QLabel()
        self.dds_desire_freq_label.setText('Desired:')
        self.dds_frequency_textbox = QLineEdit()
        self.dds_frequency_textbox.setText("%.3f" % 0.0)
        self.dds_frequency_textbox.returnPressed.connect(self.update_frequency_textbox)
        self.dds_freq_sysclk_label = QLabel()
        self.dds_freq_sysclk_label.setText('Sysclk:')
        self.dds_freq_sysclk_textbox = QLineEdit()
        self.dds_freq_sysclk_textbox.setToolTip('Sysclk reference frequency (Hz)')
        self.dds_freq_sysclk_textbox.setText("%.3f" % self.dds_max_frequency)
        self.dds_freq_sysclk_textbox.returnPressed.connect(self.update_freq_sysclk)

        self.dds_max_phase = 360
        self.dds_phase_iterator = int((1 << 16) / self.dds_max_phase)
        self.dds_phase_range = range(0, int(self.dds_phase_iterator*self.dds_max_phase))

        self.dds_phase_label = QLabel()
        self.dds_phase_label.setText('Phase (Degrees)')
        self.dds_phase_slider = QSlider(Qt.Horizontal)
        self.dds_phase_slider.setRange(min(self.dds_phase_range), max(self.dds_phase_range))
        self.dds_phase_slider.sliderReleased.connect(self.update_phase_slider)
        self.dds_desire_phase_label = QLabel()
        self.dds_desire_phase_label.setText('Desired:')
        self.dds_phase_textbox = QLineEdit()
        self.dds_phase_textbox.setText("%.5f" % 0.0)
        self.dds_phase_textbox.returnPressed.connect(self.update_phase_textbox)

        self.dds_max_amplitude = 1
        self.dds_amplitude_iterator = int((1 << 14) * 10 / self.dds_max_amplitude)
        self.dds_amplitude_range = range(0, int(self.dds_amplitude_iterator * self.dds_max_amplitude))

        self.dds_amplitude_label = QLabel()
        self.dds_amplitude_label.setText('Amplitude (V)')
        self.dds_amplitude_slider = QSlider(Qt.Horizontal)
        self.dds_amplitude_slider.setRange(min(self.dds_amplitude_range), max(self.dds_amplitude_range))
        self.dds_amplitude_slider.sliderReleased.connect(self.update_amplitude_slider)
        self.dds_desire_amp_label = QLabel()
        self.dds_desire_amp_label.setText('Desired:')
        self.dds_amplitude_textbox = QLineEdit()
        self.dds_amplitude_textbox.setText("%.5f" % 0.0)
        self.dds_amplitude_textbox.returnPressed.connect(self.update_amplitude_textbox)
        self.dds_amplitude_ref_label = QLabel()
        self.dds_amplitude_ref_label.setText('Reference:')
        self.dds_amplitude_ref_textbox = QLineEdit()
        self.dds_amplitude_ref_textbox.setToolTip('Max Reference Voltage (V)')
        self.dds_amplitude_ref_textbox.setText("%.5f" % self.dds_max_amplitude)
        self.dds_amplitude_ref_textbox.returnPressed.connect(self.update_amplitude_ref)

        # Textbox validators
        self.dds_freq_sysclk_textbox.setValidator(self.only_double)
        self.dds_frequency_textbox.setValidator(self.only_double)
        self.dds_phase_textbox.setValidator(self.only_double)
        self.dds_amplitude_ref_textbox.setValidator(self.only_double)
        self.dds_amplitude_textbox.setValidator(self.only_double)

        #############
        # EXECUTION #
        #############

        # Window dimensions
        self.WINDOW_SIZE = (670, 300)
        self.setFixedSize(self.WINDOW_SIZE[0], self.WINDOW_SIZE[1])
        self.setWindowTitle('Device Controller')

        if controller.serial_port == "none":
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            box.setText('No COM Ports Available')
            box.setInformativeText('Plug in your device and try again.')
            box.setStandardButtons(QMessageBox.Ok)
            box.exec_()

            sys.exit()

        else:
            controller.send_initialization(self.is_bipolar, self.gain)
            controller.send_voltage(controller.DAC_2, 0, self.reference_voltage, self.gain, self.is_bipolar)

            self.main_window()

    # Main window execution and layout
    def main_window(self):
        # Layout
        layout = QGridLayout()
        self.setLayout(layout)

        # Creates the DAC controller frame part of the GUI
        dac_frame = QFrame()
        dac_layout = QGridLayout()
        dac_frame.setLayout(dac_layout)

        dac_frame.setFixedSize(300, 275)

        dac_layout.addWidget(self.dac_title, 0, 0, 1, 3)

        dac_layout.addWidget(self.status_text, 1, 0, 1, 1)
        dac_layout.addWidget(self.com_select, 1, 1, 1, 1)
        dac_layout.addWidget(self.bipolar_checkbox, 1, 2, 1, 1)
        dac_layout.addWidget(self.connect_sliders_checkbox, 1, 3, 1, 1)

        dac_layout.addWidget(self.reference_label, 2, 0, 1, 1)
        dac_layout.addWidget(self.reference_textbox, 2, 1, 1, 1)
        dac_layout.addWidget(self.gain_label, 2, 2, 1, 1)
        dac_layout.addWidget(self.gain_select, 2, 3, 1, 1)

        dac_layout.addWidget(self.setup_button, 3, 0, 1, 4)

        dac_layout.addWidget(self.voltage_label_a, 4, 0, 1, 3)
        dac_layout.addWidget(self.voltage_textbox_a, 4, 3, 1, 1)

        dac_layout.addWidget(self.voltage_slider_a, 5, 0, 1, 4)

        dac_layout.addWidget(self.voltage_label_b, 6, 0, 1, 3)
        dac_layout.addWidget(self.voltage_textbox_b, 6, 3, 1, 1)

        dac_layout.addWidget(self.voltage_slider_b, 7, 0, 1, 4)

        dac_layout.addWidget(self.readback_label, 8, 0, 1, 4)

        dac_layout.addWidget(self.readback_a, 9, 0, 1, 2)
        dac_layout.addWidget(self.readback_b, 9, 3, 1, 2)

        # Creates the DDS controller frame part of the GUI
        dds_frame = QFrame()
        dds_layout = QGridLayout()
        dds_frame.setLayout(dds_layout)

        dds_frame.setFixedSize(350, 275)

        dds_layout.addWidget(self.dds_title, 0, 0, 1, 2)
        dds_layout.addWidget(self.drg_select_checkbox, 0, 2, 1, 2)

        dds_layout.addWidget(self.dds_frequency_label, 1, 0, 1, 2)

        dds_layout.addWidget(self.dds_freq_sysclk_label, 2, 0, 1, 1)
        dds_layout.addWidget(self.dds_freq_sysclk_textbox, 2, 1, 1, 1)
        dds_layout.addWidget(self.dds_desire_freq_label, 2, 2, 1, 1)
        dds_layout.addWidget(self.dds_frequency_textbox, 2, 3, 1, 1)

        dds_layout.addWidget(self.dds_frequency_slider, 3, 0, 1, 4)

        dds_layout.addWidget(self.dds_phase_label, 4, 0, 1, 2)

        dds_layout.addWidget(self.dds_desire_phase_label, 5, 2, 1, 1)
        dds_layout.addWidget(self.dds_phase_textbox, 5, 3, 1, 1)

        dds_layout.addWidget(self.dds_phase_slider, 6, 0, 1, 4)

        dds_layout.addWidget(self.dds_amplitude_label, 7, 0, 1, 2)

        dds_layout.addWidget(self.dds_amplitude_ref_label, 8, 0, 1, 1)
        dds_layout.addWidget(self.dds_amplitude_ref_textbox, 8, 1, 1, 1)
        dds_layout.addWidget(self.dds_desire_amp_label, 8, 2, 1, 1)
        dds_layout.addWidget(self.dds_amplitude_textbox, 8, 3, 1, 1)

        dds_layout.addWidget(self.dds_amplitude_slider, 9, 0, 1, 4)

        dds_layout.addWidget(self.dds_load_button, 10, 0, 1, 4)

        # Adds the frames to the main window
        layout.addWidget(dds_frame, 0, 0, 1, 1)
        layout.addWidget(dac_frame, 0, 1, 1, 1)

        self.show()

    def dds_load(self):
        pass

    def drg_toggle(self):
        pass

    def update_frequency_slider(self):
        self.dds_frequency_textbox.setText("%.3f" % (self.dds_frequency_slider.value() / self.dds_frequency_iterator))

    def update_frequency_textbox(self):
        new_frequency = float(self.dds_frequency_textbox.text())
        reference = self.dds_max_frequency

        if new_frequency > reference or new_frequency < 0:
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            box.setText('Bad Input:')
            box.setInformativeText('Chosen frequency exceeds sysclk.')
            box.setStandardButtons(QMessageBox.Ok)
            box.exec_()
            self.dds_frequency_textbox.setText("%.3f" % (self.dds_frequency_slider.value() / self.dds_frequency_iterator))
            return

        self.dds_frequency_slider.setValue(new_frequency * self.dds_frequency_iterator)

    def update_freq_sysclk(self):
        if float(self.dds_freq_sysclk_textbox.text()) < 1/self.dds_frequency_iterator:
            self.dds_max_frequency = float(1/self.dds_frequency_iterator)
            self.dds_freq_sysclk_textbox.setText("%.3f" % self.dds_max_frequency)
        else:
            self.dds_max_frequency = float(self.dds_freq_sysclk_textbox.text())

        self.dds_frequency_range = range(0, int(self.dds_max_frequency * self.dds_frequency_iterator))
        self.dds_frequency_slider.setRange(min(self.dds_frequency_range), max(self.dds_frequency_range))
        self.dds_frequency_slider.setValue(0)
        self.dds_frequency_textbox.setText("%.3f" % 0.0)

    def update_phase_slider(self):
        self.dds_phase_textbox.setText("%.5f" % (self.dds_phase_slider.value() / self.dds_phase_iterator))

    def update_phase_textbox(self):
        new_phase = float(self.dds_phase_textbox.text())
        reference = self.dds_max_phase

        if new_phase > reference or new_phase < 0:
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            box.setText('Bad Input:')
            box.setInformativeText('Chosen phase out of range.')
            box.setStandardButtons(QMessageBox.Ok)
            box.exec_()
            self.dds_phase_textbox.setText("%.5f" % (self.dds_phase_slider.value() / self.dds_phase_iterator))
            return

        self.dds_phase_slider.setValue(new_phase * self.dds_phase_iterator)

    def update_amplitude_slider(self):
        self.dds_amplitude_textbox.setText("%.5f" % (self.dds_amplitude_slider.value() / self.dds_amplitude_iterator))

    def update_amplitude_textbox(self):
        new_amplitude = float(self.dds_amplitude_textbox.text())
        reference = self.dds_max_amplitude

        if new_amplitude > reference or new_amplitude < 0:
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            box.setText('Bad Input:')
            box.setInformativeText('Chosen amplitude exceeds reference.')
            box.setStandardButtons(QMessageBox.Ok)
            box.exec_()
            self.dds_amplitude_textbox.setText("%.5f" % (self.dds_amplitude_slider.value() / self.dds_amplitude_iterator))
            return

        self.dds_amplitude_slider.setValue(new_amplitude * self.dds_amplitude_iterator)

    def update_amplitude_ref(self):
        if float(self.dds_amplitude_ref_textbox.text()) < 1/self.dds_amplitude_iterator:
            self.dds_max_amplitude = float(1/self.dds_amplitude_iterator)
            self.dds_amplitude_ref_textbox.setText("%.5f" % self.dds_max_amplitude)
        else:
            self.dds_max_amplitude = float(self.dds_amplitude_ref_textbox.text())

        self.dds_amplitude_range = range(0, int(self.dds_max_amplitude*self.dds_amplitude_iterator))
        self.dds_amplitude_slider.setRange(min(self.dds_amplitude_range), max(self.dds_amplitude_range))
        self.dds_amplitude_slider.setValue(0)
        self.dds_amplitude_textbox.setText("%.5f" % 0.0)

    # Ties the two sliders together
    def tie_outputs(self):

        if self.is_tied:
            self.is_tied = False

            self.voltage_textbox_b.setEnabled(True)
            self.voltage_slider_b.setEnabled(True)
            self.voltage_label_b.setText('DAC B')

        else:
            self.is_tied = True

            self.voltage_textbox_b.setEnabled(False)
            self.voltage_slider_b.setEnabled(False)
            self.voltage_label_b.setText('DAC B (Tied to DAC A)')

        self.status_text.setText('Welcome!')

    # Select between bipolar mode and unipolar
    def bipolar_toggle(self):

        if self.is_bipolar:
            self.is_bipolar = False
            self.voltage_slider_a.setRange(min(self.unipolar_range), max(self.unipolar_range))
            self.voltage_slider_b.setRange(min(self.unipolar_range), max(self.unipolar_range))
        else:
            self.is_bipolar = True
            self.voltage_slider_a.setRange(min(self.bipolar_range), max(self.bipolar_range))
            self.voltage_slider_b.setRange(min(self.bipolar_range), max(self.bipolar_range))

        self.voltage_textbox_a.setText("%.5f" % 0.0)
        self.voltage_textbox_b.setText("%.5f" % 0.0)
        self.voltage_slider_a.setSliderPosition(0)
        self.voltage_slider_b.setSliderPosition(0)

        # Resets the outputs and initializes the DACs for the new settings
        controller.send_initialization(self.is_bipolar, self.gain)
        controller.send_voltage(controller.DAC_2, 0.0, self.reference_voltage, self.gain, self.is_bipolar)

        self.status_text.setText('Welcome!')

    # Handler for when the slider is changed (Doesn't update DAC until release because that would suck)
    def change_voltage(self):

        new_voltage_a = self.voltage_slider_a.value() / self.iterator
        new_voltage_b = self.voltage_slider_b.value() / self.iterator

        self.voltage_textbox_a.setText("%.5f" % new_voltage_a)
        self.voltage_textbox_b.setText("%.5f" % new_voltage_b)

        self.status_text.setText('Welcome!')

    # Handler for when the text is changed and the sliders need to be updated
    def update_sliders(self):

        # Floats for the new voltages
        new_voltage_a = float(self.voltage_textbox_a.text())
        new_voltage_b = float(self.voltage_textbox_b.text())

        # Checks if the input is inside the appropriate range and gives a warning if it isn't and denies request
        if self.is_bipolar:
            if (new_voltage_a > self.gain*self.reference_voltage
                    or new_voltage_b > self.gain*self.reference_voltage
                    or new_voltage_a < -1*self.gain*self.reference_voltage
                    or new_voltage_b < -1*self.gain*self.reference_voltage):

                box = QMessageBox()
                box.setIcon(QMessageBox.Warning)
                box.setText('Bad Input:')
                box.setInformativeText('Chosen voltage is out of range.')
                box.setStandardButtons(QMessageBox.Ok)
                box.exec_()
                self.status_text.setText('Bad Input')
                self.voltage_textbox_a.setText("%.5f" % (self.voltage_slider_a.value() / self.iterator))
                self.voltage_textbox_b.setText("%.5f" % (self.voltage_slider_b.value() / self.iterator))
                return
        else:
            if (new_voltage_a > self.gain*self.reference_voltage
                    or new_voltage_b > self.gain*self.reference_voltage
                    or new_voltage_a < 0 or new_voltage_b < 0):

                box = QMessageBox()
                box.setIcon(QMessageBox.Warning)
                box.setText('Bad Input:')
                box.setInformativeText('Chosen voltage is out of range.')
                box.setStandardButtons(QMessageBox.Ok)
                box.exec_()
                self.status_text.setText('Bad Input')
                self.voltage_textbox_a.setText("%.5f" % (self.voltage_slider_a.value() / self.iterator))
                self.voltage_textbox_b.setText("%.5f" % (self.voltage_slider_b.value() / self.iterator))
                return

        # Sets the voltage sliders to match the new input
        self.voltage_slider_a.setValue(int(new_voltage_a * self.iterator))
        self.voltage_slider_b.setValue(int(new_voltage_b * self.iterator))

        # Sends the voltages to the DAC
        if self.is_tied:
            controller.send_voltage(controller.DAC_2,
                                    self.voltage_slider_a.value() / self.iterator,
                                    self.reference_voltage, self.gain, self.is_bipolar)
        else:
            controller.send_voltage(controller.DAC_A,
                                    self.voltage_slider_a.value() / self.iterator,
                                    self.reference_voltage, self.gain, self.is_bipolar)
            controller.send_voltage(controller.DAC_B,
                                    self.voltage_slider_b.value() / self.iterator,
                                    self.reference_voltage, self.gain, self.is_bipolar)

        self.status_text.setText('Welcome!')

    # Updates the program for if the chosen reference voltage is changed or if the other gain modes are selected
    def update_ranges(self):

        # Checks if the reference voltage is valid in the spec sheet
        if float(self.reference_textbox.text()) > 3 or float(self.reference_textbox.text()) < 2:
            box = QMessageBox()
            box.setIcon(QMessageBox.Warning)
            box.setText('Bad Input:')
            box.setInformativeText('The AD5722/AD5732/AD5752 DAC supports a reference voltage of +2 to +3V')
            box.setStandardButtons(QMessageBox.Ok)
            box.exec_()
            self.status_text.setText('Bad Input')
            self.reference_textbox.setText(str(self.reference_voltage))
            return

        # Sets the selections to be appropriate
        self.reference_voltage = float(self.reference_textbox.text())
        self.gain = float(self.gain_select.currentText())

        # Resets everything
        self.voltage_textbox_a.setText("%.5f" % 0.0)
        self.voltage_textbox_b.setText("%.5f" % 0.0)
        self.voltage_slider_a.setValue(0)
        self.voltage_slider_b.setValue(0)

        self.bipolar_range = range(int(-1 * self.gain * self.reference_voltage * self.iterator),
                                   int(self.gain * self.reference_voltage * self.iterator), 1)
        self.unipolar_range = range(0, int(self.gain * self.reference_voltage * self.iterator), 1)

        if self.is_bipolar:
            self.voltage_slider_a.setRange(min(self.bipolar_range), max(self.bipolar_range))
            self.voltage_slider_b.setRange(min(self.bipolar_range), max(self.bipolar_range))
        else:
            self.voltage_slider_a.setRange(min(self.unipolar_range), max(self.unipolar_range))
            self.voltage_slider_b.setRange(min(self.unipolar_range), max(self.unipolar_range))

        self.status_text.setText('Welcome!')

        # Resets the DAC
        controller.send_initialization(self.is_bipolar, self.gain)
        controller.send_voltage(controller.DAC_2, 0, self.reference_voltage, self.gain, self.is_bipolar)

    # Sends the setup command to the DAC
    def setup(self):
        controller.send_initialization(self.is_bipolar, self.gain)
        controller.send_voltage(controller.DAC_2, 0, self.reference_voltage, self.gain, self.is_bipolar)
        self.status_text.setText('Welcome!')

    # Sends update commands to the DAC upon releasing the slider
    def send_slider(self):
        if self.is_tied:
            controller.send_voltage(controller.DAC_2,
                                    self.voltage_slider_a.value() / self.iterator,
                                    self.reference_voltage, self.gain, self.is_bipolar)
        else:
            controller.send_voltage(controller.DAC_A,
                                    self.voltage_slider_a.value() / self.iterator,
                                    self.reference_voltage, self.gain, self.is_bipolar)
            controller.send_voltage(controller.DAC_B,
                                    self.voltage_slider_b.value() / self.iterator,
                                    self.reference_voltage, self.gain, self.is_bipolar)
        self.status_text.setText('Welcome!')

    # Changes the COM port so you can find the one your Arduino is on
    def change_com(self):
        controller.set_com(self.com_select.currentText())
        self.status_text.setText('Welcome!')


###################################################

#############
# EXECUTION #
#############

# Execute me
if __name__ == '__main__':
    app = QApplication(sys.argv)

    nice = Application()

    app.exec_()

    # Resets the DAC outputs to 0 upon closing
    controller.send_voltage(controller.DAC_2, 0, nice.reference_voltage, nice.gain, nice.is_bipolar)

    sys.exit()

