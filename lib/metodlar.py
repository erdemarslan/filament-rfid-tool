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