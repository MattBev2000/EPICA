# Permette di leggere 8 pagine di 32 byte dall'EEPROM (M24C64) della scheda EK26
# fornendo un offset di pagina (0x00 a 0x1F).
# Addizionalmente, la pagina Identification Page viene sempre letta.
#
# Usage:
#   - eep_read_EK26.sh PAGE_OFFSET
#
# Esempio:
#   - sudo ./eep_read_EK26.sh 0x00

# --- version ---
version="1.1"
date="12/05/2025"
echo "> script \"$0\", v$version ($date)"

# --- args control ---
if [ $# -ne 1 ]; then
	echo "> Wrong arguments number, expected 1 !!!"
	echo "> Usage: \"$0 PAGE_OFFSET (with PAGE_OFFSET equal 0x00 to 0x1F)\""
	exit 1
fi

# --- args length control ---
if [ ${#1} -ne 4 ]; then
	echo "> Wrong length for \"$1\", must be 4 chars (0x00, 0x01, ..., 0x1F) !!!"
	exit 1
fi

# --- args value control ---
#if [ $1 -ne 4 ]; then
	#echo "> Wrong value for \"$1\", must be 0x00 to 0x1F !!!"
	#exit 1
#fi

# --- legge 8 pagina della eeprom ---
echo "> Reading eeprom..."
echo ">"
#
# --- legge 32 byte ---
echo "> Address $100 (0):"
eepDump=$(sudo i2ctransfer -f -y 1 w2@0x51 $1 0x00 r32)
while IFS= read -r line; do
	echo "> $line"  
done <<< "$eepDump"
# stampa in ascii
text=$(echo "${eepDump//0x/"\x"}")
text=$(echo "${text// /""}")
echo -e "> $text"
#
# --- legge 32 byte ---
echo "> Address $120 (1):"
eepDump=$(sudo i2ctransfer -f -y 1 w2@0x51 $1 0x20 r32)
while IFS= read -r line; do
	echo "> $line"  
done <<< "$eepDump"
# stampa in ascii
text=$(echo "${eepDump//0x/"\x"}")
text=$(echo "${text// /""}")
echo -e "> $text"
#
# --- legge 32 byte ---
echo "> Address $140 (2):"
eepDump=$(sudo i2ctransfer -f -y 1 w2@0x51 $1 0x40 r32)
while IFS= read -r line; do
	echo "> $line"  
done <<< "$eepDump"
# stampa in ascii
text=$(echo "${eepDump//0x/"\x"}")
text=$(echo "${text// /""}")
echo -e "> $text"
#
# --- legge 32 byte ---
echo "> Address $160 (3):"
eepDump=$(sudo i2ctransfer -f -y 1 w2@0x51 $1 0x60 r32)
while IFS= read -r line; do
	echo "> $line"  
done <<< "$eepDump"
# stampa in ascii
text=$(echo "${eepDump//0x/"\x"}")
text=$(echo "${text// /""}")
echo -e "> $text"
#
# --- legge 32 byte ---
echo "> Address $180 (4):"
eepDump=$(sudo i2ctransfer -f -y 1 w2@0x51 $1 0x80 r32)
while IFS= read -r line; do
	echo "> $line"  
done <<< "$eepDump"
# stampa in ascii
text=$(echo "${eepDump//0x/"\x"}")
text=$(echo "${text// /""}")
echo -e "> $text"
#
# --- legge 32 byte ---
echo "> Address $1A0 (5):"
eepDump=$(sudo i2ctransfer -f -y 1 w2@0x51 $1 0xA0 r32)
while IFS= read -r line; do
	echo "> $line"  
done <<< "$eepDump"
# stampa in ascii
text=$(echo "${eepDump//0x/"\x"}")
text=$(echo "${text// /""}")
echo -e "> $text"
#
# --- legge 32 byte ---
echo "> Address $1C0 (6):"
eepDump=$(sudo i2ctransfer -f -y 1 w2@0x51 $1 0xC0 r32)
while IFS= read -r line; do
	echo "> $line"  
done <<< "$eepDump"
# stampa in ascii
text=$(echo "${eepDump//0x/"\x"}")
text=$(echo "${text// /""}")
echo -e "> $text"
#
# --- legge 32 byte ---
echo "> Address $1E0 (7):"
eepDump=$(sudo i2ctransfer -f -y 1 w2@0x51 $1 0xE0 r32)
while IFS= read -r line; do
	echo "> $line"  
done <<< "$eepDump"
# stampa in ascii
text=$(echo "${eepDump//0x/"\x"}")
text=$(echo "${text// /""}")
echo -e "> $text"


# --- legge la pagina Identification Page della eeprom ---
echo ">"
echo "> Identification Page:"
eepDump=$(sudo i2ctransfer -f -y 1 w2@0x59 0x00 0x00 r32)
while IFS= read -r line; do
	echo "> $line"
done <<< "$eepDump"

