# Libraries
from machine import I2C
from machine import reset
from lcd_api import LcdApi
from i2c_lcd import I2cLcd
from mfrc522 import MFRC522
from rotary import Rotary
from copy import deepcopy
import time
import math
import sys



# Kütüphane Değişkenleri
ekran_adres = 0x3F
ekran_satir = 2
ekran_sutun = 16
ekran_sda = machine.Pin(16)
ekran_scl = machine.Pin(17)

rfid_rst = 0
rfid_cs = 1
rfid_sck = 2
rfid_mosi = 3
rfid_miso = 4

encoder_sw = 6
encoder_data = 7
encoder_clk = 8

# Program Değişkenleri

# seçeneği seçmek için bas çek, geri gitmek için 500 ms basılı tut, reset atmak için 10 sn basılı tut

# Menü
menu_id = [0,0]
son_menu_id = [-1,-1]
ana_menu_nesneleri = ['Etiket Bilgisi', 'Etiket Kopyala', 'Etiket Olustur','Tarih Sifirla','Uzunluk Sifirla','Uzunluk Degisti', 'Rengi Degistir']



# Seçim butonu
btn_basilma = 0
btn_birakilma = -1


# RFID Değişkenleri
rfid_defaultKey = [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF]
okunan_kart = { 'serino' : '0', 'renk' : -1, 'uretim_tarihi' : 0, 'acilma_tarihi' : 0, 'son_kullanma_tarihi' : 0, 'filament_uzunlugu' : 0, 'agirlik' : 0}
gosterilen_kart_bilgisi = 0
son_gosterilen_kart_bilgisi = -1

kaynak_kart = {'renk' : [], 'uretim' : [], 'acilma' : [], 'kalan' : []}

