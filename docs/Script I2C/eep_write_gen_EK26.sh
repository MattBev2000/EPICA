# Permette di scrivere dati dentro l'EEPROM (M24C64) della scheda EK26 fornendo:
#   1. la modalità di scrittura: BYTE (b) o INFO (i)
#   2. i dati da scrivere:
#     - in modalità BYTE scrive una pagina intera (32 byte)
#     - in modalità INFO scrive:
#         - HW_INFO_1 sui byte  1 a 16 della prima pagina
#         - SERIAL_1  sui byte 17 a 32 della prima pagina
#         - HW_INFO_2 sui byte  1 a 16 della seconda pagina
#         - SERIAL_2  sui byte 17 a 32 della seconda pagina
#
# Usage:
#   - BYTE mode: eep_write_gen_EK26 b PAGE_OFFSET PAGE_SUB_OFFSET BYTES_TO_WRITE
#                con PAGE_OFFSET uguale 0x00, 0x01, 0x02, ..., 0x1F
#                e con PAGE_SUB_OFFSET uguale 0, 1, 2, 3, 4, 5, 6 o 7
#   - INFO mode: eep_write_gen_EK26 i HW_INFO_1 SERIAL_1 HW_INFO_2 SERIAL_2
#
# Esempi:
#   - sudo ./eep_write_gen_EK26.sh b 0x01 0 "0x00 0x01 0x02 0x03 0x04 0x05 0x06 0x07 0x08 0x09 0x0A 0x0B 0x0C 0x0D 0x0E 0x0F 0x10 0x11 0x12 0x13 0x14 0x15 0x16 0x17 0x18 0x19 0x1A 0x1B 0x1C 0x1D 0x1E 0x1F"
#   - sudo ./eep_write_gen_EK26.sh b 0x01 1 "0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF"
#   - sudo ./eep_write_gen_EK26.sh i "EK26 1.2" "SN1234" "EKFP 1.1" "SN1234"
#
# NB: utilizzare il DTR della seconda COM per attivare la scrittura dentro l'EEPROM


# *** DEBUG ***
debug=0


# --- version ---
version="1.0"
date="13/05/2025"
echo "> script \"$0\", v$version ($date)"


# *** DEBUG ***
if [ $debug -eq 1 ]; then	
	  echo "--> $# arguments"
fi	


