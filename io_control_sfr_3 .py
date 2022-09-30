from turtle import color
import serial.tools.list_ports
import serial
import PySimpleGUI as sg
import time
from sfrcontrol_registers328p import *
ser = serial.Serial()  #Global tanımlanmalı
# gösterilecek ikonlar için mevcut scriptin yolunu bul
import pathlib
from pathlib import Path
script_path = Path(__file__, '..').resolve()


#Globals 
adc_init_flag = False
analog_win_open = False # Analog pencere açık/kapalı flag
pwm_win_open = False # PWM Pencere açık/kapalı flag
analog_izleme_min = 1023
analog_izleme_max = 0
analog_izleme_toplamdeger = 0
analog_okuma_sayisi = 0
# analog okuma globals 
adc_read0 = 0
adc_read1 = 0
adc_read2 = 0
adc_read3 = 0
adc_read4 = 0
adc_read5 = 0
# current working directory
print(pathlib.Path().absolute())
def serial_ports():
    ports = serial.tools.list_ports.comports()
    seri_port = []
    for p in ports:
        print(p.device)
        seri_port.append(p.device)
    return seri_port
########################
def serial_baglan():
    com_deger = value[0]
    baud_deger = value[1]
    global ser
    ser = serial.Serial(com_deger, baud_deger, timeout=0.1, parity=serial.PARITY_NONE, stopbits = serial.STOPBITS_ONE , bytesize = serial.EIGHTBITS, rtscts=0)
    #Timeout ayarlanmazsa Arduino ile doğru çalışmaz..!
    window["-BAGLANDI_TEXT-"].update('Bağlandı...')
#* Yazmaç Okuma-Yazma Fonksiyonları 

# seri port komutlar
bayt_oku = b'\x00'
bayt_yaz = b'\x01'


def sfr_read(sfr):
    seri_gonder = bayt_oku + sfr 
    ser.write(seri_gonder)
    return int.from_bytes(ser.read(1), "big")

def sfr_bit_read(sfr, bit):
    sfr_deger = sfr_read(sfr)
    return (sfr_deger >> bit) & 1

def sfr_write(sfr, val):
    seri_gonder = bayt_yaz + sfr + (val.to_bytes(1, 'big'))
    ser.write(seri_gonder)

def sfr_bit_set(sfr, bit):
    sfr_deger = sfr_read(sfr)
    sfr_deger = sfr_deger | (1<<bit)
    sfr_write(sfr, sfr_deger)

def sfr_bit_reset(sfr, bit):
    sfr_deger = sfr_read(sfr)
    sfr_deger = sfr_deger & ~(1<<bit)
    sfr_write(sfr, sfr_deger)



#* ADC fonksiyonları 

def adc_init(refs):
    sfr_write(DDRC, 0)
    sfr_write(ADCSRA, ((1<<ADPS2) | (1<<ADPS1) | (1<<ADPS0))) # ADC prescaler 128
    sfr_write(ADMUX, (refs << 6)) # ADC referans voltaji AVCC
    sfr_bit_set(ADCSRA, ADEN) # ADC enable
    sfr_bit_set(ADCSRA, ADSC) # ADC start conversion

def read_adc(channel):
    admux_okuma = sfr_read(ADMUX)
    admux_okuma = admux_okuma & 0xF0
    admux_okuma = admux_okuma | channel
    sfr_write(ADMUX, admux_okuma)
    sfr_bit_set(ADCSRA, ADSC) # okumayi baslat
    while (sfr_read(ADCSRA)) & (1<<ADSC): # okuma bitene kadar bekle
        continue
    return (sfr_read(ADCL)) | (sfr_read(ADCH) << 8)