yeni_kart = {'renk' : [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
               'uretim' : [0x60, 0x46, 0x4D, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
               'acilma' : [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
               'kalan' : [0x00, 0x02, 0x98, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]}
yeni_uzunluk = 170 # metre cinsinden. en son mm ye çevrilecek!...

renkler = ['Beyaz', 'Siyah', 'Kirmizi', 'Yesil', 'Mavi', 'Sari', 'Gri', 'Diger']
secilen_renk = 0




# LCD
i2c = I2C(0, sda=ekran_sda, scl=ekran_scl, freq=400000)
lcd = I2cLcd(i2c, ekran_adres, ekran_satir, ekran_sutun)
menu_ok = bytearray([0x00,0x10,0x18,0x1C,0x1E,0x1C,0x18,0x10])
lcd.custom_char(0, menu_ok)
print("Ekran tanımlandı..")

# RFID
rfid = MFRC522(spi_id=0,sck=rfid_sck,miso=rfid_miso,mosi=rfid_mosi,cs=rfid_cs,rst=rfid_rst)
print("MFRC522 tanımlandı.")

# Encoder
encoder = Rotary(encoder_sw, encoder_data, encoder_clk)

# Fonksiyonlar

# LCD ekran için metni ortalar...
def metinOrtala(metin):
    say = len(metin)
    yeni_metin = ""
    bosluk = 0
    if say % 2 == 1:
        say = say + 1
    if say < 16:
        bosluk = (16 - say) / 2
    if bosluk != 0:
        for i in range(bosluk):
            yeni_metin += " "
        yeni_metin += metin
    else:
        yeni_metin = metin
    
    return yeni_metin

# Filament renklerini söyler...
def renkSoyle(kod):
    global renkler
    
    if kod >= 0 and kod < len(renkler):
        return renkler[kod]
    else:
        return renkler[-1]

# karttan okunan blockların ilk 4 değerini decimal e çevirir
def hexToInt16(data):
    veri = ""
    for i in range(4):
        hexvalue = hex(data[i])[2:]
        if len(hexvalue) == 1:
            veri += "0" + hexvalue
        elif hexvalue == "0":
            veri += "00"
        else:
            veri += hexvalue
    print(veri)
    return int(veri, 16)

def encoder_changed(change):
    global btn_birakilma, btn_basilma, menu_id, yeni_uzunluk, secilen_renk, renkler
    
    # Encoder saat yönünde ilerlediğinde...
    if change == Rotary.ROT_CW:
        
        # Ana menüde isek!
        if menu_id[0] == 0:
            menu_id[1] = menu_id[1] + 1
            if menu_id[1] >= len(ana_menu_nesneleri):
                menu_id[1] = 0
        
        # Okunan kartın bilgilerinde dolaşmak için
        elif menu_id[0] == 2:
            menu_id[1] = menu_id[1] + 1
            if menu_id[1] >= len(okunan_kart):
                menu_id[1] = 0
                
        # Uzunluk değerini değiştirmek için...
        elif menu_id[0] == 5:
            yeni_uzunluk = yeni_uzunluk + 10
            lcd.move_to(0,1)
            lcd.putstr("                ")
            lcd.move_to(0,1)
            lcd.putstr(metinOrtala(str(yeni_uzunluk) + " m"))
            
        elif menu_id[0] == 6:
            secilen_renk += 1
            if secilen_renk >= len(renkler):
                secilen_renk = 0
            lcd.move_to(0,1)
            lcd.putstr("                ")
            lcd.move_to(0,1)
            lcd.putstr(metinOrtala(renkSoyle(secilen_renk)))
        
    elif change == Rotary.ROT_CCW:
        
        # Ana Menüde isek
        if menu_id[0] == 0:
            menu_id[1] = menu_id[1] - 1
            if menu_id[1] < 0:
                menu_id[1] = len(ana_menu_nesneleri) - 1
        
        
        # Okunan kartın bilgilerinde dolaşmak için
        elif menu_id[0] == 2:
            menu_id[1] = menu_id[1] - 1
            if menu_id[1] < 0:
                menu_id[1] = len(okunan_kart) - 1
        
        # uzunluk değerini değiştirmek için
        elif menu_id[0] == 5:
            yeni_uzunluk = yeni_uzunluk - 10
            lcd.move_to(0,1)
            lcd.putstr("                ")
            lcd.move_to(0,1)
            lcd.putstr(metinOrtala(str(yeni_uzunluk) + " m"))
        
        # renk değerini değiştirmek için
        elif menu_id[0] == 6:
            secilen_renk -= 1
            if secilen_renk < 0:
                secilen_renk = len(renkler) - 1
            lcd.move_to(0,1)
            lcd.putstr("                ")
            lcd.move_to(0,1)
            lcd.putstr(metinOrtala(renkSoyle(secilen_renk)))
        
    elif change == Rotary.SW_PRESS:
        # Düğmeye basıldığında zamanı al...
        btn_basilma = time.ticks_ms()
        
    elif change == Rotary.SW_RELEASE:
        # Düğmeye bırakıldığında zamanı al. Süre 500 ms den az ise seçim yap, fazla ise geri git...
        btn_birakilma = time.ticks_ms()
        if time.ticks_diff(btn_birakilma, btn_basilma) > 10000:
            reset()
        elif time.ticks_diff(btn_birakilma, btn_basilma) > 500:
            print('geri') # burası daha sonra düzenlenecek...
            if menu_id[0] == 0 and menu_id[1] != 0:
                # başa sarıyoruz...
                menu_id[1] = 0
            elif menu_id[0] != 0:
                menu_id = [0,0]
        else:
            print('sec')
            
            if menu_id[0] == 0:
                if menu_id[1] == 0:
                    menu_id = [1,0]# Etiket Bilgisi, Kart Okutma Ekranı
                elif menu_id[1] == 1:
                    menu_id = [3,0] # Kart Kopyalama, Kart Okutma Ekranı
                elif menu_id[1] == 2:
                    menu_id = [4,0] # Yeni kart oluşturma Ekranı
                elif menu_id[1] == 3:
                    menu_id = [4,1] # Tarih sıfırlama
                elif menu_id[1] == 4:
                    menu_id = [4,2] # uzunluk sıfırlama
                elif menu_id[1] == 5:
                    menu_id = [5,0] # Uzunluk Değiştir
                elif menu_id[1] == 6:
                    menu_id = [6,0] # Renk Değiştir
            
            elif menu_id[0] == 5:
                # kaydetmesi için menüye yollayalım.
                menu_id = [5,1]
                
            elif menu_id[0] == 6:
                # kaydetmesi için menüye yollayalım...
                menu_id = [6,1]
            
        btn_birakilma = -1
        btn_basilma = 0
        
encoder.add_handler(encoder_changed)


lcd.putstr(metinOrtala("Arcelik Filament"))
lcd.putstr(metinOrtala("Hack  Tool"))

time.sleep(2) # 2 sn. uyu

# Anasayfa Gösterimi menu_id = [0,0]
def anasayfa_gosterimi():
    global son_menu_id, menu_id
    
    # ekranda gösterilecek 2 nesneyi belirle...
    if menu_id[1] == len(ana_menu_nesneleri) -1:
        # son nesnedeyiz
        lcd.putstr(chr(0) + ana_menu_nesneleri[menu_id[1]])
        lcd.move_to(0,1)
        lcd.putstr(" " + ana_menu_nesneleri[0])  
    else:
        lcd.putstr(chr(0) + ana_menu_nesneleri[menu_id[1]])
        lcd.move_to(0,1)
        lcd.putstr(" " + ana_menu_nesneleri[menu_id[1] + 1])
    son_menu_id[0] = menu_id[0]
    son_menu_id[1] = menu_id[1]


# Kartı Okutun Menüsü  menu_id = [1,0]
def kart_okutun():
    global son_menu_id, menu_id, rfid_defaultKey, okunan_kart
    lcd.putstr(metinOrtala("Lutfen Filamenti"))
    lcd.move_to(0,1)
    lcd.putstr(metinOrtala("Yerlestirin"))
    devam = False
    baslat = time.ticks_ms()
    while True:
        # Kart okutulmazsa süre bari bitsin...
        bitir = time.ticks_ms()
        if time.ticks_diff(bitir, baslat) > 10000:
            print("süre bitti")
            break
        
        # kartı okumaya çalışalım...
        rfid.init()
        (stat, tag_type) = rfid.request(rfid.REQIDL)
        if stat == rfid.OK:
            (stat, uid) = rfid.SelectTagSN()
            if stat == rfid.OK:
                
                okunan_kart['serino'] = ""
                for i in range(4):
                    okunan_kart['serino'] += hex(uid[i])[2:]
                
                (stat, renkkodu) = rfid.readSectorBlock(uid, 1, 4, keyA=rfid_defaultKey)
                if stat == rfid.OK:
                    # sectorBlock aslında bir dizi isteğin karakterini içinden alabiliyoruz.
                    #print("renk kodu: ")
                    #print(renkkodu)
                    renk = hexToInt16(renkkodu)
                    #print("renk: " + str(renk))
                    okunan_kart['renk'] = renk
                    
                    (stat, uretimkodu) = rfid.readSectorBlock(uid, 2, 8, keyA=rfid_defaultKey)
                    if stat == rfid.OK:
                        
                        #print("üretim kodu: ")
                        #print(uretimkodu)
                        uretim = hexToInt16(uretimkodu)
                        #print("üretim tarihi: " + str(uretim))
                        okunan_kart['uretim_tarihi'] = uretim
                        
                        (stat, acilmakodu) = rfid.readSectorBlock(uid, 2, 9, keyA=rfid_defaultKey)
                        if stat == rfid.OK:
                            #print("açılma kodu: ")
                            #print(acilmakodu)
                            acilma = hexToInt16(acilmakodu)
                            #print("açılma tarihi: " + str(acilma))
                            okunan_kart['acilma_tarihi'] = acilma
                            
                            okunan_kart['son_kullanma_tarihi'] = acilma + 7776000
                                                        
                            (stat, uzunlukkodu) = rfid.readSectorBlock(uid, 2, 10, keyA=rfid_defaultKey)
                            if stat == rfid.OK:
                                #print("uzunluk kodu: ")
                                #print(uzunlukkodu)
                                uzunluk = hexToInt16(uzunlukkodu)
                                #print("filament uzunluğu: " + str(uzunluk))
                                okunan_kart['filament_uzunlugu'] = uzunluk
                                
                                okunan_kart['agirlik'] = math.floor((uzunluk * 500) / 170000)
                                
                                devam = True
                                break
                            else:
                                print("Filament uzunluğu okunamadı...")
                                break
                        else:
                            print("Filamentin açılma tarihi okunamadı...")
                            break
                        
                    else:
                        print("Üretim tarihi okunamadı...")
                        break
                    
                else:
                    print("Renk değeri okunamadı...")
                    break
            else:
                print("UID okunamadı")
                break
        else:
            # Şimdilik birşey yapma. RFID okuma isteği başlatılamadı...
            print("etiketin okutulması bekleniyor...")
    son_menu_id[0] = menu_id[0]
    son_menu_id[1] = menu_id[1]
    if devam:
        menu_id = [2,0]
    else:
        menu_id = [0,0]

# Kart Bilgilerini Göster  menu_id = [2,0]
def kart_bilgilerini_goster():
    global son_menu_id, menu_id, okunan_kart
    
    if menu_id[1] == 0:
        lcd.putstr(metinOrtala("RFID Seri No"))
        lcd.move_to(0,1)
        lcd.putstr(metinOrtala(okunan_kart['serino'].upper()))
    elif menu_id[1] == 1:
        lcd.putstr(metinOrtala("Filament Rengi"))
        lcd.move_to(0,1)
        lcd.putstr(metinOrtala(renkSoyle(okunan_kart['renk'])))
    elif menu_id[1] == 2:
        lcd.putstr(metinOrtala("Uretim Tarihi"))
        lcd.move_to(0,1)
        t = time.localtime(okunan_kart['uretim_tarihi'])
        lcd.putstr(metinOrtala(str(t[2]) + "." + str(t[1]) + "." + str(t[0])))
    elif menu_id[1] == 3:
        lcd.putstr(metinOrtala("Acilma Tarihi"))
        lcd.move_to(0,1)
        t = time.localtime(okunan_kart['acilma_tarihi'])
        lcd.putstr(metinOrtala(str(t[2]) + "." + str(t[1]) + "." + str(t[0])))
    elif menu_id[1] == 4:
        lcd.putstr(metinOrtala("Son Kul Tarihi"))
        lcd.move_to(0,1)
        t = time.localtime(okunan_kart['son_kullanma_tarihi'])
        lcd.putstr(metinOrtala(str(t[2]) + "." + str(t[1]) + "." + str(t[0])))
    elif menu_id[1] == 5:
        lcd.putstr(metinOrtala("Kalan Uzunluk"))
        lcd.move_to(0,1)
        mm = okunan_kart['filament_uzunlugu']
        meter = 0
        centimeter = 0
        if mm != 0:
            meter = math.floor(mm / 1000)
            centimeter = mm % meter
        lcd.putstr(metinOrtala(str(meter) + "m " + str(centimeter) + "cm"))
    elif menu_id[1] == 6:
        lcd.putstr(metinOrtala("Kalan Miktar"))
        lcd.move_to(0,1)
        lcd.putstr(metinOrtala(str(okunan_kart['agirlik']) + " gr"))
        
    son_menu_id[0] = menu_id[0]
    son_menu_id[1] = menu_id[1]

def kopyalanacak_karti_koy():
    # Kopyalanak kartın bilgilerini okuyalım..
    global son_menu_id, menu_id, rfid_defaultKey, kaynak_kart
    lcd.putstr(metinOrtala("Kopyalanacak"))
    lcd.move_to(0,1)
    lcd.putstr(metinOrtala("Filamenti  Koyun"))
    devam = False
    baslat = time.ticks_ms()
    while True:
        bitir = time.ticks_ms()
        if time.ticks_diff(bitir, baslat) > 10000:
            print("süre bitti")
            break
        
        # kartı okumaya çalışalım
        rfid.init()
        (stat, tag_type) = rfid.request(rfid.REQIDL)
        if stat == rfid.OK:
            uid = ""
            (stat, uid) = rfid.SelectTagSN()
            if stat == rfid.OK:
                #print(uid)
                
                (stat, renkkodu) = rfid.readSectorBlock(uid, 1, 4, keyA=rfid_defaultKey)
                if stat == rfid.OK:
                    #print(renkkodu)
                    kaynak_kart["renk"] = renkkodu
                    
                    (stat, uretimkodu) = rfid.readSectorBlock(uid, 2, 8, keyA=rfid_defaultKey)
                    
                    if stat == rfid.OK:
                        #print(uretimkodu)
                        kaynak_kart["uretim"] = uretimkodu
                        
                        (stat, acilmakodu) = rfid.readSectorBlock(uid, 2, 9, keyA=rfid_defaultKey)
                        
                        if stat == rfid.OK:
                            #print(acilmakodu)
                            kaynak_kart["acilma"] = acilmakodu
                            
                            (stat, kalankodu) = rfid.readSectorBlock(uid, 2, 10, keyA=rfid_defaultKey)
                            
                            if stat == rfid.OK:
                                #print(kalankodu)
                                kaynak_kart["kalan"] = kalankodu
                                
                                #print(kaynak_kart)
                                devam = True
                                break
                            else :
                                print("sector 2 block 10 okunamadı")
                                break 
                        else:
                            print("sector 2 block 8 okunamadı")
                            break
                    else:
                        print("sector 2 block 8 okunamadı")
                        break
                    
                else:
                    print("sector 1 block 4 okunamadı")
                    break
            else:
                print("uid okunamadı")
                break
        else:
            print("etiketin okutulması bekleniyor")
        
    son_menu_id[0] = menu_id[0]
    son_menu_id[1] = menu_id[1]
    if devam:
        menu_id = [3,1]
    else:
        menu_id = [3,3]
            
    
def yazilacak_karti_koy(yeni=False):
    # yazılacak kartın bilgilerini okuyalım..
    global son_menu_id, menu_id, rfid_defaultKey, kaynak_kart, yeni_kart
    
    if yeni:
        kart = deepcopy(yeni_kart)
    else:
        kart = deepcopy(kaynak_kart)
    
    lcd.putstr(metinOrtala("Yazilacak"))
    lcd.move_to(0,1)
    lcd.putstr(metinOrtala("Filamenti  Koyun"))
    devam = False
    baslat = time.ticks_ms()
    
    while time.ticks_diff(time.ticks_ms(), baslat) < 2000:
        pass
    
    baslat = time.ticks_ms()
    
    
    while True:
        bitis = time.ticks_ms()
        
        if time.ticks_diff(bitis, baslat) > 10000:
            print("yazma süresi bitti")
            break
        
        rfid.init()
        (stat, tag_type) = rfid.request(rfid.REQIDL)
        if stat == rfid.OK:
            uid = ""
            (stat, uid) = rfid.SelectTagSN()
            if stat == rfid.OK:
                
                absoluteBlock = 4
                status = rfid.auth(rfid.AUTHENT1A, absoluteBlock, rfid_defaultKey, uid)
                
                if status == rfid.OK:
                    
                    status = rfid.write(absoluteBlock, kart["renk"])
                    
                    if status == rfid.OK:
                        
                        print("block 4 başarıyla yazıldı")
                        absoluteBlock = 8
                        status = rfid.auth(rfid.AUTHENT1A, absoluteBlock, rfid_defaultKey, uid)
                        if status == rfid.OK:
                            status = rfid.write(absoluteBlock, kart["uretim"])
                            if status == rfid.OK:
                                print("block 8 başarıyla yazıldı")
                                
                                absoluteBlock = 9
                                status = rfid.auth(rfid.AUTHENT1A, absoluteBlock, rfid_defaultKey, uid)
                                if status == rfid.OK:
                                    status = rfid.write(absoluteBlock, kart["acilma"])
                                    if status == rfid.OK:
                                        print("block 9 başarıyla yazıldı")
                                        
                                        absoluteBlock = 10
                                        status = rfid.auth(rfid.AUTHENT1A, absoluteBlock, rfid_defaultKey, uid)
                                        if status == rfid.OK:
                                            status = rfid.write(absoluteBlock, kart["kalan"])
                                            if status == rfid.OK:
                                                print("block 10 başarıyla yazıldı")
                                                
                                                devam = True
                                                break 
                                            else:
                                                print("block 10 yazılamadı...")
                                                break
                                        else:
                                            print("block 10 yazma için yetkilendirilemedi...")
                                            break
                                    else:
                                        print("block 9 yazılamadı...")
                                        break
                                else:
                                    print("block 9 yazma için yetkilendirilemedi")
                                    break
                            else:
                                print("block 8 yazılamadı...")
                                break
                        else:
                            print("block 8 yazmak için yetkilendirilemedi")
                            break
                    else:
                        print("block 4 yazılamadı...")
                        break
                else:
                    print("block 4 yetkilendirilemedi")
                    break
            else:
                print("uid okunamadı")
                break
        else:
            print("kartın okutulması bekleniyor...")
    
    son_menu_id[0] = menu_id[0]
    son_menu_id[1] = menu_id[1]
    if devam:
        menu_id[0] = 3
        menu_id[1] = 2
    else:
        menu_id[0] = 3
        menu_id[1] = 3

def bilgi_degistir(block, sifirla=True, data=[]):
    global son_menu_id, menu_id, rfid_defaultKey, yeni_kart, secilen_renk
    lcd.putstr(metinOrtala("Lutfen"))
    lcd.move_to(0,1)
    lcd.putstr(metinOrtala("Filamenti  Koyun"))
    
    devam = False
    baslat = time.ticks_ms()
    
    while True:
        bitis = time.ticks_ms()
        if time.ticks_diff(bitis, baslat) > 10000:
            print("süre bitti")
            break
        
        rfid.init()
        (stat, tag_type) = rfid.request(rfid.REQIDL)
        if stat == rfid.OK:
            (stat, uid) = rfid.SelectTagSN()
            if stat == rfid.OK:
                # Şimdi bloğu bulalım. Sıfırlamayı bulalım. datayı bulalım. sonra ona göre devam edelim...
                print(block)
                
                veri = []
                if sifirla:
                    if block == 9:
                        # tarih
                        veri = deepcopy(yeni_kart["acilma"])
                    elif block == 10:
                        # uzunluk. standart 170m yani 500 gr
                        veri = deepcopy(yeni_kart["kalan"])
                else:
                    # gelen veri burada da hex e dönüştürülebilir. ya da direk dizi olarak gelebilir. its your choice!
                    if block == 10:
                        uzunluk = yeni_uzunluk * 1000
                        
                        u = hex(uzunluk).lstrip("0x").upper()
                        if len(u) < 8:
                            for i in range(8-len(u)):
                                u = "0" + u
                        
                        print(u)
                        veri = []
                        veri = deepcopy(yeni_kart["kalan"])
                        veri[0] = int(u[:2], 16)
                        veri[1] = int(u[2:4], 16)
                        veri[2] = int(u[4:6], 16)
                        veri[3] = int(u[6:8], 16)
                    
                    elif block == 4:
                        
                        veri = []
                        veri = deepcopy(yeni_kart['renk'])
                        veri[3] = secilen_renk
                    
                    print(veri)
                        
                        
                
                stat = rfid.auth(rfid.AUTHENT1A, block, rfid_defaultKey, uid)
                if stat == rfid.OK:
                    stat = rfid.write(block, veri)
                    if stat == rfid.OK:
                        print("Block " + str(block) + " başarıyla yazıldı.")
                        devam = True
                        break
                    else:
                        print("Block " + str(block) + " yazım başarısız!")
                        break
                else:
                    print("yetkilendirme sağlanamadı...")
                    break
            else:
                print("UID okunamadı....")
                break
        else:
            print("Kartın okutulması bekleniyor...")
    
    son_menu_id[0] = menu_id[0]
    son_menu_id[1] = menu_id[1]
    if devam:
        menu_id[0] = 3
        menu_id[1] = 2
    else:
        menu_id[0] = 3
        menu_id[1] = 3

def uzunluk_degistir_goster():
    global son_menu_id, menu_id, yeni_uzunluk
    lcd.putstr(metinOrtala("Uzunluk Degeri"))
    lcd.move_to(0,1)
    lcd.putstr(metinOrtala(str(yeni_uzunluk) + " m"))
    
    son_menu_id[0] = menu_id[0]
    son_menu_id[1] = menu_id[1]


def renk_degistir_goster():
    global son_menu_id, menu_id, secilen_renk
    lcd.putstr(metinOrtala("Filament Rengi"))
    lcd.move_to(0,1)
    lcd.putstr(metinOrtala(renkSoyle(secilen_renk)))
    
    son_menu_id[0] = menu_id[0]
    son_menu_id[1] = menu_id[1]

def islem_basarili():
    global son_menu_id, menu_id
    lcd.putstr(metinOrtala("Islem  Basariyla"))
    lcd.move_to(0,1)
    lcd.putstr(metinOrtala("Gerceklestirildi"))
    baslat = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), baslat) < 3000:
        pass
    son_menu_id[0] = menu_id[0]
    son_menu_id[1] = menu_id[1]
    menu_id = [0,0]

def islem_basarisiz():
    global son_menu_id, menu_id
    lcd.putstr(metinOrtala("Islem Sirasinda"))
    lcd.move_to(0,1)
    lcd.putstr(metinOrtala("Hata Olustu"))
    baslat = time.ticks_ms()
    while time.ticks_diff(time.ticks_ms(), baslat) < 3000:
        pass
    son_menu_id[0] = menu_id[0]
    son_menu_id[1] = menu_id[1]
    menu_id = [0,0]


# Ana kod dönüşü...
try:
    while True:
        # Ana sayfa için
        if son_menu_id[0] != menu_id[0] or son_menu_id[1] != menu_id[1]:
            # Ekranı temizleyelim..
            lcd.clear()
            # Ana menü üzerinde işlem yapıyorsak...
            if menu_id[0] == 0:
                # ana sayfa menülerini göster...
                anasayfa_gosterimi()
            elif menu_id[0] == 1 and menu_id[1] == 0:
                # Kartı yaklaştırın menüsünü getir.
                kart_okutun()    
            elif menu_id[0] == 2:
                # kartın bilgilerini göster
                kart_bilgilerini_goster()
            elif menu_id[0] == 3:
                # Kart Okuma
                if menu_id[1] == 0:
                    kopyalanacak_karti_koy()
                # Okunan Kartı Yeni Karta Yazma
                elif menu_id[1] == 1:
                    yazilacak_karti_koy(False)
                # İşlem başarılı menüsü
                elif menu_id[1] == 2:
                    islem_basarili()
                # İşlem başarısız menüsü
                elif menu_id[1] == 3:
                    islem_basarisiz()
            elif menu_id[0] == 4:
                # Yeni kart Oluşturma
                if menu_id[1] == 0:
                    yazilacak_karti_koy(True)
                # tarih sıfırlamaca
                elif menu_id[1] == 1:
                    bilgi_degistir(9, sifirla=True)
                # Uzunluk sifirlamaca...
                elif menu_id[1] == 2:
                    bilgi_degistir(10, sifirla=True)
            elif menu_id[0] == 5:
                if menu_id[1] == 0:
                    uzunluk_degistir_goster()
                elif menu_id[1] == 1:
                    bilgi_degistir(10, sifirla=False)
                    
            elif menu_id[0] == 6:
                if menu_id[1] == 0:
                    renk_degistir_goster()
                elif menu_id[1] == 1:
                    bilgi_degistir(4, sifirla=False)
                    



except KeyboardInterrupt:
    print("Bye")

            

