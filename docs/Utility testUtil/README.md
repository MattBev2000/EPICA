## Descrizione

Utility CLI che mette a disposizione dei comandi per gestire i sistemi CASES e EPICA.

Dalla versione 3.0 vengono fatte due compilazioni diverse, una per ogni sistema. I file compilati sono **testUtilC** per CASES e **testUtilE** per EPICA.

<br>

## Usage - opzioni

**Help**

Visualizza l'help dell'utility.
```
./testUtil -?
```
```
./testUtil --help
```

Risposta:
```
Usage: testUtil [OPTION...] COMMAND [PARAMETER...]

Utility CLI con vari comandi, in particolare per il DRIVER e i bus UART e I2C.
Copyright © 2026 ELAD S.r.l. All Rights Reserved.
________________________________________________________________

Options:

 The following options should be grouped together:
  -q, --quiet                Don't produce any output
  -r, --repeat               Repeat command indefinitely
  -v, --verbose              Produce verbose output

  -?, --help                 Give this help list
      --usage                Give a short usage message
  -V, --version              Print program version

________________________________________________________________

Comandi:

* COMMAND discovery: discovery delle schede tramite comandi seriali (UART)
                     e lettura di dati dalle EEPROM (I2C)
  Usage:
  testUtil [OPTION...] discovery

* COMMAND net-state: fornisce lo stato delle interfacce ethernet
                     e gli indirizzi IP in uso
  Usage:
  testUtil [OPTION...] net-state

----------------------------------------------------------------
* COMMAND send-data: permette di inviare dati (caratteri ASCII) sul bus
                     UART indicando la scheda indirizzata e di visualizzare
                     la risposta
  Usage:
  testUtil [OPTION...] send-data ADDR SUB_ADDR DATA
  ADDR    : 0-7 e 8 per la TICK
  SUB_ADDR: 0-1 (FPGA) o 9 (micro)
  DATA    : dati da inviare (caratteri ASCII, no '@')

* COMMAND send-fpga: permette di inviare un comando ad una FPGA indicando
                     la scheda indirizzata e di visualizzare la risposta
  Usage:
  testUtil [OPTION...] send-fpga ADDR SUB_ADDR COMMAND VALUE
  ADDR    : 0-7 e 8 per la TICK
  SUB_ADDR: 0 o 1 (FPGA 0 o FPGA 1)
  COMMAND : comando composto da una sola lettera maiuscola ('A' a 'Z)
  VALUE   : valore composto da 4 caratteri esadecimali ('0' a 'F')

----------------------------------------------------------------
* COMMAND eep-read-all: lettura dell'EEPROM della scheda indirizzata
  Usage:
  testUtil [OPTION...] eep-read-all ADDR [PAGE_IDX]
  ADDR    : 0 a 7 e 8 per le schede del bus, 9 per la EK26
  PAGE_IDX: solo per ADDR=9 (EK26): 0, 8, 16, ..., 248
            (Identification Page non gestita)

* COMMAND eep-read-page: lettura di una pagina dell'EEPROM della scheda
                         indirizzata
  Usage:
  testUtil [OPTION...] eep-read-page ADDR PAGE_IDX
  ADDR    : 0 a 7 e 8 per le schede del bus, 9 per la EK26
  PAGE_IDX: 0 a 15 per le schede del bus, 0 a 255 per la EK26
            (256 per la Identification Page)

* COMMAND eep-write-page: scrittura di una pagina dell'EEPROM della scheda
                          indirizzata
  Usage:
  testUtil [OPTION...] eep-write-page ADDR PAGE_IDX PAGE_BYTES
  ADDR      : 0 a 7 e 8 per le schede del bus, 9 per la EK26
  PAGE_IDX  : 0 a 15 per le schede del bus, 0 a 255 per la EK26
              (Identification Page non gestita)
  PAGE_BYTES: 16 byte in esadecimale (0011...FF) per le schede del bus
              32 byte in esadecimale (0001...0F1011...1F) per la EK26

----------------------------------------------------------------
* COMMAND reg-read: permette di leggere il valore di un registro del sistema
  Usage:
  testUtil [OPTION...] reg-read [REG_NAME]
  REG_NAME: nome del registro di cui si vuole leggere il valore,
            omettendo REG_NAME l'utility stampa la lista dei registri
            del sistema

* COMMAND reg-write: permette di scrivere il valore di un registro del sistema
  Usage:
  testUtil [OPTION...] reg-write [REG_NAME REG_VALUE]
  REG_NAME : nome del registro di cui si vuole scrivere il valore,
             omettendo REG_NAME (e REG_VALUE) l'utility stampa la lista dei
             registri del sistema
  REG_VALUE: valore che si vuole scrivere nel registro, formato:
             "aabb_ccdd" con aa, bb, cc, e dd i 4 byte del registro in
             esadecimale

* COMMAND reg-edit: permette di modificare il valore di un registro del
                    sistema
  Usage:
  testUtil [OPTION...] reg-edit [REG_NAME AND_MASK OR_MASK]
  REG_NAME: nome del registro di cui si vuole modificare il valore,
            omettendo REG_NAME (e AND_MASK e OR_MASK) l'utility stampa
            la lista dei registri del sistema
  AND_MASK: maschera AND da applicare al valore del registro, formato:
            "AND:aabb_ccdd" con aa, bb, cc, e dd i 4 byte in esadecimale
  OR_MASK : maschera OR da applicare al valore del registro, formato:
            "OR:aabb_ccdd" con aa, bb, cc, e dd i 4 byte in esadecimale

* COMMAND reg-dump: permette di leggere i valori di alcuni registri del
                    sistema
  Usage:
  testUtil [OPTION...] reg-dump

----------------------------------------------------------------
* COMMAND data-align: permette di allineare i dati per quanto riguarda la
                      gestione del DMA
  Usage:
  testUtil [OPTION...] data-align

* COMMAND data-sync: permette di fare la sincronizzazione dei dati per quanto
                     riguarda la gestione del DMA (esegue un discovery prima)
  Usage:
  testUtil [OPTION...] data-sync CHAN_NB
  CHAN_NB: numero del canale da sincronizzare (da 1 a 16) o allora 0 per
           sincronizzarli tutti

Report bugs to <info@eladit.com>.
```

