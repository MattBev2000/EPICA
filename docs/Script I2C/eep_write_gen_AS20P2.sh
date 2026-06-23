# Permette di scrivere dati dentro una EEPROM (24AA025) di una scheda AS20P2 fornendo:
#   1. l'indirizzo dello slot (0 a 7) della scheda
#   2. la modalità di scrittura: BYTE (b) o INFO (i)
#   3. i dati da scrivere:
#     - in modalità BYTE scrive la pagina intera (16 byte)
#     - in modalità INFO scrive:
#         - HW_INFO sui primi 10 byte della prima pagina
#         - SERIAL sugli ultimi 6 byte della prima pagina
#
# Usage:
#   - BYTE mode: eep_write_gen_AS20P2 BOARD_ADDR b PAGE_OFFSET BYTES_TO_WRITE
#                con PAGE_OFFSET uguale 0x00, 0x10, 0x20, ..., 0x70 (0x80 a 0xF0 sono write protected !!!)
#   - INFO mode: eep_write_gen_AS20P2 BOARD_ADDR i HW_INFO SERIAL
#
# Esempi:
#   - sudo ./eep_write_gen_AS20P2.sh 5 b 0x20 "0x00 0x01 0x02 0x03 0x04 0x05 0x06 0x07 0x08 0x09 0x0A 0x0B 0x0C 0x0D 0x0E 0x0F"
#   - sudo ./eep_write_gen_AS20P2.sh 5 b 0x30 "0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF"
#   - sudo ./eep_write_gen_AS20P2.sh 1 i "AS20P2 1.0" "SN1234"


# *** DEBUG ***
debug=0


# --- version ---
version="1.0"
date="12/05/2025"
echo "> script \"$0\", v$version ($date)"


# *** DEBUG ***
if [ $debug -eq 1 ]; then	
	  echo "--> $# arguments"
fi	


# --- args control ---
# controllo numero argomenti
if [ $# -ne 4 ]; then
    echo "> Wrong arguments number, expected 4 !!!"
    echo "> Usage: \"$0 BOARD_ADDR \"b\" PAGE_OFFSET BYTES_TO_WRITE\""
    echo "> Usage: \"$0 BOARD_ADDR \"i\" HW_INFO SERIAL\""
    exit 1
fi
# controllo modalità, BYTE O INFO
if [ "$2" = "b" ]; then
    # *** DEBUG ***
    if [ $debug -eq 1 ]; then	
        echo "--> BYTE mode"
    fi	
else
    if [ "$2" = "i" ]; then
        # *** DEBUG ***
        if [ $debug -eq 1 ]; then	
            echo "--> INFO mode"
        fi	    
    else
        # modalità non corretta
        echo "> Wrong mode !!!"
        echo "> Usage: \"$0 BOARD_ADDR \"b\" PAGE_OFFSET BYTES_TO_WRITE\""
        echo "> Usage: \"$0 BOARD_ADDR \"i\" HW_INFO SERIAL\""
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
      	echo "--> HwInfo    (len): $3 (${#3})"
    	  echo "--> Serial    (len): $4 (${#4})"
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

    # --- get HW_INFO ---
    #
    # hexdump
    hwInfo=$(echo $3 | hexdump -v -e ''${#3}'/1 " 0x%02X"' -n ${#3})
    #
    # add remaining bytes to 0x00
    for (( i=1; i<=(10-${#3}); i++ ))
    do 
        hwInfo+=" 0x00"
    done

    # *** DEBUG ***
    if [ $debug -eq 1 ]; then
        echo "--> hwInfo (hex): $hwInfo"
    fi


    # --- get SERIAL ---
    #
    # hexdump
    serial=$(echo $4 | hexdump -v -e ''${#4}'/1 " 0x%02X"' -n ${#4})

    # *** DEBUG ***
    if [ $debug -eq 1 ]; then
        echo "--> serial (hex): $serial"
    fi


    # --- ask for confirmation ---
    echo "> Data to be written:"
    echo "> HW Info:\"$hwInfo\" (\"$3\", len: ${#3} bytes)"
    echo "> Serial :\"$serial\" (\"$4\", len: ${#4} bytes)"
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


# --- configura l'IO Expander (tutti pin a 1, P0 P3 e P4 in output) ---
sudo i2cset -y 3 $ioExpAddr 0x01 0xFF
sudo i2cset -y 3 $ioExpAddr 0x03 0xE6

# --- seleziona l'eeprom (con LED on) ---
sudo i2cset -y 3 $ioExpAddr 0x01 0xE6


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

    # --- writing HW_INFO and SERIAL ---
    echo "> Writing hardware info and serial..."
    if [ $debug -eq 1 ]; then
      sudo i2ctransfer 3 w17@0x54 0x00$hwInfo $serial
    else
      sudo i2ctransfer -y 3 w17@0x54 0x00$hwInfo  $serial
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
