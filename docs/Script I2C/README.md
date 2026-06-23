## Descrizione

Raggruppa alcuni script utili per il test/collaudo delle schede:
- lettura EEPROM:
   - eep_read_EK26: lettura pagine EEPROM scheda EK26 (addr 0x51-0x59);
   - eep_read_PBI5_A20xx: lettura EEPROM schede PBI5, A20I2 e A20C5 (addr 0x54);
   - eep_read_AS20P2: lettura EEPROM scheda AS20P2 (addr 0x54);
   - eep_read_IOHS: lettura EEPROM schede IOHS (addr 0x54);
   - eep_read_TICK: lettura EEPROM scheda TICK (addr 0x53);
- scrittura EEPROM:
   - eep_write_gen_EK26: scrittura info e seriale o scrittura di una pagina in EEPROM della scheda EK26 (addr 0x51);
   - eep_write_gen_PBI5_A20xx: scrittura info e seriale o scrittura di una pagina in EEPROM delle schede PBI5/A20xx (addr 0x54);
   - eep_write_gen_AS20P2: scrittura info e seriale o scrittura di una pagina in EEPROM della scheda AS20P2 (addr 0x54);
   - eep_write_gen_IOHS: scrittura info e seriale o scrittura di una pagina in EEPROM della scheda IOHS (addr 0x54);
   - eep_write_gen_TICK: scrittura info e seriale o scrittura di una pagina in EEPROM della scheda TICK (addr 0x53);
- utility:
   - i2c_detect: discovery dei bus e dispositivi I2C;
   - ioexp_write_config: impostazione dell'IO Expander di una scheda PBI5, A20I2 o A20C5;
   - ioexp_write_output: pilotaggio in uscita della porta dell'IO Expander di una scheda PBI5, A20I2 o A20C5;
   - eep_select: selezione di un'EEPROM di una delle schede presenti (addr 0x57 -> 0x54);
   - eep_unselect: deselezione di un'EEPROM di una delle schede presenti (addr 0x54 -> 0x57).

<br/>

## Usage 

**i2c_detect**

Permette di verificare la presenza dei bus I2C e di verificare la presenza dei dispositivi I2C.

Esempio:
```
sudo ./i2c_detect.sh
```

NB: gli IO Expander della TI non vengono visti se non effettuando prima una comunicazione con i2cget/i2cset (utilizzando eep_unselect per esempio).


***


<br/>

**eep_read_EK26**

Permette di leggere 8 pagine di 32 byte dall'EEPROM (M24C64) della scheda EK26 fornendo un offset di pagina (0x00 a 0x1F).\
Addizionalmente, la pagina Identification Page viene sempre letta.

Usage:
```
eep_read_EK26 PAGE_OFFSET
```

Esempio:
```
sudo ./eep_read_EK26.sh 0x00
```

<br/>

**eep_read_PBI5_A20xx**

Permette di leggere i dati di una EEPROM 24AA025 di una scheda PBI5, A20I2 o A20C5.\
Va fornito l'indirizzo della scheda come argomento (0 a 7).

Usage:
```
eep_read_PBI5_A20xx BOARD_ADDR
```

Esempio:
```
sudo ./eep_read_PBI5_A20xx.sh 5
```

<br/>

**eep_read_AS20P2**

Permette di leggere i dati di una EEPROM 24AA025 di una scheda AS20P2.\
Va fornito l'indirizzo della scheda come argomento (0 a 7).

Usage:
```
eep_read_AS20P2 BOARD_ADDR
```

Esempio:
```
sudo ./eep_read_AS20P2.sh 5
```

<br/>

**eep_read_IOHS**

Permette di leggere i dati di una EEPROM 24AA025 di una scheda IOHS.\
Va fornito l'indirizzo della scheda come argomento (0 a 7).

Usage:
```
eep_read_IOHS BOARD_ADDR
```

Esempio:
```
sudo ./eep_read_IOHS.sh 5
```

<br/>

**eep_read_TICK**

Permette di leggere i dati di una EEPROM 24AA025 di una scheda TICK.

Esempio:
```
sudo ./eep_read_TICK.sh
```


***


<br/>

**ioexp_write_config**

Permette di impostare la porta di un IO Expander (PCA9534) di una scheda PBI5, A20I2 o A20C5 fornendo l'indirizzo della scheda (0 a 7) e lo stato della porta (8 bit).\
Stato pin porta: 0 ouput, 1 input.

Usage:
```
ioexp_write_config BOARD_ADDR PORT_CONFIG
```

Esempio, solo pin del led in uscita (0b1111 1110):
```
sudo ./ioexp_write_config.sh 5 0xFE
```

Esempio, pin del led e pin dell'EEPROM in uscita (0b1110 0110):
```
sudo ./ioexp_write_config.sh 5 0xE6
```

<br/>

**ioexp_write_output**

Permette di pilotare in uscita un IO Expander (PCA9534) di una scheda PBI5, A20I2 o A20C5 fornendo l'indirizzo della scheda (0 a 7) e lo stato della porta (8 bit).\
Stato pin porta: 0 basso, 1 alto.