<br />

**Usage**

Visualizza l'usage dell'utility.
```
./testUtil --usage
```
Risposta:
```
Usage: testUtil [-qrv?V] [--quiet] [--repeat] [--verbose] [--help] [--usage]
            [--version] COMMAND [PARAMETER...]
```

<br />

**Version**

Visualizza la versione dell'utility.
```
./testUtil -V
```
```
./testUtil --version
```
Risposta:
```
testUtil vX.Y
```

<br />

**Repeat**

Permette di ripettere il comando in continuazione. Viene aggiunto un ritardo di 0.5s tra un comando e l'altro. Per interrompere utilizzare la sequenza Ctrl+C.
```
sudo ./testUtil -r discovery
```
```
sudo ./testUtil --repeat discovery
```

<br />

**Verbose**

Visualizza maggiore informazioni sull'esecuzione del comando.
```
sudo ./testUtil -v discovery
```
```
sudo ./testUtil --verbose discovery
```

<br />

**Quiet**

Permette di non stampare nessuna informazione sull'esecuzione del comando.
```
sudo ./testUtil -q discovery
```
```
sudo ./testUtil --quiet discovery
```

<br />

## Usage - comandi

**Discovery delle schede**

Permette di effettuare il discovery delle schede del sistema chiedendone la lista tramite UART e leggendo alcune informazioni dalle EEPROM tramite I2C.

Usage:
```
sudo ./testUtil [OPTION...] discovery
```

<br />

