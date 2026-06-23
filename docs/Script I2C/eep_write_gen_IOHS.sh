# Permette di scrivere dati dentro una EEPROM (24AA025) di una scheda IOHS fornendo:
#   1. l'indirizzo dello slot (0 a 7) della scheda
#   2. la modalità di scrittura: BYTE (b) o INFO (i)
#   3. i dati da scrivere:
#     - in modalità BYTE scrive la pagina intera (16 byte)
#     - in modalità INFO scrive:
#         - HW_INFO_1 sui primi 10 byte della prima pagina
#         - SERIAL_1  sugli ultimi 6 byte della prima pagina
#         - HW_INFO_2 sui primi 10 byte della seconda pagina
#         - SERIAL_2  sugli ultimi 6 byte della seconda pagina
#
# Usage:
#   - BYTE mode: eep_write_gen_IOHS BOARD_ADDR b PAGE_OFFSET BYTES_TO_WRITE
#                con PAGE_OFFSET uguale 0x00, 0x10, 0x20, ..., 0x70 (0x80 a 0xF0 sono write protected !!!)
#   - INFO mode: eep_write_gen_IOHS BOARD_ADDR i HW_INFO_1 SERIAL_1 HW_INFO_2 SERIAL_2
#
# Esempi:
#   - sudo ./eep_write_gen_IOHS.sh 5 b 0x20 "0x00 0x01 0x02 0x03 0x04 0x05 0x06 0x07 0x08 0x09 0x0A 0x0B 0x0C 0x0D 0x0E 0x0F"
#   - sudo ./eep_write_gen_IOHS.sh 5 b 0x30 "0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF"
#   - sudo ./eep_write_gen_IOHS.sh 5 i "IOHS 1.0" "SN1234" "IOHSFP 1.0" "SN1234"
#   - sudo ./eep_write_gen_IOHS.sh 0 i "IOHS 1.0" "SN1234" "IOHSFP 1.0" "SN1234"
#   - sudo ./eep_write_gen_IOHS.sh 1 i "IOHS 1.0" "SN1234" "IOHSFP 1.0" "SN1234"


# *** DEBUG ***
debug=0


# --- version ---
version="1.0"
date="14/01/2026"
echo "> script \"$0\", v$version ($date)"


# *** DEBUG ***
if [ $debug -eq 1 ]; then	
	  echo "--> $# arguments"
fi	


