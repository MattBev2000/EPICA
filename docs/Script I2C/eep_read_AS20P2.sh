# Permette di leggere una EEPROM (24AA025) di una scheda AS20P2
# fornendo l'indirizzo dello slot (0 a 7) della scheda
#
# Usage:
#   - eep_read_AS20P2.sh BOARD_ADDR
#
# Esempio:
#   - sudo ./eep_read_AS20P2.sh 5

# --- version ---
version="1.0"
date="25/07/2025"
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
#
ioExpAddr=0x2$1

# --- configura l'IO Expander (tutti pin a 1, P0 P3 e P4 in output) ---
sudo i2cset -y 3 $ioExpAddr 0x01 0xFF
sudo i2cset -y 3 $ioExpAddr 0x03 0xE6

# --- seleziona l'eeprom (con LED on) ---
sudo i2cset -y 3 $ioExpAddr 0x01 0xE6

# --- reading data ---
echo "> Reading eeprom..."
eepDump=$(sudo i2cdump -y 3 0x54 b)
while IFS= read -r line; do
	echo "> $line"
done <<< "$eepDump"

# --- deseleziona l'eeprom (con LED off) ---
sudo i2cset -y 3 $ioExpAddr 0x01 0xFF