Esempio con risposta:
```
sudo ./testUtil discovery
```
```
Discovery started...
Discovery:
* SYSTEM:     EPICA | CASES POLARIZED | CASES NOT POLARIZED (left) | CASES NOT POLARIZED (right) | UNKNOWN
* EK26 BOARD: (BOARD:CODE,ADDR)      (ERR:COMM_ERR) (FPGA:VERS,SYS,CHAN) (UID) (EEP:HW_INFO & SERIAL)
* BUS BOARD:  (MICRO:CODE,ADDR,VERS) (ERR:COMM_ERR) (FPGA:DATA_0,DATA_1) (UID) (EEP:HW_INFO & SERIAL)

SYSTEM:       CASES POLARIZED - error found, probable missing board(s)
EK: EK26      (BRD:E,3) (ERR:_) (F:09013,NP,2) (UID:72C3FF473230151744303312214038FF) (EEP:EK26 1.1,SL1F3H,EKFP 1.1,SL1F32)
S0:           (MIC:-,-,v0.0) (ERR:U_I) (F:----|----|----|----,----|----|----|----) (UID:) (EEP:,,,)
S1:           (MIC:-,-,v0.0) (ERR:U_I) (F:----|----|----|----,----|----|----|----) (UID:) (EEP:,,,)
S2:           (MIC:-,-,v0.0) (ERR:U_I) (F:----|----|----|----,----|----|----|----) (UID:) (EEP:,,,)
S3:           (MIC:-,-,v0.0) (ERR:U_I) (F:----|----|----|----,----|----|----|----) (UID:) (EEP:,,,)
S4:           (MIC:-,-,v0.0) (ERR:U_I) (F:----|----|----|----,----|----|----|----) (UID:) (EEP:,,,)
S5:           (MIC:-,-,v0.0) (ERR:U_I) (F:----|----|----|----,----|----|----|----) (UID:) (EEP:,,,)
S6: PBI5      (MIC:P,6,v1.1) (ERR:___) (F:____|____|____|____,614C|0402|00FF|2000) (UID:2941010EE888) (EEP:PBI5 1.2,SN1234,,)
S7: A20I2     (MIC:I,7,v1.1) (ERR:___) (F:7020|0511|0000|0000,7120|0511|0000|0000) (UID:2941010F15BB) (EEP:A20I2 1.1,SL1HBN,,)
TI: TICK      (MIC:T,8,v1.1) (ERR:___) (F:____|____|____|____,8180|0307|0000|0000) (UID:29410109DE9C) (EEP:TICK 1.2,SL1HDX,TICKFP 1.1,SL1F7B)
```
Codifica per CODE:
```
'-': scheda non riconosciuta o non presente
'A': AS20P2
'C': A20C5
'E': EK26
'F': IOHS(RX)
'G': IOHS(TX)
'I': A20I2
'P': PBI5
'T': TICK
'X': IOHS(RXTX)
```
Codifica per ADDR:
```
'-': dato non disponibile
'0' a '8': scheda presente
```
Codifica per COMM_ERR:
```
'___': nessun errore
'U__': errore UART verso il micro
'_U_': errore UART verso un FPGA
'__I': errore I2C
```

Codifica per VERS (FPGA EK26): 5 caratteri (es. "09013") o 5 trattini ("-----") se il dato non è disponibile.

Codifica per VERS (micro): versione nel formato "vX.Y" (con X e Y numeri), valore di default: "v0.0".

Codifica per SYS (tipo bitstream): "NP" per non polarizzato, "POL" per polarizzato o "UNK" se dato non valido. 

Codifica per CHAN (numero di canali): numero da 0 a 8.

<br />

___

**Stato interfacce ethernet**

Fornisce lo stato delle interfacce ethernet e gli indirizzi IP in uso.

Usage:
```
sudo ./testUtil [OPTION...] net-state
```

<br />

Esempio con risposta:
```
sudo ./testUtil net-state
```
```
Network settings:
eth0  flags  : UP:1, RUNNING:1
      address: 192.168.201.98
      netmask: 255.255.255.0
eth1  flags  : UP:1, RUNNING:1
      address: 192.168.202.98
      netmask: 255.255.255.0
```

<br />

___

**Invio dati bus UART**

Permette di inviare dati (caratteri ASCII) tramite UART indicando la scheda indirizzata.

Usage:
```
sudo ./testUtil [OPTION...] send-data ADDR SUB_ADDR DATA
```
>ADDR: 0-7 e 8 per la TICK\
SUB_ADDR: 0-1 (FPGA) o 9 (micro)\
DATA: dati da inviare (caratteri ASCII, no '@')

<br />

Esempio con risposta (micro):
```
sudo ./testUtil send-data 8 9 "HI;VSM;"
```
```
Answer received (28 byte): "HI8|T|TICK    ;.VSM001.001;."
```

Esempio con risposta (FPGA):
```
sudo ./testUtil send-data 8 0 "T000?"
```
```
Answer received (17 byte): "018003070000000?."
```

