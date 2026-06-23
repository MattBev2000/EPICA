# Permette di scrivere dati dentro una EEPROM (24AA025) di una scheda TICK fornendo:
#   1. la modalità di scrittura: BYTE (b) o INFO (i)
#   2. i dati da scrivere:
#     - in modalità BYTE scrive la pagina intera (16 byte)
#     - in modalità INFO scrive:
#         - HW_INFO_1 sui primi 10 byte della prima pagina
#         - SERIAL_1  sugli ultimi 6 byte della prima pagina
#         - HW_INFO_2 sui primi 10 byte della seconda pagina
#         - SERIAL_2  sugli ultimi 6 byte della seconda pagina
#
# Usage:
#   - BYTE mode: eep_write_gen_TICK b PAGE_OFFSET BYTES_TO_WRITE
#                con PAGE_OFFSET uguale 0x00, 0x10, 0x20, ..., 0x70 (0x80 a 0xF0 sono write protected !!!)
#   - INFO mode: eep_write_gen_TICK i HW_INFO_1 SERIAL_1 HW_INFO_2 SERIAL_2
#
# Esempi:
#   - sudo ./eep_write_gen_TICK.sh b 0x20 "0x00 0x01 0x02 0x03 0x04 0x05 0x06 0x07 0x08 0x09 0x0A 0x0B 0x0C 0x0D 0x0E 0x0F"
#   - sudo ./eep_write_gen_TICK.sh b 0x30 "0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF 0xFF"
#   - sudo ./eep_write_gen_TICK.sh i "TICK 1.2" "SN1234" "TICKFP 1.1" "SN1234"


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
if [ $# -lt 3 ]; then
    echo "> Wrong arguments number, expected at least 3 !!!"
    echo "> Usage: \"$0 \"b\" PAGE_OFFSET BYTES_TO_WRITE\""
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
    if [ $# -ne 3 ]; then
        echo "> Wrong arguments number, expected 3 !!!"
        echo "> Usage: \"$0 \"b\" PAGE_OFFSET BYTES_TO_WRITE\""
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
        echo "> Usage: \"$0 \"b\" PAGE_OFFSET BYTES_TO_WRITE\""
        echo "> Usage: \"$0 \"i\" HW_INFO_1 SERIAL_1 HW_INFO_2 SERIAL_2\""
        exit 1    
    fi
fi


# *** DEBUG ***
if [ $debug -eq 1 ]; then
	  echo "--> Mode      (len): $1 (${#1})"

    # BYTE
    if [ "$1" = "b" ]; then
        echo "--> PageOffset(len): $2 (${#2})"
        echo "--> Bytes     (len): $3 (${#3})"
    else # INFO
      	echo "--> HwInfo_1  (len): $2 (${#2})"
    	  echo "--> Serial_1  (len): $3 (${#3})"        
      	echo "--> HwInfo_2  (len): $4 (${#4})"
    	  echo "--> Serial_2  (len): $5 (${#5})"
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
    if [ ${#3} -ne 79 ]; then
        echo "> Wrong length for \"$3\", must be 79 chars !!!"
        exit 1
    fi    
else # INFO mode

    if [ ${#2} -gt 10 ]; then
        echo "> Wrong length for \"$2\", max 10 chars !!!"
        exit 1
    fi
    #
    if [ ${#3} -ne 6 ]; then
        echo "> Wrong length for \"$3\", must be 6 chars !!!"
        exit 1
    fi
    #
    if [ ${#4} -gt 10 ]; then
        echo "> Wrong length for \"$4\", max 10 chars !!!"
        exit 1
    fi
    #
    if [ ${#5} -ne 6 ]; then
        echo "> Wrong length for \"$5\", must be 6 chars !!!"
        exit 1
    fi    
fi


# --- BYTE MODE MANAGEMENT ---
if [ "$1" = "b" ]; then

    # --- ask for confirmation ---
    echo "> Data to be written:"
    echo "> Page Offset:\"$2\""
    echo "> Bytes      :\"$3\""
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
    for (( i=1; i<=(10-${#2}); i++ ))
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
    for (( i=1; i<=(10-${#4}); i++ ))
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
      sudo i2ctransfer 3 w17@0x53 $2 $3
      #sudo i2ctransfer 3 w17@0x54 $2 $3
    else
      sudo i2ctransfer -y 3 w17@0x53 $2 $3
      #sudo i2ctransfer -y 3 w17@0x54 $2 $3
    fi

else # INFO

    # --- writing HW_INFO_1 and SERIAL_1 ---
    echo "> Writing hardware info 1 and serial 1 ..."
    if [ $debug -eq 1 ]; then
      sudo i2ctransfer 3 w17@0x53 0x00$hwInfo1 $serial1
      #sudo i2ctransfer 3 w17@0x54 0x00$hwInfo1 $serial1
    else
      sudo i2ctransfer -y 3 w17@0x53 0x00$hwInfo1 $serial1
      #sudo i2ctransfer -y 3 w17@0x54 0x00$hwInfo1  $serial1
    fi

    # --- writing HW_INFO_2 and SERIAL_2 ---
    echo "> Writing hardware info 2 and serial 2 ..."
    if [ $debug -eq 1 ]; then
      sudo i2ctransfer 3 w17@0x53 0x10$hwInfo2 $serial2
      #sudo i2ctransfer 3 w17@0x54 0x10$hwInfo2 $serial2
    else
      sudo i2ctransfer -y 3 w17@0x53 0x10$hwInfo2  $serial2
      #sudo i2ctransfer -y 3 w17@0x54 0x10$hwInfo2  $serial2
    fi    
fi


# --- reading data ---
echo "> Reading eeprom..."
eepDump=$(sudo i2cdump -y 3 0x53 b)
#eepDump=$(sudo i2cdump -y 3 0x54 b)
while IFS= read -r line; do
	echo "> $line"
done <<< "$eepDump"


exit 0
