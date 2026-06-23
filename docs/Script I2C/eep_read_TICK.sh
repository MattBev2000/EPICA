# Permette di leggere i dati di una EEPROM 24AA025 di una scheda TICK.

# --- version ---
version="1.0"
date="09/05/2025"
echo "> script \"$0\", v$version ($date)"

# --- reading data ---
echo "> Reading eeprom..."
eepDump=$(sudo i2cdump -y 3 0x53 b)
#eepDump=$(sudo i2cdump -y 3 0x54 b)
while IFS= read -r line; do
	echo "> $line"
done <<< "$eepDump"
