## Descrizione

Questo server TCP mette a disposizione dei comandi SCPI per gestire i sistemi CASES e EPICA.
 
Dalla versione 3.0 vengono fatte due compilazioni diverse, una per ogni sistema. I file compilati sono **eladScpiServerC** per CASES e **eladScpiServerE** per EPICA.

<br>

## Usage - avvio e opzioni

**Avvio**

Avvio server senza opzioni.
```
sudo ./eladScpiServer
```
Risposta:
```
eladScpiServer vX.Y for CASES/EPICA
11:31:28 INI Initialization...
11:31:28 TCP Server ready
```

<br />

**Opzione Verbose**

Permette di aumentare la quantità di informazioni stampate sul terminale durante il funzionamento.
```
sudo ./eladScpiServer -v
```
Risposta:
```
eladScpiServer vX.Y for CASES/EPICA
Verbose mode ON.
11:33:15 INI Initialization...
11:33:15 TCP Server ready
```

<br />

**Opzione Quiet**

Permette di ridurre la quantità di informazioni stampate sul terminale durante il funzionamento.
```
sudo ./eladScpiServer -q
```
Risposta:
```
eladScpiServer vX.Y for CASES/EPICA
Quiet mode ON.
```

<br />

**Opzione Port**

Permette di lanciare il server su una porta diversa da quella di default (5025).
```
sudo ./eladScpiServer -p 60000
```
Risposta:
```
eladScpiServer vX.Y for CASES/EPICA
Port set to 60000.
11:36:59 INI Initialization...
11:36:59 TCP Server ready
```

<br />

**Opzione UART**

Indica di aprire la UART del bus (richiede circa 2s) solo all'avvio del programma. In caso contrario, la UART viene aperta e chiusa ad ogni utilizzo del bus.
```
sudo ./eladScpiServer -u
```
Risposta:
```
eladScpiServer vX.Y for CASES/EPICA
16:11:15 INI Initialization...
16:11:17 TCP Server ready
```

<br />

**Opzione Discovery**

Indica di effettuare il discovery all'avvio del programma.
```
sudo ./eladScpiServer -d
```
Risposta:
```
eladScpiServer vX.Y for CASES/EPICA
16:12:34 INI Initialization...
16:12:36 PHL Discovery started...
16:12:37 PHL Discovery:
16:12:37 PHL * SYSTEM:     EPICA | CASES POLARIZED | CASES NOT POLARIZED (left) | CASES NOT POLARIZED (right) | UNKNOWN
16:12:37 PHL * EK26 BOARD: (EEP:HW_INFO & SERIAL) (BOARD:CODE,ADDR)      (ERR:COMM_ERR) (FPGA:VERS,SYS,CHAN)   (UID)
16:12:37 PHL * BUS BOARD:  (EEP:HW_INFO & SERIAL) (MICRO:CODE,ADDR,VERS) (ERR:COMM_ERR) (FPGA:[DATA_0,]DATA_1) (UID)
16:12:37 PHL
16:12:37 PHL SYSTEM:       CASES NOT POLARIZED (left) - error found, probable missing board(s)
16:12:37 PHL EK: EK26      (BRD:E,0) (ERR:_) (F:09013,NP,2) (UID:72C3FF473230151744303312214038FF) (EEP:EK26 1.1,SL1F3H,EKFP 1.1,SL1F32)
16:12:37 PHL S0:           (MIC:-,-,v0.0) (ERR:U_I) (F:----|----|----|----,----|----|----|----) (UID:) (EEP:,,,)
16:12:37 PHL S1:           (MIC:-,-,v0.0) (ERR:U_I) (F:----|----|----|----,----|----|----|----) (UID:) (EEP:,,,)
16:12:37 PHL S2:           (MIC:-,-,v0.0) (ERR:U_I) (F:----|----|----|----,----|----|----|----) (UID:) (EEP:,,,)
16:12:37 PHL S3:           (MIC:-,-,v0.0) (ERR:U_I) (F:----|----|----|----,----|----|----|----) (UID:) (EEP:,,,)
16:12:37 PHL S4:           (MIC:-,-,v0.0) (ERR:U_I) (F:----|----|----|----,----|----|----|----) (UID:) (EEP:,,,)
16:12:37 PHL S5:           (MIC:-,-,v0.0) (ERR:U_I) (F:----|----|----|----,----|----|----|----) (UID:) (EEP:,,,)
16:12:37 PHL S6:           (MIC:-,-,v0.0) (ERR:U_I) (F:----|----|----|----,----|----|----|----) (UID:) (EEP:,,,)
16:12:37 PHL S7: A20I2     (MIC:I,7,v1.1) (ERR:___) (F:7020|0511|0000|0000,7120|0511|0000|0000) (UID:2941010F15BB) (EEP:A20I2 1.1,SL1HBN,,)
16:12:37 PHL TI: TICK      (MIC:T,8,v1.1) (ERR:___) (F:____|____|____|____,8180|0307|0000|0000) (UID:29410109DE9C) (EEP:TICK 1.2,SL1HDX,TICKFP 1.1,SL1F7B)
16:12:37 TCP Server ready
```