def map_range(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
#* Ekran Layout Tanımları

#* PWM Tanımlama 
def pwm_init():
    window['d3_text'].update(text_color='red')
    window['d9_text'].update(text_color='red')
    window['d10_text'].update(text_color='red')
    window['d11_text'].update(text_color='red')
    #d3 arayüz ayarları
    window['key_d3_in'].update(disabled=True)
    window['key_d3_out'].update(value=True)
    window['key_d3_out'].update(disabled=True)
    window['key_d3_high'].update(disabled=True)
    window['key_d3_low'].update(disabled=True)
    #d9 arayüz ayarları
    window['key_d9_in'].update(disabled=True)
    window['key_d9_out'].update(value=True)
    window['key_d9_out'].update(disabled=True)
    window['key_d9_high'].update(disabled=True)
    window['key_d9_low'].update(disabled=True)
    #d3 arayüz ayarları
    window['key_d10_in'].update(disabled=True)
    window['key_d10_out'].update(value=True)
    window['key_d10_out'].update(disabled=True)
    window['key_d10_high'].update(disabled=True)
    window['key_d10_low'].update(disabled=True)
    #d3 arayüz ayarları
    window['key_d11_in'].update(disabled=True)
    window['key_d11_out'].update(value=True)
    window['key_d11_out'].update(disabled=True)
    window['key_d11_high'].update(disabled=True)
    window['key_d11_low'].update(disabled=True)

    # Timer Ayarları
    #Çıkış olarak ayakları tanıma
    sfr_bit_set(DDRD, 3)
    sfr_bit_set(DDRB, 1)
    sfr_bit_set(DDRB, 2)
    sfr_bit_set(DDRB, 3)

    # Timer 2 ayarları
    sfr_write(TCCR2A, ((1<<WGM20) | (1<<COM2A1) | (1<<COM2B1))) # Fast PWM, non-inverting
    sfr_bit_set(TCCR2B, CS20) # Prescaler 1

    # Timer 1 ayarları
    sfr_bit_set(TCCR1A, COM1A1)
    sfr_bit_set(TCCR1A, COM1B1)
    sfr_bit_set(TCCR1B, WGM13)
    sfr_bit_set(TCCR1B, CS10)
    icr_value = pwm_window.read()[1]
    icr_value = int(icr_value['key_slider_icr1'])
    sfr_write(ICR1L, icr_value)


def pwm_deinit():
    window['d3_text'].update(text_color='black')
    window['d9_text'].update(text_color='black')
    window['d10_text'].update(text_color='black')
    window['d11_text'].update(text_color='black')
    #d3 arayüz ayarları
    window['key_d3_in'].update(disabled=False)
    window['key_d3_in'].update(value=True)
    window['key_d3_out'].update(value=False)
    window['key_d3_out'].update(disabled=False)
    window['key_d3_high'].update(disabled=False)
    window['key_d3_low'].update(disabled=False)
    #d9 arayüz ayarları
    window['key_d9_in'].update(disabled=False)
    window['key_d9_out'].update(value=False)
    window['key_d9_in'].update(value=True)
    window['key_d9_out'].update(disabled=False)
    window['key_d9_high'].update(disabled=False)
    window['key_d9_low'].update(disabled=False)
    #d3 arayüz ayarları
    window['key_d10_in'].update(disabled=False)
    window['key_d10_out'].update(value=False)
    window['key_d10_in'].update(value=True)
    window['key_d10_out'].update(disabled=False)
    window['key_d10_high'].update(disabled=False)
    window['key_d10_low'].update(disabled=False)
    #d3 arayüz ayarları
    window['key_d11_in'].update(disabled=False)
    window['key_d11_out'].update(value=False)
    window['key_d11_in'].update(value=True)
    window['key_d11_out'].update(disabled=False)
    window['key_d11_high'].update(disabled=False)
    window['key_d11_low'].update(disabled=False)
    
    sfr_write(TCCR1A, 0)
    sfr_write(TCCR1B, 0)
    sfr_write(TCCR2A, 0)
    sfr_write(TCCR2B, 0)

sg.theme("Reddit")

serial_frame = [ [sg.Text("Port Seçiniz:"), sg.Combo(serial_ports(), size=(10,1)),
            sg.Text("Baud Seçiniz:"), sg.Combo(["110","300","600","1200", "2400", "4800", "9600", "14400", "19200", "38400", "57600", "115200", "128000", "256000", "500000"], default_value=500000), 
            sg.Button(button_text="Bağlan", key="-BAGLAN-", size=(10,1)),
            sg.Text("", size=(42,1), font=('Arial Black', 10, 'italic'), key="-BAGLANDI_TEXT-")]
        ]

io_frame = [ [sg.Text("I/O ADI", size=(10,1), justification="left", font=('Arial Black', 10, 'bold')),
            sg.Text("  Giriş/Çıkış", size=(18,1), justification="left", font=('Arial Black', 10, 'bold')), sg.Text("Manuel Kontrol", size=(15,1), justification="left", font=('Arial Black', 10, 'bold')),
            sg.Text("I/O Canlı Durum", size=(12,1), justification="left", font=('Arial Black', 10, 'bold'))],
            [sg.HorizontalSeparator()],
            
            [sg.Text("D2/PORTD2", size=(10,1), font=('Arial', 10), justification="left", key="d2_text"),
            sg.Radio('Giriş', 'd2_io_dir', size=(5, 1), key='key_d2_in', font=('Arial', 10), default=True),
            sg.Radio('Çıkış', 'd2_io_dir', size=(8, 1), key='key_d2_out', font=('Arial', 10)),
            sg.Radio('LOW', 'd2_io_out', size=(5, 1), key='key_d2_low', font=('Arial', 10), default=True),
            sg.Radio('HIGH', 'd2_io_out', size=(12, 1), key='key_d2_high', font=('Arial', 10)),
            sg.Image(filename=script_path.joinpath("gri_led.png"), key="key_d2_led", size=(30,30))],[sg.HorizontalSeparator()],

           [sg.Text("D3/PORTD3", size=(10,1), font=('Arial', 10), justification="left", key="d3_text"),
            sg.Radio('Giriş', 'd3_io_dir', size=(5, 1), key='key_d3_in', font=('Arial', 10), default=True),
            sg.Radio('Çıkış', 'd3_io_dir', size=(8, 1), key='key_d3_out', font=('Arial', 10)),
            sg.Radio('LOW', 'd3_io_out', size=(5, 1), key='key_d3_low', font=('Arial', 10), default=True),
            sg.Radio('HIGH', 'd3_io_out', size=(12, 1), key='key_d3_high', font=('Arial', 10)),
            sg.Image(filename=script_path.joinpath("gri_led.png"), key="key_d3_led", size=(30,30))],[sg.HorizontalSeparator()],

            [sg.Text("D4/PORTD4", size=(10,1), font=('Arial', 10), justification="left", key="d4_text"),
            sg.Radio('Giriş', 'd4_io_dir', size=(5, 1), key='key_d4_in', font=('Arial', 10), default=True),
            sg.Radio('Çıkış', 'd4_io_dir', size=(8, 1), key='key_d4_out', font=('Arial', 10)),
            sg.Radio('LOW', 'd4_io_out', size=(5, 1), key='key_d4_low', font=('Arial', 10), default=True),
            sg.Radio('HIGH', 'd4_io_out', size=(12, 1), key='key_d4_high', font=('Arial', 10)),
            sg.Image(filename=script_path.joinpath("gri_led.png"), key="key_d4_led", size=(30,30))],[sg.HorizontalSeparator()],

            [sg.Text("D5/PORTD5", size=(10,1), font=('Arial', 10), justification="left", key="d5_text"),
            sg.Radio('Giriş', 'd5_io_dir', size=(5, 1), key='key_d5_in', font=('Arial', 10), default=True),
            sg.Radio('Çıkış', 'd5_io_dir', size=(8, 1), key='key_d5_out', font=('Arial', 10)),
            sg.Radio('LOW', 'd5_io_out', size=(5, 1), key='key_d5_low', font=('Arial', 10), default=True),
            sg.Radio('HIGH', 'd5_io_out', size=(12, 1), key='key_d5_high', font=('Arial', 10)),
            sg.Image(filename=script_path.joinpath("gri_led.png"), key="key_d5_led", size=(30,30))],[sg.HorizontalSeparator()],

            [sg.Text("D6/PORTD6", size=(10,1), font=('Arial', 10), justification="left", key="d6_text"),
            sg.Radio('Giriş', 'd6_io_dir', size=(5, 1), key='key_d6_in', font=('Arial', 10), default=True),
            sg.Radio('Çıkış', 'd6_io_dir', size=(8, 1), key='key_d6_out', font=('Arial', 10)),
            sg.Radio('LOW', 'd6_io_out', size=(5, 1), key='key_d6_low', font=('Arial', 10), default=True),
            sg.Radio('HIGH', 'd6_io_out', size=(12, 1), key='key_d6_high', font=('Arial', 10)),
            sg.Image(filename=script_path.joinpath("gri_led.png"), key="key_d6_led", size=(30,30))],[sg.HorizontalSeparator()],

            [sg.Text("D7/PORTD7", size=(10,1), font=('Arial', 10), justification="left", key="d7_text"),
            sg.Radio('Giriş', 'd7_io_dir', size=(5, 1), key='key_d7_in', font=('Arial', 10), default=True),
            sg.Radio('Çıkış', 'd7_io_dir', size=(8, 1), key='key_d7_out', font=('Arial', 10)),
            sg.Radio('LOW', 'd7_io_out', size=(5, 1), key='key_d7_low', font=('Arial', 10), default=True),
            sg.Radio('HIGH', 'd7_io_out', size=(12, 1), key='key_d7_high', font=('Arial', 10)),
            sg.Image(filename=script_path.joinpath("gri_led.png"), key="key_d7_led", size=(30,30))],[sg.HorizontalSeparator()],

            [sg.Text("D8/PORTB0", size=(10,1), font=('Arial', 10), justification="left", key="d8_text"),
            sg.Radio('Giriş', 'd8_io_dir', size=(5, 1), key='key_d8_in', font=('Arial', 10), default=True),
            sg.Radio('Çıkış', 'd8_io_dir', size=(8, 1), key='key_d8_out', font=('Arial', 10)),
            sg.Radio('LOW', 'd8_io_out', size=(5, 1), key='key_d8_low', font=('Arial', 10), default=True),
            sg.Radio('HIGH', 'd8_io_out', size=(12, 1), key='key_d8_high', font=('Arial', 10)),
            sg.Image(filename=script_path.joinpath("gri_led.png"), key="key_d8_led", size=(30,30))],[sg.HorizontalSeparator()],

            [sg.Text("D9/PORTB1", size=(10,1), font=('Arial', 10), justification="left", key="d9_text"),
            sg.Radio('Giriş', 'd9_io_dir', size=(5, 1), key='key_d9_in', font=('Arial', 10), default=True),
            sg.Radio('Çıkış', 'd9_io_dir', size=(8, 1), key='key_d9_out', font=('Arial', 10)),
            sg.Radio('LOW', 'd9_io_out', size=(5, 1), key='key_d9_low', font=('Arial', 10), default=True),
            sg.Radio('HIGH', 'd9_io_out', size=(12, 1), key='key_d9_high', font=('Arial', 10)),
            sg.Image(filename=script_path.joinpath("gri_led.png"), key="key_d9_led", size=(30,30))],[sg.HorizontalSeparator()],

            [sg.Text("D10/PORTB2", size=(10,1), font=('Arial', 10), justification="left", key="d10_text"),
            sg.Radio('Giriş', 'd10_io_dir', size=(5, 1), key='key_d10_in', font=('Arial', 10), default=True),
            sg.Radio('Çıkış', 'd10_io_dir', size=(8, 1), key='key_d10_out', font=('Arial', 10)),
            sg.Radio('LOW', 'd10_io_out', size=(5, 1), key='key_d10_low', font=('Arial', 10), default=True),
            sg.Radio('HIGH', 'd10_io_out', size=(12, 1), key='key_d10_high', font=('Arial', 10)),
            sg.Image(filename=script_path.joinpath("gri_led.png"), key="key_d10_led", size=(30,30))],[sg.HorizontalSeparator()],

            [sg.Text("D11/PORTB3", size=(10,1), font=('Arial', 10), justification="left", key="d11_text"),
            sg.Radio('Giriş', 'd11_io_dir', size=(5, 1), key='key_d11_in', font=('Arial', 10), default=True),
            sg.Radio('Çıkış', 'd11_io_dir', size=(8, 1), key='key_d11_out', font=('Arial', 10)),
            sg.Radio('LOW', 'd11_io_out', size=(5, 1), key='key_d11_low', font=('Arial', 10), default=True),
            sg.Radio('HIGH', 'd11_io_out', size=(12, 1), key='key_d11_high', font=('Arial', 10)),
            sg.Image(filename=script_path.joinpath("gri_led.png"), key="key_d11_led", size=(30,30))],[sg.HorizontalSeparator()],

            [sg.Text("D12/PORTB4", size=(10,1), font=('Arial', 10), justification="left", key="d12_text"),
            sg.Radio('Giriş', 'd12_io_dir', size=(5, 1), key='key_d12_in', font=('Arial', 10), default=True),
            sg.Radio('Çıkış', 'd12_io_dir', size=(8, 1), key='key_d12_out', font=('Arial', 10)),
            sg.Radio('LOW', 'd12_io_out', size=(5, 1), key='key_d12_low', font=('Arial', 10), default=True),
            sg.Radio('HIGH', 'd12_io_out', size=(12, 1), key='key_d12_high', font=('Arial', 10)),
            sg.Image(filename=script_path.joinpath("gri_led.png"), key="key_d12_led", size=(30,30))],[sg.HorizontalSeparator()],

            [sg.Text("D13/PORTB5", size=(10,1), font=('Arial', 10), justification="left", key="d13_text"),
            sg.Radio('Giriş', 'd13_io_dir', size=(5, 1), key='key_d13_in', font=('Arial', 10), default=True),
            sg.Radio('Çıkış', 'd13_io_dir', size=(8, 1), key='key_d13_out', font=('Arial', 10)),
            sg.Radio('LOW', 'd13_io_out', size=(5, 1), key='key_d13_low', font=('Arial', 10), default=True),
            sg.Radio('HIGH', 'd13_io_out', size=(12, 1), key='key_d13_high', font=('Arial', 10)),
            sg.Image(filename=script_path.joinpath("gri_led.png"), key="key_d13_led", size=(30,30))],[sg.HorizontalSeparator()],
            
            [sg.Button(button_text="Analog Okuma", font=('Arial', 14, 'bold'), size=(24,10), key="key_analog_islemler"),
            sg.Button(button_text="PWM", font=('Arial', 14, 'bold'), size=(24,10), key="key_pwm")]
            ]


#* Analog pencere tasarımı
analog_frame = [[sg.Text("Analog Kanal", font=('Arial', 12, 'bold'), justification="left", size=(20, 1)), sg.Text("Okunan Değer", font=('Arial', 12, 'bold'), justification="right")],
                [sg.Text("A0", size=(17,1), font=('Arial', 16), justification="left", key="key_a0_ad"), sg.Text("", size=(13,1), font=('Arial', 16), justification="right", key="key_a0_deger")],
                [sg.HorizontalSeparator()],
                [sg.Text("A1", size=(17,1), font=('Arial', 16), justification="left", key="key_a1_ad"), sg.Text("", size=(13,1), font=('Arial', 16), justification="right", key="key_a1_deger")],
                [sg.HorizontalSeparator()],
                [sg.Text("A2", size=(17,1), font=('Arial', 16), justification="left", key="key_a2_ad"), sg.Text("", size=(13,1), font=('Arial', 16), justification="right", key="key_a2_deger")],
                [sg.HorizontalSeparator()],
                [sg.Text("A3", size=(17,1), font=('Arial', 16), justification="left", key="key_a3_ad"), sg.Text("", size=(13,1), font=('Arial', 16), justification="right", key="key_a3_deger")],
                [sg.HorizontalSeparator()],
                [sg.Text("A4", size=(17,1), font=('Arial', 16), justification="left", key="key_a4_ad"), sg.Text("", size=(13,1), font=('Arial', 16), justification="right", key="key_a4_deger")],
                [sg.HorizontalSeparator()],
                [sg.Text("A5", size=(17,1), font=('Arial', 16), justification="left", key="key_a5_ad"), sg.Text("", size=(13,1), font=('Arial', 16), justification="right", key="key_a5_deger")],
                [sg.HorizontalSeparator()],
                [sg.Checkbox("A0", size=(2,1), font=('Arial', 12), key="key_a0_check"), sg.Checkbox("A1", size=(2,1), font=('Arial', 12), key="key_a1_check"),
                sg.Checkbox("A2", size=(2,1), font=('Arial', 12), key="key_a2_check"), sg.Checkbox("A3", size=(2,1), font=('Arial', 12), key="key_a3_check"),
                sg.Checkbox("A4", size=(2,1), font=('Arial', 12), key="key_a4_check"), sg.Checkbox("A5", size=(2,1), font=('Arial', 12), key="key_a5_check")]
            ]

analog_ayar_frame = [[sg.Checkbox("Gerilim Olarak Göster", size=(20,1), font=('Arial', 12), key="key_analog_ayar_volt"),
                    sg.Checkbox("Değer Aralığı Belirle", size=(20,1), font=('Arial', 12), key="key_analog_ayar_deger")],
                    [sg.Text("Min", size=(3,1), font=('Arial', 12), justification="left", key="key_analog_ayar_min_deger_ad"),
                    sg.Input("0", size=(10,1), font=('Arial', 12), justification="right", key="key_analog_ayar_min_deger"),
                    sg.Text("Max", size=(3,1), font=('Arial', 12), justification="left", key="key_analog_ayar_max_deger_ad"),
                    sg.Input("1023", size=(10,1), font=('Arial', 12), justification="right", key="key_analog_ayar_max_deger")],
                    [sg.Text("Referans:"), sg.Radio("5V", "analog_ayar_ref", size=(3,1), font=('Arial', 10), key="key_analog_ayar_ref_5v", default=True),
                    sg.Radio("AREF", "analog_ayar_ref", size=(5,1), font=('Arial', 10), key="key_analog_ayar_aref"), 
                    sg.Radio("1.1V", "analog_ayar_ref", size=(5,1), font=('Arial', 10), key="key_analog_ayar_ref_1v1")]

]

analog_comparator_frame = [[sg.Checkbox("Karşılaştırıcı Etkin", size=(15,1), font=('Arial', 12), key="key_ac_etkin", default=True ), sg.Checkbox("Bandgap Fix(1.1V)", size=(15,1), font=('Arial', 12), key="key_fix_etkin")],
                           [sg.Text("Karşılaştırıcı Canlı Durum: "), sg.Image(filename=script_path.joinpath("kirmizi_led.png"), key="key_ac_led", size=(30,30))],

]

analog_izleme_frame = [[sg.Checkbox("İzleme", size=(6,1), font=('Arial', 10), key="key_analog_izleme_etkin", default=False),
                    sg.Combo(['A0', 'A1', 'A2', 'A3', 'A4', 'A5'], size=(5,1), font=('Arial', 10, 'bold'), key="key_analog_izleme_kanal", default_value="A0")],
                    [sg.Text("En Düşük", size=(26,1), font=('Arial', 10, 'bold'), justification="left", key="key_analog_izleme_min_label"), sg.Text("", size=(13,1), font=('Arial', 10, 'bold'), justification="right", key="key_analog_izleme_min_deger")],
                    [sg.HorizontalSeparator()],
                    [sg.Text("En Yüksek", size=(26,1), font=('Arial', 10, 'bold'), justification="left", key="key_analog_izleme_max_label"), sg.Text("", size=(13,1), font=('Arial', 10, 'bold'), justification="right", key="key_analog_izleme_max_deger")],
                    [sg.HorizontalSeparator()],
                    [sg.Text("Ortalama", size=(26,1), font=('Arial', 10, 'bold'), justification="left", key="key_analog_izleme_ort_label"), sg.Text("", size=(13,1), font=('Arial', 10, 'bold'), justification="right", key="key_analog_izleme_ortalama_deger")],
                    [sg.HorizontalSeparator()]

                      
                    ]


#* PWM Pencere Tasarımı
t1_pwm_frame = [[sg.Text("ICR1", size=(4,2), font=('Arial', 12), justification="center", key="key_icr1_ad"),
            sg.Slider((1,255), key='key_slider_icr1', size=(30, 20), orientation='h', enable_events=True, disable_number_display=False, default_value=255)],
            [sg.Text("(D9)", size=(4,2), font=('Arial', 12), justification="center", key="key_ocr1a_ad"),
            sg.Slider((0,100), key='key_slider_ocr1a', size=(30, 20), orientation='h', enable_events=True, disable_number_display=False, default_value=0)],
            [sg.Text("(D10)", size=(4,2), font=('Arial', 12), justification="center", key="key_ocr1b_ad"),
            sg.Slider((0,100), key='key_slider_ocr1b', size=(30, 20), orientation='h', enable_events=True, disable_number_display=False, default_value=0)]
]

t2_pwm_frame = [ [sg.Text("(D11)", size=(4,2), font=('Arial', 12), justification="center", key="key_icr2_ad"),
                sg.Slider((0,100), key='key_slider_ocr2a', size=(30, 20), orientation='h', enable_events=True, disable_number_display=False, default_value=0)],
                [sg.Text("(D3)", size=(4,2), font=('Arial', 12), justification="center", key="key_ocr2a_ad"),
                sg.Slider((0,100), key='key_slider_ocr2b', size=(30, 20), orientation='h', enable_events=True, disable_number_display=False, default_value=0)]

]

# Pwm etkin checkbox'u event üretecek ona göre zamanlayıcılar konfigüre edilecek ve dijital kotnrol devre dışı bırakılacak
# Devre dışı bırakıldığında ise dijital kontrol devreye girecek, zamanlayıcılar sıfırlanacak 
pwm_ayar_frame = [[sg.Checkbox("PWM Etkin", size=(10,1), font=('Arial', 12), key="key_pwm_etkin", default=False, enable_events=True)]

            ]

layout =[ [sg.Frame("Seri Port Bağlantı", serial_frame, size=(580, 60))],
        [sg.Frame("I/O Kontrol", io_frame, size=(580, 620))]
        ]
#Y 685 px olacak
analog_layout = [[sg.Frame("Analog Girişler", analog_frame, size=(350,335))],
                [sg.Frame("Analog Ayarları", analog_ayar_frame, size=(350, 117))],
                [sg.Frame("Analog Karşılaştırıcı", analog_comparator_frame, size=(350, 90))],
                [sg.Frame("Analog İzleme", analog_izleme_frame, size=(350, 156))]
                ]

pwm_layout = [[sg.Frame("T1 PWM", t1_pwm_frame, size=(350, 180))],
                [sg.Frame("T2 PWM", t2_pwm_frame, size=(350, 130))],
                [sg.Frame("PWM Ayarları", pwm_ayar_frame, size=(350, 50))]
        ]
window = sg.Window("Python ile AVR Kontrol", layout, finalize=True)

#* Analog penceresini oluştur ve gizle
analog_window = sg.Window("Analog Okuma", analog_layout, finalize=True, no_titlebar = True)
analog_window.hide();

pwm_window = sg.Window("PWM İşlemleri", pwm_layout, finalize=True, no_titlebar = True)
pwm_window.hide();


while True:
    event, value = window.read(timeout=0) 
    analog_event, analog_value = analog_window.read(timeout=0)
    pwm_event, pwm_value = pwm_window.read(timeout=0)
    if event == sg.WIN_CLOSED or event == 'Exit':
        break    
    if event == "-BAGLAN-":
        if (value[0] == ""):
            sg.popup("Bir Port Seçiniz!", title="Hata", custom_text="Tamam") 
        elif (value[1] == ""):
            sg.popup("Baud Oranını Seçiniz!", title="Hata", custom_text="Tamam")
        else:
            serial_baglan()
    if event == 'key_analog_islemler':
        if analog_win_open == False:
            analog_win_open = True
            analog_window.UnHide()
            analog_window.move(window.current_location()[0]-373, window.current_location()[1]+1)
        else:
            analog_win_open = False 
            analog_window.Hide()
    if event == 'key_pwm' and ser.is_open:
        if pwm_win_open == False:
            pwm_win_open = True
            pwm_window.UnHide()
            pwm_window.move(window.current_location()[0]+619, window.current_location()[1]+1)
        else:
            pwm_win_open = False 
            pwm_window.Hide()

    if pwm_event == 'key_pwm_etkin':
        if pwm_value['key_pwm_etkin'] == True:
            pwm_init()
        else:
            pwm_deinit()

    if pwm_event == 'key_slider_ocr1a':
        sfr_write(OCR1AL, int(pwm_value['key_slider_ocr1a']))
    if pwm_event == 'key_slider_ocr1b':
        sfr_write(OCR1BL, int(pwm_value['key_slider_ocr1b']))
    if pwm_event == 'key_slider_ocr2a':
        sfr_write(OCR2A, int(pwm_value['key_slider_ocr2a']))
    if pwm_event == 'key_slider_ocr2b':
        sfr_write(OCR2B, int(pwm_value['key_slider_ocr2b']))
    #* IO Durumlarını Ekranda Canlı Olarak Gösterme 
    if ser.is_open:
        pind = sfr_read(PIND)
        pinb = sfr_read(PINB)
        #pinc = sfr_read(PINC)
        #* C portu IO işleri için kullanım dışı bırakıldı
        #datasheette giriş/çıkış fark etmeksizin pin yazmacından okunabilir yazmakta. 
        # ilk 2 bit UART ayrılmıştır. 

        #* Bit okumalarında sağa kaydırmaya gerek duyulmamıştır, 0'dan farklı ise TRUE sayılmıştır.
        #* IO Durumlarını ekranda canlı olarak gösterme.
        io_d2 = pind & (1<<2)
        if io_d2 == 0:
            window["key_d2_led"].update(filename=script_path.joinpath("gri_led.png"))
        else:
            window["key_d2_led"].update(filename=script_path.joinpath("yesil_led.png"))
        io_d3 = pind & (1<<3)
        if io_d3 == 0:
            window["key_d3_led"].update(filename=script_path.joinpath("gri_led.png"))
        else:
            window["key_d3_led"].update(filename=script_path.joinpath("yesil_led.png"))
        io_d4 = pind & (1<<4)
        if io_d4 == 0:
            window["key_d4_led"].update(filename=script_path.joinpath("gri_led.png"))
        else:
            window["key_d4_led"].update(filename=script_path.joinpath("yesil_led.png"))
        io_d5 = pind & (1<<5)
        if io_d5 == 0:
            window["key_d5_led"].update(filename=script_path.joinpath("gri_led.png"))
        else:
            window["key_d5_led"].update(filename=script_path.joinpath("yesil_led.png"))
        io_d6 = pind & (1<<6)
        if io_d6 == 0:
            window["key_d6_led"].update(filename=script_path.joinpath("gri_led.png"))
        else:
            window["key_d6_led"].update(filename=script_path.joinpath("yesil_led.png"))
        io_d7 = pind & (1<<7)
        if io_d7 == 0:
            window["key_d7_led"].update(filename=script_path.joinpath("gri_led.png"))
        else:
            window["key_d7_led"].update(filename=script_path.joinpath("yesil_led.png"))
        io_d8 = pinb & (1<<0)
        if io_d8 == 0:
            window["key_d8_led"].update(filename=script_path.joinpath("gri_led.png"))
        else:
            window["key_d8_led"].update(filename=script_path.joinpath("yesil_led.png"))
        io_d9 = pinb & (1<<1)
        if io_d9 == 0:
            window["key_d9_led"].update(filename=script_path.joinpath("gri_led.png"))
        else:
            window["key_d9_led"].update(filename=script_path.joinpath("yesil_led.png"))
        io_d10 = pinb & (1<<2)
        if io_d10 == 0:
            window["key_d10_led"].update(filename=script_path.joinpath("gri_led.png"))
        else:
            window["key_d10_led"].update(filename=script_path.joinpath("yesil_led.png"))
        io_d11 = pinb & (1<<3)
        if io_d11 == 0:
            window["key_d11_led"].update(filename=script_path.joinpath("gri_led.png"))
        else:
            window["key_d11_led"].update(filename=script_path.joinpath("yesil_led.png"))
        io_d12 = pinb & (1<<4)
        if io_d12 == 0:
            window["key_d12_led"].update(filename=script_path.joinpath("gri_led.png"))
        else:
            window["key_d12_led"].update(filename=script_path.joinpath("yesil_led.png"))
        io_d13 = pinb & (1<<5)
        if io_d13 == 0:
            window["key_d13_led"].update(filename=script_path.joinpath("gri_led.png"))
        else:
            window["key_d13_led"].update(filename=script_path.joinpath("yesil_led.png"))

        #* Pin Giriş/Çıkış Ayarla
        if value["key_d2_out"] == True:
            sfr_bit_set(DDRD, DDD2)
        else:
            sfr_bit_reset(DDRD, DDD2)
        #* Pin HIGH/LOW Ayarla
        if value["key_d2_high"] == True:
            sfr_bit_set(PORTD, PORTD2)
        else:
            sfr_bit_reset(PORTD, PORTD2)

        if value['key_d3_out'] == True:
            sfr_bit_set(DDRD, DDD3)
        else:
            sfr_bit_reset(DDRD, DDD3)
        if value['key_d3_high'] == True:
            sfr_bit_set(PORTD, PORTD3)
        else:
            sfr_bit_reset(PORTD, PORTD3)
        
        if value['key_d4_out'] == True:
            sfr_bit_set(DDRD, DDD4)
        else:
            sfr_bit_reset(DDRD, DDD4)
        
        if value['key_d4_high'] == True:
            sfr_bit_set(PORTD, PORTD4)
        else:
            sfr_bit_reset(PORTD, PORTD4)
        
        if value['key_d5_out'] == True:
            sfr_bit_set(DDRD, DDD5)
        else:
            sfr_bit_reset(DDRD, DDD5)
        
        if value['key_d5_high'] == True:
            sfr_bit_set(PORTD, PORTD5)
        else:
            sfr_bit_reset(PORTD, PORTD5)
        
        if value['key_d6_out'] == True:
            sfr_bit_set(DDRD, DDD6)
        else:
            sfr_bit_reset(DDRD, DDD6)
        
        if value['key_d6_high'] == True:
            sfr_bit_set(PORTD, PORTD6)
        else:
            sfr_bit_reset(PORTD, PORTD6)
        
        if value['key_d7_out'] == True:
            sfr_bit_set(DDRD, DDD7)
        else:
            sfr_bit_reset(DDRD, DDD7)

        if value['key_d7_high'] == True:
            sfr_bit_set(PORTD, PORTD7)
        else:
            sfr_bit_reset(PORTD, PORTD7)

        if value['key_d8_out'] == True:
            sfr_bit_set(DDRB, DDB0)
        else:
            sfr_bit_reset(DDRB, DDB0)
        
        if value['key_d8_high'] == True:
            sfr_bit_set(PORTB, PORTB0)
        else:
            sfr_bit_reset(PORTB, PORTB0)
        
        if value['key_d9_out'] == True:
            sfr_bit_set(DDRB, DDB1)
        else:
            sfr_bit_reset(DDRB, DDB1)
        
        if value['key_d9_high'] == True:
            sfr_bit_set(PORTB, PORTB1)
        else:
            sfr_bit_reset(PORTB, PORTB1)

        if value['key_d10_out'] == True:
            sfr_bit_set(DDRB, DDB2)
        else:
            sfr_bit_reset(DDRB, DDB2)
        
        if value['key_d10_high'] == True:
            sfr_bit_set(PORTB, PORTB2)
        else:
            sfr_bit_reset(PORTB, PORTB2)
        
        if value['key_d11_out'] == True:
            sfr_bit_set(DDRB, DDB3)
        else:
            sfr_bit_reset(DDRB, DDB3)

        if value['key_d11_high'] == True:
            sfr_bit_set(PORTB, PORTB3)
        else:
            sfr_bit_reset(PORTB, PORTB3)

        if value['key_d12_out'] == True:
            sfr_bit_set(DDRB, DDB4)
        else:
            sfr_bit_reset(DDRB, DDB4)
        
        if value['key_d12_high'] == True: 
            sfr_bit_set(PORTB, PORTB4)
        else:
            sfr_bit_reset(PORTB, PORTB4)

        if value['key_d13_out'] == True:
            sfr_bit_set(DDRB, DDB5)
        else:
            sfr_bit_reset(DDRB, DDB5)
        
        if value['key_d13_high'] == True:
            sfr_bit_set(PORTB, PORTB5)
        else:
            sfr_bit_reset(PORTB, PORTB5)

        #********************* Analog Yazdırma işlemleri
        if analog_win_open == True:
            if analog_value['key_analog_ayar_ref_5v'] == True:
                refs = 1
            elif analog_value['key_analog_ayar_ref_1v1'] == True:
                refs = 3
            elif analog_value['key_analog_ayar_aref'] == True:
                refs = 0
            adc_init(refs)
            time.sleep(0.001)
            if analog_value['key_a0_check'] == True:
                adc_read0 = read_adc(0)
            if analog_value['key_a1_check'] == True:    
                adc_read1 = read_adc(1)
            if analog_value['key_a2_check'] == True:    
                adc_read2 = read_adc(2)
            if analog_value['key_a3_check'] == True:
                adc_read3 = read_adc(3)
            if analog_value['key_a4_check'] == True:
                adc_read4 = read_adc(4)
            if analog_value['key_a5_check'] == True:    
                adc_read5 = read_adc(5)
            #Analog okumalar yavaşlığa sebep olmakta, gereksiz okumalar engellenir. 
            analog_izleme_guncel = 0

            if analog_value['key_analog_izleme_etkin'] == True:
                if analog_value['key_analog_izleme_kanal'] == 'A0' and analog_value['key_a0_check'] == True:
                    analog_izleme_guncel = adc_read0

                if analog_value['key_analog_izleme_kanal'] == 'A1' and analog_value['key_a1_check'] == True:
                    analog_izleme_guncel = adc_read1

                if analog_value['key_analog_izleme_kanal'] == 'A2' and analog_value['key_a2_check'] == True:
                    analog_izleme_guncel = adc_read2

                if analog_value['key_analog_izleme_kanal'] == 'A3' and analog_value['key_a3_check'] == True:
                    analog_izleme_guncel = adc_read3

                if analog_value['key_analog_izleme_kanal'] == 'A4' and analog_value['key_a4_check'] == True:
                    analog_izleme_guncel = adc_read4

                if analog_value['key_analog_izleme_kanal'] == 'A5' and analog_value['key_a5_check'] == True:
                    analog_izleme_guncel = adc_read5
                
                if analog_izleme_guncel > analog_izleme_max:
                    analog_izleme_max = analog_izleme_guncel

                if analog_izleme_guncel < analog_izleme_min:
                    analog_izleme_min = analog_izleme_guncel

                analog_izleme_toplamdeger = analog_izleme_toplamdeger + analog_izleme_guncel
                analog_okuma_sayisi = analog_okuma_sayisi + 1
                adc_izleme_ort = analog_izleme_toplamdeger / analog_okuma_sayisi

                analog_window['key_analog_izleme_max_deger'].update(analog_izleme_max)
                analog_window['key_analog_izleme_min_deger'].update(analog_izleme_min)
                analog_window['key_analog_izleme_ortalama_deger'].update("{:4.3f}".format(adc_izleme_ort))

                
            # analog izleme etkin değilse hepsini sıfırla
            else:
                analog_window['key_analog_izleme_min_deger'].update("")
                analog_window['key_analog_izleme_max_deger'].update("")
                analog_window['key_analog_izleme_ortalama_deger'].update("")
                analog_izleme_min = 1023
                analog_izleme_max = 0
                analog_izleme_toplamdeger = 0
                analog_okuma_sayisi = 0
            

            v_ekleme = ""
            if analog_value['key_analog_ayar_volt'] == True:
                adc_read0 = adc_read0 * 0.0048828125
                adc_read1 = adc_read1 * 0.0048828125
                adc_read2 = adc_read2 * 0.0048828125
                adc_read3 = adc_read3 * 0.0048828125
                adc_read4 = adc_read4 * 0.0048828125
                adc_read5 = adc_read5 * 0.0048828125
                v_ekleme = "V"
            else:
                v_ekleme = ""
            #! Girilen değerleri geçerliliğini kontrol etme
            if analog_value['key_analog_ayar_deger'] == True:
                analog_window['key_analog_ayar_volt'].update(value=False)

                if analog_value['key_analog_ayar_max_deger'].isnumeric() == False or analog_value['key_analog_ayar_min_deger'].isnumeric() == False:
                    sg.Popup("Lütfen Değerleri Sayısal olarak giriniz")
                    analog_window['key_analog_ayar_max_deger'].update(value="0")
                    analog_window['key_analog_ayar_min_deger'].update(value="0")     

                else:
                    if(int(analog_value['key_analog_ayar_max_deger']) > 999999):
                        analog_window['key_analog_ayar_max_deger'].update(value=999999)
                        sg.Popup("Maksimum Değer 999999'dan büyük olamaz")
                    if(int(analog_value['key_analog_ayar_min_deger']) < 0):
                        analog_window['key_analog_ayar_min_deger'].update(value=0)
                        sg.Popup("Minimum Değer 0'dan küçük olamaz")

                    if(int(analog_value['key_analog_ayar_max_deger']) < int(analog_value['key_analog_ayar_min_deger'])):
                        analog_window['key_analog_ayar_max_deger'].update(value=analog_value['key_analog_ayar_min_deger'])
                        sg.Popup("Maksimum Değer Minimum Değerden küçük olamaz")
                

                
                    adc_read0 = map_range(adc_read0, 0, 1023, float(analog_value['key_analog_ayar_min_deger']), float(analog_value['key_analog_ayar_max_deger']))
                    adc_read1 = map_range(adc_read1, 0, 1023, float(analog_value['key_analog_ayar_min_deger']), float(analog_value['key_analog_ayar_max_deger']))
                    adc_read2 = map_range(adc_read2, 0, 1023, float(analog_value['key_analog_ayar_min_deger']), float(analog_value['key_analog_ayar_max_deger']))
                    adc_read3 = map_range(adc_read3, 0, 1023, float(analog_value['key_analog_ayar_min_deger']), float(analog_value['key_analog_ayar_max_deger']))
                    adc_read4 = map_range(adc_read4, 0, 1023, float(analog_value['key_analog_ayar_min_deger']), float(analog_value['key_analog_ayar_max_deger']))
                    adc_read5 = map_range(adc_read5, 0, 1023, float(analog_value['key_analog_ayar_min_deger']), float(analog_value['key_analog_ayar_max_deger']))

            if analog_value['key_a0_check'] == True:
                analog_window['key_a0_deger'].update("{:.3f}".format(adc_read0) + v_ekleme)
            else:
                analog_window['key_a0_deger'].update("")

            if analog_value['key_a1_check'] == True:
                analog_window['key_a1_deger'].update("{:.3f}".format(adc_read1) + v_ekleme)
            else:
                analog_window['key_a1_deger'].update("")

            if analog_value['key_a2_check'] == True:
                analog_window['key_a2_deger'].update("{:.3f}".format(adc_read2) + v_ekleme)
            else:
                analog_window['key_a2_deger'].update("")

            if analog_value['key_a3_check'] == True:
                analog_window['key_a3_deger'].update("{:.3f}".format(adc_read3) + v_ekleme)
            else:
                analog_window['key_a3_deger'].update("")

            if analog_value['key_a4_check'] == True:
                analog_window['key_a4_deger'].update("{:.3f}".format(adc_read4) + v_ekleme)
            else:
                analog_window['key_a4_deger'].update("")

            if analog_value['key_a5_check'] == True:
                analog_window['key_a5_deger'].update("{:.3f}".format(adc_read5) + v_ekleme)
            else:
                analog_window['key_a5_deger'].update("")

            #* Analog Comparator Gösterimi
            if analog_value['key_ac_etkin'] == True:
                sfr_bit_reset(ACSR, ACD)
            else:
                sfr_bit_set(ACSR, ACD)

            if analog_value['key_fix_etkin'] == True:
                sfr_bit_set(ACSR, ACBG)
            else:
                sfr_bit_reset(ACSR, ACBG)

            aco = sfr_bit_read(ACSR, ACO)

            if aco == 0:
                analog_window['key_ac_led'].update(filename=script_path.joinpath("kirmizi_led.png"))
            else:
                analog_window['key_ac_led'].update(filename=script_path.joinpath("yesil_led.png"))

        #* ************** PWM İşlemleri ******************
analog_window.hide()
pwm_window.hide()
analog_window.close()
pwm_window.close()
window.close()


