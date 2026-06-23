# Permette di pilotare in uscita un IO Expander (PCA9534) di una scheda PBI5, 
# A20I2 o A20C5 fornendo l'indirizzo della scheda (0 7) e lo stato della porta (8 bit).
# Stato pin porta: 0 basso, 1 alto.
#
# Usage:
#   - ioexp_write_output.sh BOARD_ADDR PORT_STATE
#
# Esempio:
#   - sudo ./ioexp_write_output.sh 5 0xFF (Tutti i pin a 1, 0b1111 1111, LED spento e EEPROM non selezionata)
#   - sudo ./ioexp_write_output.sh 5 0xFE (Led acceso, 0b1111 1110)
#   - sudo ./ioexp_write_output.sh 5 0xE6 (Led acceso e EEPROM selezionata, 0b1110 0110)

# --- version ---
version="1.0"
date="09/05/2025"
echo "> script \"$0\", v$version ($date)"

# --- args control ---
if [ $# -ne 2 ]; then
	echo "> Wrong arguments number, expected 2 !!!"
	echo "> Usage: \"$0 BOARD_ADDR PORT_STATE\""
  echo "> Usage: \"with BOARD_ADDR: 0 to 7\""
  echo "> Usage: \"with PORT_STATE: 0x00 to 0xFF\""
	exit 1
fi

# --- args length control ---
if [ ${#1} -ne 1 ]; then
	echo "> Wrong length for \"$1\", must be 1 char !!!"
	exit 1
fi
if [ ${#2} -ne 4 ]; then
	echo "> Wrong length for \"$2\", must be 4 chars (0x00, 0x01, ..., 0xFF) !!!"
	exit 1
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

# --- configura l'IO Expander ---
sudo i2cset -y 3 $ioExpAddr 0x01 $2

echo "> Script executed"