<br />

**Opzione Help**

Visualizza l'help.
```
./eladScpiServer -?
```
Risposta:
```
eladScpiServer vX.Y for CASES/EPICA
Usage: eladScpiServer [-v] [-q] [-p PORT] [-u] [-d] [-?]
  -v       verbose mode
  -q       quiet mode
  -p PORT  set alternative port (DEFAULT 5025)
  -u       open UART bus only at startup
  -d       perform discovery at startup
  -?       show this help
```

<br />

## Usage - comandi SCPI

NB:
- comandi e risposte devono finire con un **terminatore**: LF, CR o CR+LF;
- i comandi vengono descritti in questa pagina come **standard** (SCPI-99) o **custom** (creati appositamente per il sistema CASES/EPICA);
- i caratteri **'<'** e **'>'** servono nella documentazione per identificare i **parametri dei comandi** e le diverse **parti delle risposte**.

<br/>

## Comandi SCPI - SISTEMA

***

| *IDN? | Standard command |
|---------|-----------------|
| Descrizione | Questo comando recupera la stringa identificativa della macchina. |
| Sintassi comando | *IDN? |
| Sintassi risposta | \<manufacturer\>,\<instrument_model\>,\<serial_number\>,\<sw_version\> |

Esempio:
```
*IDN?
```

<br />

Risposte possibili:
```
ELAD,EPICA,<serial_number>,vX.Y
```
```
ELAD,CASES-POL,<serial_number>,vX.Y
```
```
ELAD,CASES-NPL,<serial_number>,vX.Y
```
```
ELAD,CASES-NPR,<serial_number>,vX.Y
```
```
ELAD,UNK,,vX.Y
```

NB:
- i vari tipi di strumento sono: EPICA, POL (polarizzato), NPL (non polarizzato sinistra), NPR (non polarizzato destra) e UNK (sconosciuto); in caso di errore (scheda mancante o scheda che non risponde) viene aggiunto "-E";
- il numero di serie è quello della scheda EK26, non viene fornito se non è disponibile.

<br />

***

| *CLS | Standard command |
|---------|-----------------|
| Descrizione | Questo comando cancella i registri degli eventi e le code. |
| Sintassi | *CLS |

Esempio:
```
*CLS
```

<br />

***

| SYSTem:ERRor:COUNt? | Standard command |
|---------|-----------------|
| Descrizione | Questo comando restituisce il numero di errori nel registro eventi. |
| Sintassi | SYSTem:ERRor:COUNt? |

Esempio:
```
SYSTem:ERRor:COUNt?
```

<br />

Esempio di risposta:
```
1
```

<br />

***

| SYSTem:ERRor:NEXT? | Standard command |
|---------|-----------------|
| Descrizione | Questo comando legge il codice di errore più vecchio. |
| Sintassi | SYSTem:ERRor:NEXT? |

Esempio:
```
SYSTem:ERRor:NEXT?
```

<br />

Esempio risposta:
```
-200,"Execution error"
```

<br />

## Comandi SCPI - ACQUISIZIONE

