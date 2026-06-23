
#ifndef __PERIPH_SYS_H_
#define __PERIPH_SYS_H_

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>


// *** define *************************************************

#define PRINT_OUTPUT__PERIPH_SYS                // utilizzare il livello INF_STD

// prefisso per periph-sys.c
#define PRINT_OUTPUT__PERIPH_SYS_PREFIX ""      // per testUtil
//#define PRINT_OUTPUT__PERIPH_SYS_PREFIX "PHL "  // per eladScpiServer

// General
#define PERIPH_RES__OK                    0 
#define PERIPH_RES__START_ERROR           1
#define PERIPH_RES__UART_CONFIG_ERROR     2
// UART
#define PERIPH_RES__WRONG_BOARD_ADDR      10
#define PERIPH_RES__WRONG_BOARD_SUB_ADDR  11
#define PERIPH_RES__TOO_MANY_BYTE         12
#define PERIPH_RES__UART_SENDING_ERROR    13
#define PERIPH_RES__NO_ANSWER_RECEIVED    14
// I2C
#define PERIPH_RES__WRONG_PAGE_IDX        20
#define PERIPH_RES__IOEXP_CONFIG1_ERROR   21
#define PERIPH_RES__IOEXP_CONFIG2_ERROR   22
#define PERIPH_RES__IOEXP_DRIVE1_ERROR    23
#define PERIPH_RES__IOEXP_DRIVE2_ERROR    24
#define PERIPH_RES__EEP_READ_Sx_ERROR     25
#define PERIPH_RES__EEP_READ_TI_ERROR     26
#define PERIPH_RES__EEP_READ_EK_ERROR     27
#define PERIPH_RES__EEP_WRITE_Sx_ERROR    28
#define PERIPH_RES__EEP_WRITE_TI_ERROR    29
#define PERIPH_RES__EEP_WRITE_EK_ERROR    30

// tipo di cassetto
#define SYS_TYP__UNKNOWN    0x00  // sconosciuto
#define SYS_TYP__CASES_POL  0x01  // CASES polarizzato
#define SYS_TYP__CASES_NPL  0x02  // CASES non polarizzato sx
#define SYS_TYP__CASES_NPR  0x04  // CASES non polarizzato dx
#define SYS_TYP__EPICA      0x08  // EPICA
#define SYS_TYP__MSK        0x0F  // maschera tipi cassetti
//
#define SYS_TYP__ERR  0x10  // flag casetto non completo

// board address
#define BA_NONE   '-'

// board codes
#define BC_NONE   '-'
#define BC_EK26   'E'
#define BC_PBI5   'P'
#define BC_A20C5  'C'
#define BC_A20I2  'I'
#define BC_AS20P2 'A'
#define BC_TICK   'T'
#define BC_IORX   'F'
#define BC_IORXTX 'X'
#define BC_IOTX   'G'

// schede sul bus
#define BUS_BOARD_IDX__S0   0
#define BUS_BOARD_IDX__S1   1
#define BUS_BOARD_IDX__S2   2
#define BUS_BOARD_IDX__S3   3
#define BUS_BOARD_IDX__S4   4
#define BUS_BOARD_IDX__S5   5
#define BUS_BOARD_IDX__S6   6
#define BUS_BOARD_IDX__S7   7
#define BUS_BOARD_IDX__TI   8
#define BUS_BOARDS_NUMBER   9

// scheda EK26
#define EK26_IDX  255

// FPGA Version (EK26)
#define FPGA_VERS_LEN      8
#define FPGA_VERS_DEFAULT  "-----"

// FPGA Data (BUS)
#define FPGA_DATA_LEN       20 // 19+1
#define FPGA_DATA_DEFAULT   "----|----|----|----"
#define FPGA_DATA_NONE      "____|____|____|____"

// sub address
#define SUB_ADDRESS_0   0
#define SUB_ADDRESS_1   1

// dati EEPROM nella EK26
#define MAIN_BOARD_NAME_LEN  9  //  8 + 0x00
#define MAIN_EEP_HWINFO_LEN  17 // 16 + 0x00
#define MAIN_EEP_SERIAL_LEN  17 // 16 + 0x00
#define MAIN_EEP_UID_LEN     16 // 16 byte

// dati EEPROM nelle schede sul bus
#define BUS_BOARD_NAME_LEN  9   //  8 + 0x00
#define BUS_EEP_HWINFO_LEN  11  // 10 + 0x00
#define BUS_EEP_SERIAL_LEN  7   //  6 + 0x00
#define BUS_EEP_UID_LEN     6   //  6 byte

