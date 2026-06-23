#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

// #include <fcntl.h>
// #include <linux/i2c.h>
// #include <linux/i2c-dev.h>
// #include <sys/ioctl.h>
// #include <unistd.h>

#include "main.h"
#include "periph-uart.h"


// *** variabili *************************************************

uart_cfg uartConfiguration;    // struttura di configurazione
char *periphUartPrefix = PRINT_OUTPUT__PERIPH_UART_PREFIX;


// *** funzioni *************************************************

// inizializzazione e apertura porta
// return:
//  - UART_RES__OK
//  - UART_RES__CONFIG_ERROR
int PeriphUART_Open(void)
{
    int ret = UART_RES__OK;

    // Initialize every thing to default
    init_uart_cfg(&uartConfiguration);

    // Set port and baudrate
    strcpy(uartConfiguration.port, UART_DEV);
    uartConfiguration.baudrate = UART_BAUDRATE;

	  // Set other stuff
    // Number of bits per byte
    uartConfiguration.nbits_per_byte                = 8;
    // parity check is off by default
    uartConfiguration.enable_parity_check           = false;
    // we use a single stop bit by default
    uartConfiguration.enable_two_stop_bits          = false;
    // by default hardware flow control is off
    uartConfiguration.enable_hw_flow_control        = false;
    // by default software flow control is off
    uartConfiguration.enable_sw_flow_control        = false;
    // by default echo is disabled
    uartConfiguration.enable_echo                   = false;
    // by default erasure is disabled
    uartConfiguration.enable_erasure                = false;
    // by default new line echo is disabled
    uartConfiguration.enable_newline_echo           = false;
    // by default new special bytes handling is deactivated
    uartConfiguration.enable_bytes_special_handling = false;

    // by default minimum number of bytes is 0
    uartConfiguration.V_MIN                         = 0;
    // by default maximum time between bytes is 10 deciseconds (1s)
    uartConfiguration.V_TIME                        = 1; // 10;

    //NOTE.
    //VMIN = 0 and VTIME > 0
    //This is a pure timed read. If data are available in the input queue, it's transferred to the caller's 
    //buffer up to a maximum of nbytes, and returned immediately to the caller. Otherwise the driver blocks 
    //until data arrives, or when VTIME tenths expire from the start of the call. If the timer expires without data, zero is returned.
    //Warning: VMIN = 0 and VTIME > 0 is a read with a timeout, rather than a timed read. 
    //This read does not wait the VTIME duration and then return what is available. The timeout 
    //occurs only if no character are available. Otherwise the read returns immediately 
    //as soon as any characters are available.

    //VMIN = 0 and VTIME = 0
    //This is a completely non-blocking read - the call is satisfied immediately directly from the driver's input queue.
    //Don't use this mode unless you really, really know what you're doing.

    //VMIN > 0 and VTIME = 0
    //This is a counted read that is satisfied only when at least VMIN characters have been transferred to 
    //the caller's buffer - there is no timing component involved. This read can be satisfied from the driver's 
    //input queue (where the call could return immediately), or by waiting for new data to arrive: in this respect the call could block indefinitely.

    //VMIN > 0 and VTIME > 0
    //A read() is satisfied when either VMIN characters have been transferred to the caller's buffer, 
    //or when VTIME tenths expire between characters. Since this timer is not started until the first 
    //character arrives, this call can block indefinitely if the serial line is idle. This is the most 
    //common mode of operation, and we consider VTIME to be an intercharacter timeout, not an overall one. This call should never return zero bytes read.

    //Note when VMIN=1 that the VTIME specification will be irrelevant. The availability of any data will always 
    //satisfy the minimum criterion of a single byte, so the time criterion can be ignored

	  // Activate low latency mode
    uart_activate_low_latency(&uartConfiguration);

	  // Set reception buffer size
    uart_set_buffer_sizes(&uartConfiguration, UART_BUFF_SIZE);

    // configure UART
    #ifdef PRINT_OUTPUT__PERIPH_UART
    sprintf(outStr, "Configuring %s... ", uartConfiguration.port);
    Sys_PrintOutput(PT_YES, INF_EXT, periphUartPrefix, outStr);
    #endif
    //
    if(configure_uart(&uartConfiguration))
    {	 
        #ifdef PRINT_OUTPUT__PERIPH_UART
        Sys_PrintOutput(PT_NO, INF_EXT, "", "OK\n");
        #endif
    }
    else
    {       
        ret = UART_RES__CONFIG_ERROR;

        #ifdef PRINT_OUTPUT__PERIPH_UART
        Sys_PrintOutput(PT_NO, INF_EXT, "", "ERROR !!!\n");
        #endif
    }

    // TEST
    //uart_drive_control_line(&uartConfiguration, TIOCM_RTS, 1);

	  return ret;
}