***

| ACQuisition:DATa:ALIGn | (custom command) |
|---------|-----------------|
| Descrizione | Permette di allineare i dati per quanto riguarda la gestione del DMA. |
| Sintassi comando | ACQuisition:DATa:ALIGn |

Esempio:
```
ACQuisition:DATa:ALIGn
```

<br />

***

| ACQuisition:DATa:SYNC | (custom command) |
|---------|-----------------|
| Descrizione | Permette di fare la sincronizzazione dei dati per quanto riguarda la gestione del DMA.<br>Il parametro \<channelNumber\> permette di indicare quale canale si vuole sincronizzare. Omettendo questo parametro vengono sincronizzati tutti i canali (1 a 16). |
| Sintassi comando | ACQuisition:DATa:SYNC <br> ACQuisition:DATa:SYNC \<channelNumber\> |

Esempi:
```
ACQuisition:DATa:SYNC
```
```
ACQuisition:DATa:SYNC 1
```
```
ACQuisition:DATa:SYNC 16
```

<br />

## Comandi SCPI - GESTIONE SCHEDE

***

| BOARds:LIST? | Custom command |
|---------|-----------------|
| Descrizione | Fornisce la lista delle schede del sistema indicando per ogni scheda lo stato della comunicazione UART e I2C, il tipo di scheda, il numero di serie della scheda e l'UID dell'EEPROM.<br />**Il comando ha un parametro opzionale che permette di aggiornare la lista delle schede (esecuzione discovery) prima di spedire la riposta.** |
| Sintassi comando | BOARds:LIST?<br />BOARds:LIST? \<action\> |
| Sintassi risposta | \<EK26_data\>,\<slot0_data\>,\<slot1_data\>,...,\<slot7_data\>,\<TICK_data\> |
| Sintassi dei parametri della risposta (EK26_data, slot0_data, ...) | \<slot_code\>:\<comm_state\>:\<brd_code\>:\<brd_serial\>:\<eeprom_uid\> |

>\<action\>: "update" per avviare il discovery

>\<slot_code\>: "EK", "S0" a "S7" o "TI"\
\<comm_state\>: "OK" per nessun errore, "EU" per errore UART, "EI" per errore I2C o "EB" per errore UART e I2C\
\<brd_code\>: 'E' per EK26, 'P' per PBI5, 'I' per A20I2, 'C' per A20C5, 'A' per AS20P2, 'T' per TICK o '-' per scheda non riconosciuta o non presente

<br />

NB: 
- <brd_code> è uguale a '-' se c'è un errore di comunicazione UART;
- <brd_serial> e <eeprom_uid> non vengono forniti se c'è un errore di comunicazione I2C.

<br />

Esempio:
```
BOARds:LIST?
```
Esempio con richiesta di aggiornamento dei dati (esecuzione discovery):
```
BOARds:LIST? update
```

<br />

