
#ifndef __PERIPH_UART_H_
#define __PERIPH_UART_H_

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>
#include <uart.h>


// *** define *************************************************

#define PRINT_OUTPUT__PERIPH_UART               // utilizzare il livello INF_EXT
#define PRINT_OUTPUT__PERIPH_UART_PREFIX ""     // "UAx " // prefisso per periph-uart.c

#define UART_DEV                "/dev/ttyPS0" // TEST "/dev/ttyUSB2"
#define UART_BAUDRATE           115200
#define UART_BUFF_SIZE          128

#define UART_RES__OK            0
#define UART_RES__CONFIG_ERROR  1
#define UART_RES__SENDING_ERROR 2


// *** prototipi *************************************************

int  PeriphUART_Open(void);
void PeriphUART_Close(void);
int  PeriphUART_SendReceive(uint8_t *tx_buff, uint8_t byte_to_send, bool wait_ans, uint8_t *rx_buff, uint8_t byte_to_received, uint8_t *byte_received);

#ifdef __cplusplus
}
#endif

#endif /* __PERIPH_UART_H_ */