# --- args control ---
# controllo numero argomenti
if [ $# -lt 4 ]; then
    echo "> Wrong arguments number, expected at least 4 !!!"
    echo "> Usage: \"$0 BOARD_ADDR \"b\" PAGE_OFFSET BYTES_TO_WRITE\""
    echo "> Usage: \"$0 BOARD_ADDR \"i\" HW_INFO_1 SERIAL_1 HW_INFO_2 SERIAL_2\""
    exit 1
fi
# controllo modalità, BYTE O INFO
if [ "$2" = "b" ]; then
    # *** DEBUG ***
    if [ $debug -eq 1 ]; then	
        echo "--> BYTE mode"
    fi	

    # controllo numero argomenti
    if [ $# -ne 4 ]; then
        echo "> Wrong arguments number, expected 4 !!!"
        echo "> Usage: \"$0 \"b\" PAGE_OFFSET BYTES_TO_WRITE\""
        exit 1
    fi

else
    if [ "$2" = "i" ]; then
        # *** DEBUG ***
        if [ $debug -eq 1 ]; then	
            echo "--> INFO mode"
        fi	    

        # controllo numero argomenti
        if [ $# -ne 6 ]; then
            echo "> Wrong arguments number, expected 6 !!!"
            echo "> Usage: \"$0 \"i\" HW_INFO_1 SERIAL_1 HW_INFO_2 SERIAL_2\""
            exit 1
        fi

    else
        # modalità non corretta
        echo "> Wrong mode !!!"
        echo "> Usage: \"$0 BOARD_ADDR \"b\" PAGE_OFFSET BYTES_TO_WRITE\""
        echo "> Usage: \"$0 BOARD_ADDR \"i\" HW_INFO_1 SERIAL_1 HW_INFO_2 SERIAL_2\""
        exit 1    
    fi
fi


# *** DEBUG ***
if [ $debug -eq 1 ]; then
	  echo "--> BoardAddr (len): $1 (${#1})"
	  echo "--> Mode      (len): $2 (${#2})"

    # BYTE
    if [ "$2" = "b" ]; then
        echo "--> PageOffset(len): $3 (${#3})"
        echo "--> Bytes     (len): $4 (${#4})"
    else # INFO
      	echo "--> HwInfo_1  (len): $3 (${#3})"
    	  echo "--> Serial_1  (len): $4 (${#4})"
        echo "--> HwInfo_2  (len): $5 (${#5})"
    	  echo "--> Serial_2  (len): $6 (${#6})"
    fi
fi


# --- args length control ---
if [ ${#1} -ne 1 ]; then
	  echo "> Wrong length for \"$1\", must be 1 char !!!"
	  exit 1
fi
#
if [ ${#2} -ne 1 ]; then
	  echo "> Wrong length for \"$2\", must be  1 char !!!"
	  exit 1
fi
#
# BYTE mode
if [ "$2" = "b" ]; then 

    if [ ${#3} -ne 4 ]; then
        echo "> Wrong length for \"$3\", must be 4 chars !!!"
        exit 1
    fi
    #
    if [ ${#4} -ne 79 ]; then
        echo "> Wrong length for \"$4\", must be 79 chars !!!"
        exit 1
    fi    
else # INFO mode

    if [ ${#3} -gt 10 ]; then
        echo "> Wrong length for \"$3\", max 10 chars !!!"
        exit 1
    fi
    #
    if [ ${#4} -ne 6 ]; then
        echo "> Wrong length for \"$4\", must be 6 chars !!!"
        exit 1
    fi
    #
    if [ ${#5} -gt 10 ]; then
        echo "> Wrong length for \"$5\", max 10 chars !!!"
        exit 1
    fi
    #
    if [ ${#6} -ne 6 ]; then
        echo "> Wrong length for \"$6\", must be 6 chars !!!"
        exit 1
    fi    
fi


# --- args value control ---
# check for number 
case $1 in
    ''|*[!0-9]*) error=1;;
    *) error=0;;
esac
#
# error notification
if [ $error -eq 1 ]; then
	echo "> \"$1\" not a number (expected \"0\" to \"7\") !!!"
	exit 1
fi
#
# check for value
if [ $1 -gt 7 ]; then
    echo "> Wrong value ($1), expected \"0\" to \"7\" !!!"
    exit 1
fi
#
ioExpAddr=0x2$1


# --- BYTE MODE MANAGEMENT ---
if [ "$2" = "b" ]; then

    # --- ask for confirmation ---
    echo "> Data to be written:"
    echo "> Page Offset:\"$3\""
    echo "> Bytes      :\"$4\""
    question="> Write data (y/n)?"
    read -p "$question" choice
    case "$choice" in 
      y|Y ) abort=0;;
      n|N ) abort=1;;
      * ) abort=1;;
    esac

    # *** DEBUG ***
    if [ $debug -eq 1 ]; then
      echo "--> abort: $abort"
    fi

    # error notification
    if [ $abort -eq 1 ]; then
      echo "> Aborted, closing !!!"
      exit 1
    fi

# --- INFO MODE MANAGEMENT ---    
else 

    # --- get HW_INFO_1 ---
    #
    # hexdump
    hwInfo1=$(echo $3 | hexdump -v -e ''${#3}'/1 " 0x%02X"' -n ${#3})
    #
    # add remaining bytes to 0x00
    for (( i=1; i<=(10-${#3}); i++ ))
    do 
        hwInfo1+=" 0x00"
    done

    # *** DEBUG ***
    if [ $debug -eq 1 ]; then
        echo "--> hwInfo1 (hex): $hwInfo1"
    fi


    # --- get SERIAL_1 ---
    #
    # hexdump
    serial1=$(echo $4 | hexdump -v -e ''${#4}'/1 " 0x%02X"' -n ${#4})

    # *** DEBUG ***
    if [ $debug -eq 1 ]; then
        echo "--> serial1 (hex): $serial1"
    fi


    # --- get HW_INFO_2 ---
    #
    # hexdump
    hwInfo2=$(echo $5 | hexdump -v -e ''${#5}'/1 " 0x%02X"' -n ${#5})
    #
    # add remaining bytes to 0x00
    for (( i=1; i<=(10-${#5}); i++ ))
    do 
        hwInfo2+=" 0x00"
    done

    # *** DEBUG ***
    if [ $debug -eq 1 ]; then
        echo "--> hwInfo2 (hex): $hwInfo2"
    fi


    # --- get SERIAL_2 ---
    #
    # hexdump
    serial2=$(echo $6 | hexdump -v -e ''${#6}'/1 " 0x%02X"' -n ${#6})

    # *** DEBUG ***
    if [ $debug -eq 1 ]; then
        echo "--> serial2 (hex): $serial2"
    fi


    # --- ask for confirmation ---
    echo "> Data to be written:"
    echo "> HW Info 1:\"$hwInfo1\" (\"$3\", len: ${#3} bytes)"
    echo "> Serial  1:\"$serial1\" (\"$4\", len: ${#4} bytes)"
    echo "> HW Info 2:\"$hwInfo2\" (\"$5\", len: ${#5} bytes)"
    echo "> Serial  2:\"$serial2\" (\"$6\", len: ${#6} bytes)"    
    question="> Write data (y/n)?"
    read -p "$question" choice
    case "$choice" in 
      y|Y ) abort=0;;
      n|N ) abort=1;;
      * ) abort=1;;
    esac

    # *** DEBUG ***
    if [ $debug -eq 1 ]; then
      echo "--> abort: $abort"
    fi

    # error notification
    if [ $abort -eq 1 ]; then
      echo "> Aborted, closing !!!"
      exit 1
    fi
fi


# --- configura l'IO Expander (tutti pin a 1 e P0, P1, P3, e P4 in output) ---
sudo i2cset -y 3 $ioExpAddr 0x01 0xFF
sudo i2cset -y 3 $ioExpAddr 0x03 0xE4

# --- seleziona l'eeprom (con LED on) ---
sudo i2cset -y 3 $ioExpAddr 0x01 0xE4


# --- write ---
# BYTE
if [ "$2" = "b" ]; then
    # --- writing page ---
    echo "> Writing page..."
    if [ $debug -eq 1 ]; then
      sudo i2ctransfer 3 w17@0x54 $3 $4
    else
      sudo i2ctransfer -y 3 w17@0x54 $3 $4
    fi

else # INFO

    # --- writing HW_INFO_1 and SERIAL_1 ---
    echo "> Writing hardware info 1 and serial 1..."
    if [ $debug -eq 1 ]; then
      sudo i2ctransfer 3 w17@0x54 0x00$hwInfo1 $serial1
    else
      sudo i2ctransfer -y 3 w17@0x54 0x00$hwInfo1  $serial1
    fi

    # --- writing HW_INFO_2 and SERIAL_2 ---
    echo "> Writing hardware info 2 and serial 2..."
    if [ $debug -eq 1 ]; then
      sudo i2ctransfer 3 w17@0x54 0x10$hwInfo2 $serial2
    else
      sudo i2ctransfer -y 3 w17@0x54 0x10$hwInfo2  $serial2
    fi    
fi


# --- reading data ---
echo "> Reading eeprom..."
eepDump=$(sudo i2cdump -y 3 0x54 b)
while IFS= read -r line; do
	echo "> $line"
done <<< "$eepDump"


# --- deseleziona l'eeprom (con LED off) ---
sudo i2cset -y 3 $ioExpAddr 0x01 0xFF


exit 0