// maschere errori di comunicazione
#define COMM_ERR__NONE          0x00
#define COMM_ERR__UART_DEMUX    0x01
#define COMM_ERR__UART_SUBADDR  0x02
#define COMM_ERR__I2C           0x04

// caratteri errori di comunicazione
#define ERR_CHAR__NONE          '_'
#define ERR_CHAR__UART_DEMUX    'U'
#define ERR_CHAR__UART_SUBADDR  'U'
#define ERR_CHAR__I2C           'I'


// *** enumerazioni/strutture *************************************************

typedef struct
{	
  // FPGA/Driver
  char boardAddr;                       // '-' o '0' a '3'
  char boardCode;                       // 'E'
  char boardName[MAIN_BOARD_NAME_LEN];  // "EK26    " stringa, 0x20 padded  
  //
  uint8_t fpgaSysType;                  // tipo di sistema (0:NP, 1:POL)
  uint8_t fpgaChanNb;                   // numero di canali gestiti
  char    fpgaVers[FPGA_VERS_LEN];
  
  // eeprom
  char eepHwInfo1[MAIN_EEP_HWINFO_LEN]; // stringa
  char eepSerial1[MAIN_EEP_SERIAL_LEN]; // stringa
  char eepHwInfo2[MAIN_EEP_HWINFO_LEN]; // stringa
  char eepSerial2[MAIN_EEP_SERIAL_LEN]; // stringa
  uint8_t eepUID[MAIN_EEP_UID_LEN];     // byte

  // comunicazione
  uint8_t commRes;  // esito comunicazione UART e I2C

} MainBoardInfo_TypeDef;

typedef struct
{	
  // micro (comando CAT HI)
  char micBoardAddr;                     // '-' o '0' a '8'
  char micBoardCode;                     // '-', 'P', 'T', 'C' o 'I'
  char micBoardName[BUS_BOARD_NAME_LEN]; // stringa (!!! 0x20 padded !!!)

  // micro (comando CAT VS)
  uint8_t micFwVers[2];   // 0-255 e 0-255

  // // FPGA
  // char fpgaVers0[FPGA_VERSION_LEN];
  // char fpgaVers1[FPGA_VERSION_LEN];

  // FPGA Data
  char fpgaData0[FPGA_DATA_LEN];
  char fpgaData1[FPGA_DATA_LEN];

  // eeprom
  char eepHwInfo1[BUS_EEP_HWINFO_LEN];  // stringa
  char eepSerial1[BUS_EEP_SERIAL_LEN];  // stringa
  char eepHwInfo2[BUS_EEP_HWINFO_LEN];  // stringa
  char eepSerial2[BUS_EEP_SERIAL_LEN];  // stringa
  uint8_t eepUID[BUS_EEP_UID_LEN];      // byte

  // comunicazione
  uint8_t commRes;  // esito comunicazione UART e I2C

} BusBoardInfo_TypeDef;


typedef struct
{	
  uint8_t               systemType;                       // polarizzate o non polarizzate
  MainBoardInfo_TypeDef mainBoardInfo;                    // EK26
  BusBoardInfo_TypeDef  busBoardsInfo[BUS_BOARDS_NUMBER]; // schede sul bus

} SystemInfo_TypeDef;


// *** variabili *************************************************

#ifdef DECLARE_VARS
  #define EXTERN
#else
  #define EXTERN extern
#endif

EXTERN SystemInfo_TypeDef systemInfo;


// *** prototipi *************************************************

// Start/Discovery Functions
int  PeriphSYS_Start(void);
void PeriphSYS_Stop(void);
int  PeriphSYS_Discovery(void);

// Print Stuff Functions
void PeriphSYS_GetMiscInfoForPrinting(uint8_t *out_str, uint8_t comm_res, uint8_t *in_str);
int  PeriphSYS_PrintSystemInfo(void);
void PeriphSYS_GetSystemType(char *sysTypeStr);

// Communication Functions
int PeriphSYS_Uart_SendCommand(uint8_t board_addr, uint8_t sub_addr, uint8_t *cmd, uint8_t cmd_len, bool wait_ans, uint8_t *ans_buff, uint8_t max_ans_len, uint8_t *byte_received);
int PeriphSYS_I2c_ReadEeprom(uint8_t board_addr, uint16_t page_idx, uint8_t *data, uint16_t data_len);
int PeriphSYS_I2c_WriteEepromPage(uint8_t board_addr, uint16_t page_idx, uint8_t *page_data);


#ifdef __cplusplus
}
#endif

#endif /* __PERIPH_SYS_H_ */