# --- args control ---
# controllo numero argomenti
if [ $# -lt 4 ]; then
    echo "> Wrong arguments number, expected al least 4 !!!"
    echo "> Usage: \"$0 \"b\" PAGE_OFFSET PAGE_SUB_OFFSET BYTES_TO_WRITE\""
    echo "> Usage: \"$0 \"i\" HW_INFO_1 SERIAL_1 HW_INFO_2 SERIAL_2\""
    exit 1
fi
# controllo modalità, BYTE O INFO
if [ "$1" = "b" ]; then
    # *** DEBUG ***
    if [ $debug -eq 1 ]; then	
        echo "--> BYTE mode"
    fi	

    # controllo numero argomenti
    if [ $# -ne 4 ]; then
        echo "> Wrong arguments number, expected 4 !!!"
        echo "> Usage: \"$0 \"b\" PAGE_OFFSET PAGE_SUB_OFFSET BYTES_TO_WRITE\""
        exit 1
    fi

else
    if [ "$1" = "i" ]; then
        # *** DEBUG ***
        if [ $debug -eq 1 ]; then	
            echo "--> INFO mode"
        fi	    

        # controllo numero argomenti
        if [ $# -ne 5 ]; then
            echo "> Wrong arguments number, expected 5 !!!"
            echo "> Usage: \"$0 \"i\" HW_INFO_1 SERIAL_1 HW_INFO_2 SERIAL_2\""
            exit 1
        fi

    else
        # modalità non corretta
        echo "> Wrong mode !!!"
        echo "> Usage: \"$0 \"b\" PAGE_OFFSET PAGE_SUB_OFFSET BYTES_TO_WRITE\""
        echo "> Usage: \"$0 \"i\" HW_INFO_1 SERIAL_1 HW_INFO_2 SERIAL_2\""
        exit 1
    fi
fi


# *** DEBUG ***
if [ $debug -eq 1 ]; then
	  echo "--> Mode         (len): $1 (${#1})"

    # BYTE
    if [ "$1" = "b" ]; then
        echo "--> PageOffset   (len): $2 (${#2})"
        echo "--> PageSubOffset(len): $3 (${#3})"
        echo "--> Bytes        (len): $4 (${#4})"
    else # INFO
      	echo "--> HwInfo_1     (len): $2 (${#2})"
    	  echo "--> Serial_1     (len): $3 (${#3})"        
      	echo "--> HwInfo_2     (len): $4 (${#4})"
    	  echo "--> Serial_2     (len): $5 (${#5})"
    fi
fi


# --- args length control ---
if [ ${#1} -ne 1 ]; then
	  echo "> Wrong length for \"$1\", must be 1 char !!!"
	  exit 1
fi
#
# BYTE mode
if [ "$1" = "b" ]; then 

    if [ ${#2} -ne 4 ]; then
        echo "> Wrong length for \"$2\", must be 4 chars !!!"
        exit 1
    fi
    #
    if [ ${#3} -ne 1 ]; then
        echo "> Wrong length for \"$3\", must be 1 char !!!"
        exit 1
    fi
    #
    if [ ${#4} -ne 159 ]; then
        echo "> Wrong length for \"$4\", must be 159 chars !!!"
        exit 1
    fi 
else # INFO mode

    if [ ${#2} -gt 16 ]; then
        echo "> Wrong length for \"$2\", max 16 chars !!!"
        exit 1
    fi
    #
    if [ ${#3} -gt 16 ]; then
        echo "> Wrong length for \"$3\", max 16 chars !!!"
        exit 1
    fi
    #
    if [ ${#4} -gt 16 ]; then
        echo "> Wrong length for \"$4\", max 16 chars !!!"
        exit 1
    fi
    #
    if [ ${#5} -gt 16 ]; then
        echo "> Wrong length for \"$5\", max 16 chars !!!"
        exit 1
    fi    
fi


# --- BYTE MODE MANAGEMENT ---
if [ "$1" = "b" ]; then

    # --- args value control ---
    # check for number 
    case $3 in
        ''|*[!0-9]*) error=1;;
        *) error=0;;
    esac
    #
    # error notification
    if [ $error -eq 1 ]; then
      echo "> \"$3\" not a number (expected \"0\" to \"7\") !!!"
      exit 1
    fi
    #
    # check for value
    if [ $3 -gt 7 ]; then
        echo "> Wrong value ($3), expected \"0\" to \"7\" !!!"
        exit 1
    fi
    #    
    pageSubOffset=$3
    pageSubOffset=$((pageSubOffset * 32))
    pageSubOffsetNo0x=$( printf '%02x' $pageSubOffset )
    pageSubOffset=$( printf '0x%02x' $pageSubOffset )


    # --- ask for confirmation ---
    echo "> Data to be written:"
    echo "> Page Offset    :\"$2\""
    echo "> Page Sub Offset:\"$3\""
    echo "> Bytes          :\"$4\""
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
    hwInfo1=$(echo $2 | hexdump -v -e ''${#2}'/1 " 0x%02X"' -n ${#2})
    #
    # add remaining bytes to 0x00
    for (( i=1; i<=(16-${#2}); i++ ))
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
    serial1=$(echo $3 | hexdump -v -e ''${#3}'/1 " 0x%02X"' -n ${#3})
    #
    # add remaining bytes to 0x00
    for (( i=1; i<=(16-${#3}); i++ ))
    do 
        serial1+=" 0x00"
    done

    # *** DEBUG ***
    if [ $debug -eq 1 ]; then
        echo "--> serial1 (hex): $serial1"
    fi


    # --- get HW_INFO_2 ---
    #
    # hexdump
    hwInfo2=$(echo $4 | hexdump -v -e ''${#4}'/1 " 0x%02X"' -n ${#4})
    #
    # add remaining bytes to 0x00
    for (( i=1; i<=(16-${#4}); i++ ))
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
    serial2=$(echo $5 | hexdump -v -e ''${#5}'/1 " 0x%02X"' -n ${#5})
    #
    # add remaining bytes to 0x00
    for (( i=1; i<=(16-${#5}); i++ ))
    do 
        serial2+=" 0x00"
    done

    # *** DEBUG ***
    if [ $debug -eq 1 ]; then
        echo "--> serial2 (hex): $serial2"
    fi


    # --- ask for confirmation ---
    echo "> Data to be written:"
    echo "> HW Info 1:\"$hwInfo1\" (\"$2\", len: ${#2} bytes)"
    echo "> Serial  1:\"$serial1\" (\"$3\", len: ${#3} bytes)"
    echo "> HW Info 2:\"$hwInfo2\" (\"$4\", len: ${#4} bytes)"
    echo "> Serial  2:\"$serial2\" (\"$5\", len: ${#5} bytes)"    
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


# --- write ---
# BYTE
if [ "$1" = "b" ]; then

    # --- writing page ---
    echo "> Writing page..."
    if [ $debug -eq 1 ]; then
      sudo i2ctransfer -f 1 w34@0x51 $2 $pageSubOffset $4
    else
      sudo i2ctransfer -f -y 1 w34@0x51 $2 $pageSubOffset $4
    fi

else # INFO

    # --- writing HW_INFO_1 and SERIAL_1 ---
    echo "> Writing hardware info 1 and serial 1 ..."
    if [ $debug -eq 1 ]; then
      sudo i2ctransfer -f 1 w34@0x51 0x00 0x00$hwInfo1 $serial1
    else
      sudo i2ctransfer -f -y 1 w34@0x51 0x00 0x00$hwInfo1 $serial1
    fi  

    # --- writing HW_INFO_2 and SERIAL_2 ---
    echo "> Writing hardware info 2 and serial 2 ..."
    if [ $debug -eq 1 ]; then
      sudo i2ctransfer -f 1 w34@0x51 0x00 0x20$hwInfo2 $serial2
    else
      sudo i2ctransfer -f -y 1 w34@0x51 0x00 0x20$hwInfo2 $serial2
    fi          
fi


# --- reading data ---
#
# BYTE
if [ "$1" = "b" ]; then

    echo "> Reading eeprom..."
    echo ">"
    echo "> Address $2$pageSubOffsetNo0x:"

    eepDump=$(sudo i2ctransfer -f -y 1 w2@0x51 $2 $pageSubOffset r32)
    while IFS= read -r line; do
      echo "> $line"  
    done <<< "$eepDump"

else # INFO

    echo "> Reading eeprom..."
    echo ">"

    # --- legge 32 byte ---
    echo "> Address 0x0000:"
    eepDump=$(sudo i2ctransfer -f -y 1 w2@0x51 0x00 0x00 r32)
    while IFS= read -r line; do
      echo "> $line"  
    done <<< "$eepDump"
    # stampa in ascii
    text=$(echo "${eepDump//0x/"\x"}")
    text=$(echo "${text// /""}")
    echo -e "> $text"    

    # --- legge 32 byte ---
    echo "> Address 0x0020:"
    eepDump=$(sudo i2ctransfer -f -y 1 w2@0x51 0x00 0x20 r32)
    while IFS= read -r line; do
      echo "> $line"  
    done <<< "$eepDump"
    # stampa in ascii
    text=$(echo "${eepDump//0x/"\x"}")
    text=$(echo "${text// /""}")
    echo -e "> $text"
fi


exit 0