Risposta nel caso del rack con sonde non polarizzate, parte sinistra:
```
EK:OK:E:SLA001:00112233445566778899AABBCCDDEEFF,S0:OK:I:SLA002:AABBCCDDEEFF,S1:OK:I:SLA003:AABBCCDDEEFF,S2:OK:I:SLA004:AABBCCDDEEFF,S3:OK:I:SLA005:AABBCCDDEEFF,S4:OK:I:SLA006:AABBCCDDEEFF,S5:OK:I:SLA007:AABBCCDDEEFF,S6:OK:I:SLA008:AABBCCDDEEFF,S7:OK:I:SLA009:AABBCCDDEEFF,TI:OK:T:SLA010:AABBCCDDEEFF
```
Risposta nel caso del rack con sonde non polarizzate, parte destra:
```
EK:OK:E:SLB001:00112233445566778899AABBCCDDEEFF,S0:OK:I:SLB002:AABBCCDDEEFF,S1:OK:I:SLB003:AABBCCDDEEFF,S2:OK:I:SLB004:AABBCCDDEEFF,S3:OK:I:SLB005:AABBCCDDEEFF,S4:OK:I:SLB006:AABBCCDDEEFF,S5:OK:I:SLB007:AABBCCDDEEFF,S6:OK:I:SLB008:AABBCCDDEEFF,S7:OK:I:SLB009:AABBCCDDEEFF,TI:EB:-::
```
Risposta nel caso del rack con sonde polarizzate:
```
EK:OK:E:SLC001:00112233445566778899AABBCCDDEEFF,S0:OK:P:SLC002:AABBCCDDEEFF,S1:OK:C:SLC003:AABBCCDDEEFF,S2:OK:P:SLC004:AABBCCDDEEFF,S3:OK:C:SLC005:AABBCCDDEEFF,S4:OK:P:SLC006:AABBCCDDEEFF,S5:OK:C:SLC007:AABBCCDDEEFF,S6:EB:-::,S7:EB:-::,TI:OK:T:SLC010:AABBCCDDEEFF
```
Esempio di risposta con errori (rack con sonde non polarizzate, parte sinistra):
```
EK:OK:E:SLD001:00112233445566778899AABBCCDDEEFF,S0:OK:I:SLD002:AABBCCDDEEFF,S1:EU:-:SLD003:AABBCCDDEEFF,S2:EI:I::,S3:EB:-::,S4:EU:-:SLD006:AABBCCDDEEFF,S5:EI:I::,S6:EB:-::,S7:EB:-::,TI:EB:-::
```

<br />

***

| BOARds:INFo? | Custom command |
|---------|-----------------|
| Descrizione | Fornisce, per una singola scheda, tutte le informazioni recuperate al momento dell'esecuzione di un discovery.<br />**Per farsi che i dati siano aggiornati è necessario che sia stato eseguito un discovery prima (all'avvio o tramite il comando "BOARds:LIST? update").** |
| Sintassi comando | BOARds:INFo? \<slot_code\> |
| Sintassi risposta (EK) | \<slot_code\>:\<brd_name:\<brd_code\>:\<brd_addr\>,ERR:\<error_code\>,F:\<fpga_vers\>:\<bitstream_type\>:\<chan_nb\>,UID:\<eeprom_uid\>,EEP:\<hw_info_1\>:\<serial_nb_1\>:\<hw_info_2\>:\<serial_nb_2\> |
| Sintassi risposta (Sx e TI) | \<slot_code\>:\<brd_name\>,MIC:\<brd_code\>:\<brd_addr\>:\<fw_vers\>,ERR:\<error_codes\>,F:\<fpga0_data\>:\<fpga1_data\>,UID:\<eeprom_uid\>,EEP:\<hw_info_1\>:\<serial_nb_1\>:\<hw_info_2\>:\<serial_nb_2\> |

>\<slot_code\>: "EK", "S0" a "S7" o "TI"\
\<brd_code\>: 'E' per EK26, 'P' per PBI5, 'I' per A20I2, 'C' per A20C5, 'A' per AS20P2, 'T' per TICK o '-' per scheda non riconosciuta o non presente\
\<brd_addr\>: da '0' a '8', '-' se dato non disponibile

>\<error_code\>: "\_" per nessun errore e "I" per errore I2C\
\<fpga_vers\>: 5 caratteri (es. "09013") o 5 trattini ("-----") se il dato non è disponibile\
\<bitstream_type\>: "NP" per non polarizzato, "POL" per polarizzato o "UNK" se dato non valido\
\<chan_nb\>: numero da '0' a '8'

>\<fw_vers\>: versione firmware nel formato "vX.Y" (con X e Y numeri), valore di default: "v0.0"\
\<error_codes\>: "\_\_\_" per nessun errore, "U\_\_" per errore UART verso il micro, "\_U\_" per errore UART verso un FPGA e "\_\_I" per errore I2C\
\<fpga0/1_data\>: dati del FPGA (es. 7020|0511|0000|0000), riempito con '-' se il dato non è disponibile, riempito con '\_' se il dato non è rilevante (<fpga0_data> non presente per la TICK e per la PBI5)

<br />