<br />

___

**Invio comando FPGA**

Permette di inviare un comando tramite UART ad una FPGA indicando la scheda indirizzata.

Usage:
```
sudo ./testUtil [OPTION...] send-fpga ADDR SUB_ADDR COMMAND VALUE
```
>ADDR: 0-7 e 8 per la TICK\
SUB_ADDR: 0 o 1 (FPGA 0 o FPGA 1)\
COMMAND: comando composto da una sola lettera maiuscola ('A' a 'Z)\
VALUE: valore composto da 4 caratteri esadecimali ('0' a 'F')

<br />

Esempio con risposta:
```
sudo ./testUtil send-fpga 6 1 A 0000
```
```
Answer received (17 byte): "614F040200002000 "
Board Addr: 6
FPGA Addr : 1
Board Code: 4
Spare     : F
Version   : 0402
Value     : 0000 2000
```

<br />

___

**Lettura EEPROM I2C**

Permette di leggere l'EEPROM della scheda indirizzata.

Usage:
```
sudo ./testUtil [OPTION...] eep-read-all ADDR [PAGE_IDX]
```
>ADDR: 0 a 7 e 8 per le schede del bus, 9 per la EK26\
PAGE_IDX: solo per ADDR=9 (EK26): 0, 8, 16, ..., 248 (Identification Page non gestita)

<br />

Esempio con risposta (EK26):
```
sudo ./testUtil eep-read-all 9 0
```
```
Read 256 bytes starting from page 0:
       0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F
0000: 45 4B 32 36 20 31 2E 31 00 00 00 00 00 00 00 00 53 4C 31 46 33 48 00 00 00 00 00 00 00 00 00 00
0020: 45 4B 46 50 20 31 2E 31 00 00 00 00 00 00 00 00 53 4C 31 46 33 32 00 00 00 00 00 00 00 00 00 00
0040: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
0060: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
0080: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
00A0: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
00C0: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
00E0: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
```

Esempio con risposta (scheda del bus):
```
sudo ./testUtil eep-read-all 0
```
```
Read 256 bytes starting from page 0:
     0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
00: 42 4F 41 52 44 20 31 2E 32 00 53 4C 31 41 42 43
10: 54 49 43 4B 46 50 20 31 2E 31 53 4E 31 32 33 34
20: 00 11 22 33 44 55 66 77 88 99 AA BB CC DD EE FF
30: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
40: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
50: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
60: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
70: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
80: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
90: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
A0: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
B0: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
C0: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
D0: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
E0: FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF FF
F0: FF FF FF FF FF FF FF FF FF FF 29 41 01 0E E8 88
```

<br />

___

**Lettura pagina EEPROM I2C**

Permette di leggere una pagina dell'EEPROM della scheda indirizzata.

Usage:
```
sudo ./testUtil [OPTION...] eep-read-page ADDR PAGE_IDX
```
>ADDR: 0 a 7 e 8 per le schede del bus, 9 per la EK26\
PAGE_IDX: 0 a 15 per le schede del bus, 0 a 255 per la EK26 (256 per la Identification Page)

<br />

Esempio con risposta (EK26):
```
sudo ./testUtil eep-read-page 9 0
```
```
Read 32 bytes from page 0:
       0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F
0000: 45 4B 32 36 20 31 2E 31 00 00 00 00 00 00 00 00 53 4C 31 46 33 48 00 00 00 00 00 00 00 00 00 00
```

Esempio con risposta (scheda del bus):
```
sudo ./testUtil eep-read-page 0 0
```
```
Read 16 bytes from page 0:
     0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
00: 42 4F 41 52 44 20 31 2E 32 00 53 4C 31 41 42 43
```

<br />

___

**Scrittura pagina EEPROM I2C**

Permette di scrivere una pagina dell'EEPROM della scheda indirizzata.

Usage:
```
sudo ./testUtil [OPTION...] eep-write-page ADDR PAGE_IDX PAGE_BYTES
```
>ADDR: 0 a 7 e 8 per le schede del bus, 9 per la EK26\
PAGE_IDX: 0 a 7 per le schede del bus, 0 a 255 per la EK26 (Identification Page non gestita)\
PAGE_BYTES: 16 byte in esadecimale (0011...FF) per le schede del bus, o 32 byte in esadecimale (0001...0F1011...1F) per la EK26

<br />

Esempio con risposta (EK26):
```
sudo ./testUtil eep-write-page 9 2 000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F
```
```
Write 32 bytes into page 2.
Read 32 bytes from page 2:
       0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F
0040: 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F
```

Esempio con risposta (scheda del bus):
```
sudo ./testUtil eep-write-page 0 2 00112233445566778899AABBCCDDEEFF
```
```
Write 16 bytes into page 2.
Read 16 bytes from page 2:
     0  1  2  3  4  5  6  7  8  9  A  B  C  D  E  F
20: 00 11 22 33 44 55 66 77 88 99 AA BB CC DD EE FF
```

<br />

NB: per poter scrivere dentro l'EEPROM della scheda EK26 è necessario che la scrittura sia abilitata al livello hardware, ci sono due metodi per abilitare la scrittura:
- aprire la seconda COM disponibile sul connettore micro USB e attivare il segnale DTR;
- chiudere il jumper JMP30 della scheda EK26.

<br />

___

**Lettura registro del sistema**

Permette di leggere il valore di un registro del sistema.

Usage:
```
sudo ./testUtil [OPTION...] reg-read [REG_NAME]
```
>REG_NAME: nome del registro di cui si vuole leggere il valore, omettendo REG_NAME l'utility stampa la lista dei registri del sistema

<br />

Esempio con risposta (lista registri):
```
sudo ./testUtil reg-read
```
```
reg13 fpga_ver               (r-)
reg14 axi_cfg0               (rw)
reg15 daq0                   (rw)
reg16 daq0_stat              (rw)
reg17 daq1                   (rw)
reg18 daq1_stat              (rw)
reg19 daq2                   (rw)
reg20 daq2_stat              (rw)
reg21 daq3                   (rw)
reg22 daq3_stat              (rw)
reg23 daq4                   (rw)
reg24 daq4_stat              (rw)
reg25 daq5                   (rw)
reg26 daq5_stat              (rw)
reg27 daq6                   (rw)
reg28 daq6_stat              (rw)
reg29 daq7                   (rw)
reg30 daq7_stat              (rw)
reg31 gen_stat               (rw)
reg32 pts                    (rw)
reg33 recorder               (rw)
reg34 recorder_stat          (rw)
```

Esempio con risposta (lettura):
```
sudo ./testUtil reg-read fpga_ver
```
```
reg13 fpga_ver 0230_9013
```

<br />

___

**Scrittura registro del sistema**

Permette di scrivere un valore dentro un registro del sistema.

Usage:
```
sudo ./testUtil [OPTION...] reg-write [REG_NAME REG_VALUE]
```
>REG_NAME: nome del registro nel quale si vuole scrivere il valore, omettendo REG_NAME (e REG_VALUE) l'utility stampa la lista dei registri del sistema\
REG_VALUE: valore da scrivere dentro il registro, formato: "aabb_ccdd" con aa, bb, cc, e dd i 4 byte del registro in esadecimale

<br />

Esempio con risposta (lista registri):
```
sudo ./testUtil reg-write
```
```
reg13 fpga_ver               (r-)
reg14 axi_cfg0               (rw)
reg15 daq0                   (rw)
reg16 daq0_stat              (rw)
reg17 daq1                   (rw)
reg18 daq1_stat              (rw)
reg19 daq2                   (rw)
reg20 daq2_stat              (rw)
reg21 daq3                   (rw)
reg22 daq3_stat              (rw)
reg23 daq4                   (rw)
reg24 daq4_stat              (rw)
reg25 daq5                   (rw)
reg26 daq5_stat              (rw)
reg27 daq6                   (rw)
reg28 daq6_stat              (rw)
reg29 daq7                   (rw)
reg30 daq7_stat              (rw)
reg31 gen_stat               (rw)
reg32 pts                    (rw)
reg33 recorder               (rw)
reg34 recorder_stat          (rw)
```

Esempio con risposta (scrittura):
```
sudo ./testUtil reg-write axi_cfg0 AABB_CCDD
```
```
reg14 axi_cfg0 AABB_CCDD
```

<br />

___

**Edit registro del sistema**

Permette di modificare un registro del sistema applicando sia una maschera in AND che una maschera in OR.

Usage:
```
sudo ./testUtil [OPTION...] reg-edit [REG_NAME AND_MASK OR_MASK]
```
>REG_NAME: nome del registro nel quale si vuole scrivere, omettendo REG_NAME (e AND_MASK e OR_MASK) l'utility stampa la lista dei registri del sistema\
AND_MASK: maschera AND da applicare al valore del registro, formato: "AND:aabb_ccdd" con aa, bb, cc, e dd i 4 byte in esadecimale della maschera\
OR_MASK: maschera OR da applicare al valore del registro, formato: "OR:aabb_ccdd" con aa, bb, cc, e dd i 4 byte in esadecimale della maschera

<br />

Esempio con risposta (lista registri):
```
sudo ./testUtil reg-edit
```
```
reg13 fpga_ver               (r-)
reg14 axi_cfg0               (rw)
reg15 daq0                   (rw)
reg16 daq0_stat              (rw)
reg17 daq1                   (rw)
reg18 daq1_stat              (rw)
reg19 daq2                   (rw)
reg20 daq2_stat              (rw)
reg21 daq3                   (rw)
reg22 daq3_stat              (rw)
reg23 daq4                   (rw)
reg24 daq4_stat              (rw)
reg25 daq5                   (rw)
reg26 daq5_stat              (rw)
reg27 daq6                   (rw)
reg28 daq6_stat              (rw)
reg29 daq7                   (rw)
reg30 daq7_stat              (rw)
reg31 gen_stat               (rw)
reg32 pts                    (rw)
reg33 recorder               (rw)
reg34 recorder_stat          (rw)
```

Esempio con risposta (edit registro):
```
sudo ./testUtil reg-edit daq0 AND:0003_F00F OR:0C02_9003
```
```
reg15 daq0 0C02_9003
```

<br />

___

**Dump registri del sistema**

Permette di leggere i valori di alcuni registri del sistema.

Usage:
```
sudo ./testUtil [OPTION...] reg-dump
```

<br />

Esempio con risposta:
```
sudo ./testUtil reg-dump
```
```
reg13 fpga_ver               0230_9013
reg14 axi_cfg0               0000_0000
reg15 daq0                   0000_0000
reg16 daq0_stat              13E8_13E8
reg17 daq1                   0000_0000
reg18 daq1_stat              0000_0000
reg19 daq2                   0000_0000
reg20 daq2_stat              0000_0000
reg21 daq3                   0000_0000
reg22 daq3_stat              0000_0000
reg23 daq4                   0000_0000
reg24 daq4_stat              0000_0000
reg25 daq5                   0000_0000
reg26 daq5_stat              0000_0000
reg27 daq6                   0000_0000
reg28 daq6_stat              0000_0000
reg29 daq7                   0000_0000
reg30 daq7_stat              0000_0000
reg31 gen_stat               0000_0000
reg32 pts                    0000_0000
reg33 recorder               0000_0000
reg34 recorder_stat          0000_0000
```

<br />

___

**Allineamento dei dati DMA**

Permette di allineare i dati per quanto riguarda la gestione del DMA.

Usage:
```
sudo ./testUtil [OPTION...] data-align
```

<br />

Esempio con risposta:
```
sudo ./testUtil data-align
```
```
Align done.
```

<br />

___

**Sincronizzazione dei dati DMA**

Permette di fare la sincronizzazione dei dati per quanto riguarda la gestione del DMA (esegue un discovery prima).

Usage:
```
sudo ./testUtil [OPTION...] data-sync CHAN_NB
```
>CHAN_NB: numero del canale da sincronizzare (da 1 a 16) o allora 0 per sincronizzarli tutti

<br />

Esempio con risposta (con 2 schede presenti):
```
sudo ./testUtil data-sync 0
```
```
Discovery started...
DAQ3_REGISTER=0x40084008
DAQ5_REGISTER=0x40084008
Sync done.
```

Esempio con risposta:
```
sudo ./testUtil data-sync 1
```
```
Discovery started...
DAQ0_REGISTER=0x40804080
Sync done.
```

Esempio con risposta:
```
sudo ./testUtil data-sync 16
```
```
Discovery started...
DAQ7_REGISTER=0x40084000
Sync done.
```

<br />