Usage:
```
ioexp_write_output BOARD_ADDR PORT_STATE
```

Esempio, tutti i pin a 1 (0b1111 1111), LED spento e EEPROM non selezionata:
```
sudo ./ioexp_write_output.sh 5 0xFF
```

Esempio, led acceso (0b1111 1110):
```
sudo ./ioexp_write_output.sh 5 0xFE
```

Esempio, led acceso e EEPROM selezionata (0b1110 0110):
```
sudo ./ioexp_write_output.sh 5 0xE6
```


***


<br/>

**eep_select** (utilizza ioexp_write_config e ioexp_write_output)

Permette di selezionare una EEPROM (24AA025) di una scheda PBI5, A20I2, A20C5, AS20P2 o IOHS fornendo l'indirizzo della scheda (0 a 7).\
Viene anche acceso il led corrispondente (2 led per la scheda IOHS).

Usage:
```
eep_select BOARD_ADDR
```

Esempio:
```
sudo ./eep_select.sh 5
```

NB: utilizzare i2c_detect per verificare l'effetto.

<br/>

**eep_unselect** (utilizza ioexp_write_output e ioexp_write_config)

Permette di deselezionare una EEPROM (24AA025) di una scheda PBI5, A20I2 o A20C5 fornendo l'indirizzo della scheda (0 a 7).\
Viene anche spento il led corrispondente.

Usage:
```
eep_unselect BOARD_ADDR
```

Esempio:
```
sudo ./eep_unselect.sh 5
```

NB: utilizzare i2c_detect per verificare l'effetto.


***


<br/>

**eep_write_gen_EK26** 

Permette di scrivere dati dentro l'EEPROM (M24C64) della scheda EK26 fornendo:  
  1. la modalità di scrittura: BYTE (b) o INFO (i)
  2. i dati da scrivere:
     - in modalità BYTE scrive una pagina intera (32 byte)
     - in modalità INFO scrive:
        - HW_INFO_1 sui byte  1 a 16 della prima pagina
        - SERIAL_1  sui byte 17 a 32 della prima pagina
        - HW_INFO_2 sui byte  1 a 16 della seconda pagina
        - SERIAL_2  sui byte 17 a 32 della seconda pagina

Usage:
```
eep_write_gen_EK26 b PAGE_OFFSET PAGE_SUB_OFFSET BYTES_TO_WRITE
eep_write_gen_EK26 i HW_INFO_1 SERIAL_1 HW_INFO_2 SERIAL_2
```
NB: PAGE_OFFSET uguale 0x00 a 0x1F e PAGE_SUB_OFFSET uguale 0 a 7.
NB: utilizzare il DTR della seconda COM per attivare la scrittura dentro l'EEPROM.

Esempi:
```
sudo ./eep_write_gen_EK26.sh b 0x01 0 "0x00 0x01 0x02 0x03 0x04 0x05 0x06 0x07 0x08 0x09 0x0A 0x0B 0x0C 0x0D 0x0E 0x0F 0x10 0x11 0x12 0x13 0x14 0x15 0x16 0x17 0x18 0x19 0x1A 0x1B 0x1C 0x1D 0x1E 0x1F"
```
```
sudo ./eep_write_gen_EK26.sh b 0x01 1 "0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF"
```
```
sudo ./eep_write_gen_EK26.sh i "EK26 1.2" "SN1234" "EKFP 1.1" "SN1234"
```

<br/>

**eep_write_gen_PBI5_A20xx** 

Permette di scrivere dati dentro una EEPROM (24AA025) di una scheda PBI5, A20I2 o A20C5 fornendo:
  1. l'indirizzo dello slot (0 a 7) della scheda
  2. la modalità di scrittura: BYTE (b) o INFO (i)
  3. i dati da scrivere:
     - in modalità BYTE scrive la pagina intera (16 byte)
     - in modalità INFO scrive:
         - HW_INFO sui primi 10 byte della prima pagina
         - SERIAL sugli ultimi 6 byte della prima pagina

Usage:
```
eep_write_gen_PBI5_A20xx BOARD_ADDR b PAGE_OFFSET BYTES_TO_WRITE
eep_write_gen_PBI5_A20xx BOARD_ADDR i HW_INFO SERIAL
```
NB: PAGE_OFFSET uguale a 0x00, 0x10, 0x20, ..., 0x70 (0x80 a 0xF0 sono "permanently write-protected")

Esempi:
```
sudo ./eep_write_gen_PBI5_A20xx.sh 5 b 0x20 "0x00 0x01 0x02 0x03 0x04 0x05 0x06 0x07 0x08 0x09 0x0A 0x0B 0x0C 0x0D 0x0E 0x0F"
```
```
sudo ./eep_write_gen_PBI5_A20xx.sh 5 b 0x30 "0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF"
```
```
sudo ./eep_write_gen_PBI5_A20xx.sh 5 i "PBI5 1.2" "SN1234"
```
```
sudo ./eep_write_gen_PBI5_A20xx.sh 0 i "A20C5 1.2" "SN1234"
```
```
sudo ./eep_write_gen_PBI5_A20xx.sh 1 i "A20I2 1.2" "SN1234"
```