NB: 
- <brd_code> è uguale a '-' se c'è un errore di comunicazione UART;
- <brd_name> non viene fornito se c'è un errore di comunicazione UART;
- <eeprom_uid>, <hw_info_1/2> e <serial_nb_1/2> non vengono forniti se c'è un errore di comunicazione I2C.

<br />

Esempi:
```
BOARds:INFo? EK
```
```
BOARds:INFo? S0
```
```
BOARds:INFo? TI
```

<br />

Risposta nel caso di una scheda EK26 (EK):
```
EK:EK26:E:2,ERR:_,F:09013:NP:2,UID:72C3FF473230151744303312214038FF,EEP:EK26 1.1:SL1F3H:EKFP 1.1:SL1F32
```
Risposta nel caso di schede Sx (S0-S7):
```
S6:PBI5,MIC:P:6:v1.1,ERR:___,F:____|____|____|____:0140|0402|0000|2000,UID:2941010EE888,EEP:PBI5 1.2:SN1234::
S7:A20C5,MIC:C:7:v1.1,ERR:___,F:0050|0514|4000|0000:0150|0514|5000|0000,UID:2941010F10CD,EEP:A20C5 1.2:SL1FZB::
S7:A20I2,MIC:I:7:v1.1,ERR:___,F:7020|0511|0000|0000:7120|0511|0000|0000,UID:2941010F15BB,EEP:A20I2 1.1:SL1HBN::
```
Risposta nel caso di una scheda TICK (TI):
```
TI:TICK,MIC:T:8:v1.1,ERR:___,F:____|____|____|____:8180|0307|0000|0000,UID:29410109DE9C,EEP:TICK 1.2:SL1HDX:TICKFP 1.1:SL1F7B
```
Esempi di risposta con errori:
```
EK::E:-,ERR:I,F:-----:UNK:0,UID:,EEP::::
S7:,MIC:-:-:v0.0,ERR:U_I,F:----|----|----|----:----|----|----|----,UID:,EEP::::
TI:,MIC:-:-:v0.0,ERR:U_I,F:____|____|____|____:----|----|----|----,UID:,EEP::::
```

<br />

## Comandi SCPI - GESTIONE REGISTRI

***

| REGisters:READ? | (custom command) |
|---------|-----------------|
| Descrizione | Permette di leggere alcuni registri del sistema.<br>Il parametro \<registerName\> permette di indicare quale registro si vuole leggere, eseguire il comando REGisters:DUMP? per avere la lista dei registri. |
| Sintassi comando | REGisters:READ? \<registerName\> |
| Sintassi risposta | REGisters:READ?,\<registerName\>\<registerValue\> |

NB:
- \<registerValue\> viene fornito in esadecimale seguendo il formato del parser "SCPI parser library v2" (vd. documentazione in sw-scpitcpserver/scpi-parser-2.3/README.md).

<br />

Esempio:
```
REGisters:READ? fpga_ver
```
Risposta:
```
REGisters:READ?,fpga_ver#H2309013
```

<br />

***

| REGisters:WRITe? | (custom command) |
|---------|-----------------|
| Descrizione | Permette di scrivere alcuni registri del sistema.<br>Il parametro \<registerName\> permette di indicare quale registro si vuole scrivere, eseguire il comando REGisters:DUMP? per avere la lista dei registri.<br>Il parametro \<registerValue\> permette di fornire il valore del registro. |
| Sintassi comando | REGisters:WRITe? \<registerName\>,\<registerValue\> |
| Sintassi risposta | REGisters:WRITe?,\<registerName\>\<registerValue\> |

NB:
- \<registerValue\> va fornito in esadecimale seguendo il formato del parser "SCPI parser library v2" (vd. documentazione in sw-scpitcpserver/scpi-parser-2.3/README.md).

<br />

Esempio:
```
REGisters:WRITe? axi_cfg0,#H0000AA55
```
Risposta:
```
REGisters:WRITe?,axi_cfg0#H0000AA55
```

<br />

***

