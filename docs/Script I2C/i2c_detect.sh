# Permette di sapere i bus I2C installati e i dispositivi I2C visti.

# --- version ---
version="1.0"
date="09/05/2025"
echo "> script \"$0\", v$version ($date)"

# lista bus I2C
echo ">"
echo "> List of installed busses:"
sudo i2cdetect -l

# lista dispositivi su ogni bus I2C
echo ">"
echo "> List of detected devices on bus 1:"
sudo i2cdetect -y -r 1
echo ">"
echo "> List of detected devices on bus 2:"
sudo i2cdetect -y -r 2
echo ">"
echo "> List of detected devices on bus 3:"
sudo i2cdetect -y -r 3
echo ">"
echo "> List of detected devices on bus 4:"
sudo i2cdetect -y -r 4
echo ">"
echo "> List of detected devices on bus 5:"
sudo i2cdetect -y -r 5

# Interpreting the Output
echo ">"
echo "> Output meaning:"
echo ">   \"--\" The address was probed but no chip answered."
echo ">   \"UU\" Probing was skipped, because this address is currently in use by a driver. This strongly suggests that there is a chip at this address."
echo ">   \"HH\" Address number in hexadecimal. A chip was found at this address."
