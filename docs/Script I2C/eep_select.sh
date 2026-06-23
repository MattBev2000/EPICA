# Permette di selezionare una EEPROM (24AA025) di una scheda PBI5, A20I2,
# A20C5, AS20P2 o IOHS fornendo l'indirizzo della scheda (0 a 7).
# Viene anche acceso il led corrispondente (2 led per la scheda IOHS).
#
# Usage:
#   - eep_select BOARD_ADDR
#
# Esempio:
#   - sudo ./eep_select.sh 5

# --- version ---
version="1.1"
date="14/01/2026"
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

# --- configura l'IO Expander (tutti pin a 1 e P0, P1, P3, e P4 in output) ---
sudo ./ioexp_write_config.sh $1 0xE4

# --- seleziona l'eeprom (con LED on) ---
sudo ./ioexp_write_output.sh $1 0xE4