<br/>

**eep_write_gen_AS20P2** 

Permette di scrivere dati dentro una EEPROM (24AA025) di una scheda AS20P2 fornendo:
  1. l'indirizzo dello slot (0 a 7) della scheda
  2. la modalità di scrittura: BYTE (b) o INFO (i)
  3. i dati da scrivere:
     - in modalità BYTE scrive la pagina intera (16 byte)
     - in modalità INFO scrive:
         - HW_INFO sui primi 10 byte della prima pagina
         - SERIAL sugli ultimi 6 byte della prima pagina

Usage:
```
eep_write_gen_AS20P2 BOARD_ADDR b PAGE_OFFSET BYTES_TO_WRITE
eep_write_gen_AS20P2 BOARD_ADDR i HW_INFO SERIAL
```
NB: PAGE_OFFSET uguale a 0x00, 0x10, 0x20, ..., 0x70 (0x80 a 0xF0 sono "permanently write-protected")

Esempi:
```
sudo ./eep_write_gen_AS20P2.sh 5 b 0x20 "0x00 0x01 0x02 0x03 0x04 0x05 0x06 0x07 0x08 0x09 0x0A 0x0B 0x0C 0x0D 0x0E 0x0F"
```
```
sudo ./eep_write_gen_AS20P2.sh 5 b 0x30 "0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF"
```
```
sudo ./eep_write_gen_AS20P2.sh 0 i "AS20P2 1.0" "SN1234"
```

<br/>

**eep_write_gen_IOHS** 

Permette di scrivere dati dentro una EEPROM (24AA025) di una scheda IOHS fornendo:
  1. l'indirizzo dello slot (0 a 7) della scheda
  2. la modalità di scrittura: BYTE (b) o INFO (i)
  3. i dati da scrivere:
     - in modalità BYTE scrive la pagina intera (16 byte)
     - in modalità INFO scrive:
         - HW_INFO_1 sui primi 10 byte della prima pagina
         - SERIAL_1  sugli ultimi 6 byte della prima pagina
         - HW_INFO_2 sui primi 10 byte della seconda pagina
         - SERIAL_2  sugli ultimi 6 byte della seconda pagina

Usage:
```
eep_write_gen_IOHS BOARD_ADDR b PAGE_OFFSET BYTES_TO_WRITE
eep_write_gen_IOHS BOARD_ADDR i HW_INFO_1 SERIAL_1 HW_INFO_2 SERIAL_2
```
NB: PAGE_OFFSET uguale a 0x00, 0x10, 0x20, ..., 0x70 (0x80 a 0xF0 sono "permanently write-protected")

Esempi:
```
sudo ./eep_write_gen_IOHS.sh 5 b 0x20 "0x00 0x01 0x02 0x03 0x04 0x05 0x06 0x07 0x08 0x09 0x0A 0x0B 0x0C 0x0D 0x0E 0x0F"
```
```
sudo ./eep_write_gen_IOHS.sh 5 b 0x30 "0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF"
```
```
sudo ./eep_write_gen_IOHS.sh 5 i "IOHS 1.0" "SN1234" "IOHSFP 1.0" "SN1234"
```
```
sudo ./eep_write_gen_IOHS.sh 0 i "IOHS 1.0" "SN1234" "IOHSFP 1.0" "SN1234"
```
```
sudo ./eep_write_gen_IOHS.sh 1 i "IOHS 1.0" "SN1234" "IOHSFP 1.0" "SN1234"
```

<br/>

**eep_write_gen_TICK** 

Permette di scrivere dati dentro una EEPROM (24AA025) di una scheda TICK fornendo:  
  1. la modalità di scrittura: BYTE (b) o INFO (i)
  2. i dati da scrivere:
     - in modalità BYTE scrive la pagina intera (16 byte)
     - in modalità INFO scrive:
         - HW_INFO_1 sui primi 10 byte della prima pagina
         - SERIAL_1  sugli ultimi 6 byte della prima pagina
         - HW_INFO_2 sui primi 10 byte della seconda pagina
         - SERIAL_2  sugli ultimi 6 byte della seconda pagina

Usage:
```
eep_write_gen_TICK b PAGE_OFFSET BYTES_TO_WRITE
eep_write_gen_TICK i HW_INFO_1 SERIAL_1 HW_INFO_2 SERIAL_2
```
NB: PAGE_OFFSET uguale a 0x00, 0x10, 0x20, ..., 0x70 (0x80 a 0xF0 sono "permanently write-protected")

Esempi:
```
sudo ./eep_write_gen_TICK.sh b 0x20 "0x00 0x01 0x02 0x03 0x04 0x05 0x06 0x07 0x08 0x09 0x0A 0x0B 0x0C 0x0D 0x0E 0x0F"
```
```
sudo ./eep_write_gen_TICK.sh b 0x30 "0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF"
```
```
sudo ./eep_write_gen_TICK.sh i "TICK 1.2" "SN1234" "TICKFP 1.1" "SN1234"
```


***


<br/>