// chiusura porta
void PeriphUART_Close(void)
{
    #ifdef PRINT_OUTPUT__PERIPH_UART
    sprintf(outStr, "Unconfigure %s... ", uartConfiguration.port);
    Sys_PrintOutput(PT_YES, INF_EXT, periphUartPrefix, outStr);
    #endif

    unconfigure_uart(&uartConfiguration);

    #ifdef PRINT_OUTPUT__PERIPH_UART
    Sys_PrintOutput(PT_NO, INF_EXT, "", "DONE\n");
    #endif
}


// invia e riceve dati
// param:
//  - tx_buff         : buffer con i dati da inviare
//  - byte_to_send    : numero di byte da inviare
//  - wait_ans        : se aspettare o no una risposta
//  - rx_buff         : buffer per i dati ricevuti
//  - byte_to_received: numero massimo di byte che il driver si aspetta di ricevere (se riceve meno va in timeout, vd. lib uart)
//  - byte_received   : numero effettivi di byte ricevuti
// return:
//  - UART_RES__OK
//  - UART_RES__SENDING_ERROR
int PeriphUART_SendReceive(uint8_t *tx_buff, uint8_t byte_to_send, bool wait_ans, uint8_t *rx_buff, uint8_t byte_to_received, uint8_t *byte_received)
{
    #ifdef PRINT_OUTPUT__PERIPH_UART
    sprintf(outStr, "Tx %dB:", byte_to_send);
    Sys_PrintOutput(PT_YES, INF_EXT, periphUartPrefix, outStr);

	  for(int i=0; i<byte_to_send; i++)
    {
        sprintf(outStr, " 0x%02X", tx_buff[i]);
        Sys_PrintOutput(PT_NO, INF_EXT, "", outStr);
    }
	  Sys_PrintOutput(PT_NO, INF_EXT, "", "\n");
    #endif

    // tx
    int size = write(uartConfiguration.fd, tx_buff, byte_to_send);
    if(size != byte_to_send)
    {
        return UART_RES__SENDING_ERROR;
    }

    // attesa risposta
    if(wait_ans)
    {
        // rx
        *byte_received = read(uartConfiguration.fd, rx_buff, byte_to_received);

        #ifdef PRINT_OUTPUT__PERIPH_UART
        sprintf(outStr, "Rx %dB:", *byte_received);
        Sys_PrintOutput(PT_YES, INF_EXT, periphUartPrefix, outStr);

        for(int i=0; i<*byte_received; i++)
        {
            sprintf(outStr, " 0x%02X", rx_buff[i]);
            Sys_PrintOutput(PT_NO, INF_EXT, "", outStr);
        }        
        Sys_PrintOutput(PT_NO, INF_EXT, "", "\n");
        #endif
    }
    else
    {
        #ifdef PRINT_OUTPUT__PERIPH_UART
        Sys_PrintOutput(PT_YES, INF_EXT, periphUartPrefix, "Skip rx !!!\n");
        #endif
    }

    return UART_RES__OK;
}

