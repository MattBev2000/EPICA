# Permette di deselezionare una EEPROM (24AA025) di una scheda PBI5, A20I2 o
# A20C5 fornendo l'indirizzo della scheda (0 a 7).
# Viene anche spento il led corrispondente.
#
# Usage:
#   - eep_unselect BOARD_ADDR
#
# Esempio:
#   - sudo ./eep_unselect.sh 5

# --- version ---
version="1.0"
date="09/05/2025"
echo "> script \"$0\", v$version ($date)"

# --- args control ---
if [ $# -ne 1 ]; then
	echo "> Wrong arguments number, expected 1 !!!"
	echo "> Usage: \"$0 BOARD_ADDR (with BOARD_ADDR equal 0 to 7)\""
	exit 1
fi

# --- args length control ---
if [ ${#1} -ne 1 ]; then
	echo "> Wrong length for \"$1\", must be 1 char !!!"
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

# --- deseleziona l'eeprom (con LED off) ---
sudo ./ioexp_write_output.sh $1 0xFF

# --- configura l'IO Expander (tutti pin a 1, in input) ---
sudo ./ioexp_write_config.sh $1 0xFF