| REGisters:EDIT? | (custom command) |
|---------|-----------------|
| Descrizione | Permette di modificare alcuni registri del sistema.<br>Il parametro \<registerName\> permette di indicare quale registro si vuole modificare, eseguire il comando REGisters:DUMP? per avere la lista dei registri.<br>Il parametro \<andMask\> permette di fornire la maschera in AND da applicare al registro.<br>Il parametro \<orMask\> permette di fornire la maschera in OR da applicare al registro. |
| Sintassi comando | REGisters:EDIT? \<registerName\>,\<andMask\>,\<orMask\> |
| Sintassi risposta | REGisters:EDIT?,\<registerName\>\<registerValue\> |

NB:
- \<andMask\> e \<orMask\> vanno forniti in esadecimale seguendo il formato del parser "SCPI parser library v2" (vd. documentazione in sw-scpitcpserver/scpi-parser-2.3/README.md).

<br />

Esempio:
```
REGisters:EDIT? daq0,#H0000F0F0,#H0000000F
```
Risposta:
```
REGisters:EDIT?,daq0#H0000A05F
```

<br />

***

| REGisters:DUMP? | (custom command) |
|---------|-----------------|
| Descrizione | Permette di leggere la maggiore parte dei registri del sistema. |
| Sintassi comando | REGisters:DUMP? |
| Sintassi risposta | REGisters:DUMP?,\<reg1Name\>\<reg1Value\>,\<reg2Name\>\<reg2Value\>, ... , \<regnName\>\<regnValue\> |

NB:
- \<regxName\> viene fornito senza doppi apici (");
- \<regxValue\> viene fornito in esadecimale seguendo il formato del parser "SCPI parser library v2" (vd. documentazione in sw-scpitcpserver/scpi-parser-2.3/README.md).

<br />

Esempio:
```
REGisters:DUMP?
```
Risposta:
```
REGisters:DUMP?,fpga_ver#H2309013,axi_cfg0#H0,daq0#H0,daq1#H0,daq2#H0,daq3#H0,daq4#H0,daq5#H0,daq6#H0,daq7#H0,daq0_stat#H13E813E8,daq1_stat#H0,daq2_stat#H0,daq3_stat#H0,daq4_stat#H0,daq5_stat#H0,daq6_stat#H0,daq7_stat#H0,gen_stat#H0,pts#H0,recorder#H0,recorder_stat#H0
```

<br />

## Comandi SCPI - GESTIONE ACCESSO REMOTO

***

| SERVice:REMote:STArt | Custom command |
|---------|-----------------|
| Descrizione | Permette di avviare l'utility socat su una o due porte TCP per accedere alle seriali della scheda EKFP. |
| Sintassi comando | SERVice:REMote:STArt \<mode\>,<port_1><br />SERVice:REMote:STArt \<mode\>,<port_1>,<port_2> |

> \<mode\>: "talk" o "silent"\
\<port_1\>: porta di accesso al bus UART in talk mode, porta di ascolto delle risposte del bus UART in silent mode; da 0 a 65535\
\<port_2\>: porta di accesso al terminale PetaLinux in talk mode, porta di ascolto dei comandi del bus UART in silent mode; da 0 a 65535

<br />

L'uso di questo comando necessità che sia collegato un cavo USB A-microB tra i connettori del frontale del modulo EK26, in questo modo il sistema vede i dispositivi ttyUSB0, ttyUSB1, ttyUSB2 e ttyUSB3 che permettono di accedere a:
  - ttyUSB0: porta JTAG, NON UTILIZZARE;
  - ttyUSB1: terminale PetaLinux;
  - ttyUSB2(RTS=ON): controllo bidirezionale del bus UART;
  - ttyUSB2(RTS=OFF): sniffing risposte seriali sul bus UART;
  - ttyUSB3: sniffing comandi seriali sul bus UART.

<br />

Le modalità disponibili sono:
  - **talk**: ttyUSB2(RTS=ON) e ttyUSB1 (opzionale) vengono resi accessibili sulle porte TCP indicate in parametro;
  - **silent**: ttyUSB2(RTS=OFF) e ttyUSB3 (opzionale) vengono resi accessibili sulle porte TCP indicate in parametro.

<br />

Questo comando va utilizzato insieme ai comandi:
  - "SERVice:REMote:CONtrol": apertura ttyUSB2 per pilotare il segnale RTS;
  - "SERVice:REMote:STOp": chiusura ttyUSB2 e richiesta di liberare le porte TCP utilizzate.

<br />

Esempio di utilizzo in modalità **talk**:
  1. invio di "SERVice:REMote:STArt talk, 50000" (socat crea un socket tcp);
  2. connessione da parte di un client TCP alla porta 50000 (viene aperto il ttyUSB2 con RTS=ON);
  3. gestione bidirezionale del bus UART tramite il client TCP;
  4. disconnessione del client TCP;
  5. invio di "SERVice:REMote:STOp" per rilasciare le risorse utilizzate.

<br />

Esempio di utilizzo in modalità **silent**:
  1. invio di "SERVice:REMote:STArt silent, 60000" (socat crea un socket tcp);
  2. connessione da parte di un client TCP alla porta 60000 (viene aperto il ttyUSB2 con RTS=ON);
  3. invio di "SERVice:REMote:CONtrol rts_off" (viene gestito il ttyUSB2 per avere RTS=OFF);
  4. gestione unidirezionale del bus UART tramite il client TCP (sniffing delle risposte che passano sul bus UART);
  5. disconnessione del client TCP;
  6. invio di "SERVice:REMote:STOp" per rilasciare le risorse utilizzate.

<br />

Esempi:
```
SERVice:REMote:STArt talk,60000
```
```
SERVice:REMote:STArt talk,60000,60001
```
```
SERVice:REMote:STArt silent,60000
```
```
SERVice:REMote:STArt silent,60000,60001
```

<br />

***

| SERVice:REMote:CONtrol | Custom command |
|---------|-----------------|
| Descrizione | Permette di impostare il tipo di accesso alla seriale collegata al bus UART (pilotando in particolare il segnale RTS). |
| Sintassi comando | SERVice:REMote:CONtrol <rts_cmd><br />SERVice:REMote:CONtrol <rts_cmd>,<dtr_cmd> |

> \<rts_cmd\>: "rts_on" per attivare l'RTS o "rts_off" per disattivare l'RTS\
\<dtr_cmd\>: "dtr_on" per attivare il DTR o "dtr_off" per disattivare il DTR

<br />

L'utilizzo tipo è:
  - pilotaggio del segnale RTS a OFF dopo l'invio del comando "SERVice:REMote:STArt" in modalità silent;
  - pilotaggio del segnale DTR per abilitare la scrittura per l'EEPROM della scheda EK26.

NB: dopo l'utilizzo di "SERVice:REMote:CONtrol", inviare sempre "SERVice:REMote:STOp".

<br />

Questo comando va utilizzato insieme ai comandi:
  - "SERVice:REMote:STArt": avvio socat sulle porte TCP indicate;
  - "SERVice:REMote:STOp": chiusura ttyUSB2 e richiesta di liberare le porte TCP utilizzate.

<br />

Esempi:
```
SERVice:REMote:CONtrol rts_off
```
```
SERVice:REMote:CONtrol rts_off,dtr_off
```
```
SERVice:REMote:CONtrol rts_off,dtr_on
```
```
SERVice:REMote:CONtrol rts_off,dtr_off
```

<br />

***

| SERVice:REMote:STOp | Custom command |
|---------|-----------------|
| Descrizione | Permette di eseguire azioni di chiusura per quanto riguarda l'accesso remoto alle seriali. |
| Sintassi comando | SERVice:REMote:STOp |

Questo comando rilascia le risorse utilizzate (close su ttyUSB2 e "fuser -k" sulle porte TCP utilizzate).\
NB: il comando "SERVice:REMote:STOp" va sempre inviato dopo avere invio un "SERVice:REMote:STArt" e/o un "SERVice:REMote:CONtrol".

<br />

Questo comando va utilizzato insieme ai comandi:
  - "SERVice:REMote:STArt": avvio socat sulle porte TCP indicate;
  - "SERVice:REMote:CONtrol": apertura ttyUSB2 per pilotare i segnali RTS e DTR.

<br />

Esempio:
```
SERVice:REMote:STOp
```

<br />
