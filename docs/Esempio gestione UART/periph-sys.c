#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include <fcntl.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <sys/ioctl.h>
#include <unistd.h>

#include "main.h"
#include "periph-sys.h"
#include "periph-uart.h"
#include "periph-i2c.h"
#if(DRIVER_TO_USE==TEST_DRIVER)
#include "testdriver.h"
#endif
#if(DRIVER_TO_USE==DAQ32_DRIVER)
#include "daq32driver.h"
#endif


// *** periph lib version *************************************************

char *periphLibVersion = "v4.0";

// * v4.0 - 19/01/2026:
//  - aggiunto supporto per entrambi i driver "testdriver.h" (CASES) e "daq32driver.h" (EPICA)
//  - differenziate le compilazioni per CASES e EPICA
//  - aggiunto supporto per schede IOHS
//
// * v3.1 - 30/09/2025:
//  - funzione PeriphSYS_Discovery, viene decodificato in pseudo-ASCII anche il campo versione FPGA delle schede
//
// * v3.0 - 25/07/2025:
//  - aggiunto gestione scheda AS20P2 del progetto EPICA
//
// * v2.1 - 26/06/2025:
//  - corretto la visualizzazione della legenda in PeriphSYS_PrintSystemInfo
//  - corretto gestione misc_info
//
// * v2.0 - 24/06/2025:
//  - aggiunto PeriphSYS_Stop che chiama PeriphUART_Close che chiama unconfigure_uart
//  - utilizzo della libuart con la funzione unconfigure_uart
//
// * v1.5 - 19/06/2025:
//  - cambiata PrintSystemInfo per allineare la visualizzazione dei dati dell'FPGA
//
// * v1.4 - 18/06/2025:
//  - modificato Discovery e PrintSystemInfo per visualizzare (in HEX) tutte le informazioni
//    delle FPGA che arrivano dalla risposta al comando A
//  - cambiata PrintSystemInfo per avere una visualizzazione più chiara
//
// * v1.3 - 17/06/2025:
//  - aggiunto chiusura driver dopo la lettura della versione dell'FPGA durante il discovery
//  - aggiunto la lettura dall'FPGA (e la stampa) del numero di canali gestiti
//  - aggiunto la lettura dall'FPGA (e la stampa) del tipo di sistema (POL, NP)
//
// * v1.2 - 13/06/2025:
//  - velocizzata la chiusura della ricezione UART modificando il numero di byte che ci si aspetta
//    di ricevere, da 50 a 28 per il micro e 17 per l'FPGA (prima era 8+1 ma è cambiata a 16+1)
//  - utilizzato il comando 'A' dappertutto per chiedere la versione alle FPGA
//
// * v1.1 - 10/06/2025:
//  - lettura versioni FPGA: messo comando M per TICK, comando A per le altre
//  - aggiunto prima gestione del driver (lettura versione FPGA e indirizzo EK26)
//  - rivista visualizzazione discovery
//
// * v1.0 - 05/06/2025:
//  - aggiunto una versione ai file "periph-xxxx.c/h"
//  - aggiunto scrittura pagina EEPROM
//  - modificato la lettura in EEPROM per poter leggere fino a I2C_BUFF_SIZE__READ (256) byte 
//  - modificata PeriphSYS_Discovery per via delle modifiche di lettura in EEPROM
//  - aggiunto la lettura delle versioni delle FPGA
//
// * v0.x - 03/06/2025:
//  - aggiunto gestione UART, invio e ricezione
//  - aggiunto lettura pagina EEPROM
//  - aggiunto funzione di discovery delle schede


// *** variabili *************************************************

bool driverOpened = false;    // stato apertura driver
bool uartConfigured = false;  // stato configurazione uart
char *periphSysPrefix = PRINT_OUTPUT__PERIPH_SYS_PREFIX;


// *** FUNCTION - Start & Discovery *************************************************

// inizializza e avvia la gestione delle schede
// return:
//  - PERIPH_RES__OK
//  - PERIPH_RES__START_ERROR
int PeriphSYS_Start(void)
{
    int ret = PERIPH_RES__OK;

    #ifdef PRINT_OUTPUT__PERIPH_SYS
    sprintf(outStr, "PeriphLib version: %s\n", periphLibVersion);
    Sys_PrintOutput(PT_YES, INF_EXT, periphSysPrefix, outStr);
    #endif

    // apre la UART
    ret = PeriphUART_Open();
    if(ret == UART_RES__OK)
    {
        uartConfigured = true;
    }
    else
    {
        ret = PERIPH_RES__START_ERROR;
        uartConfigured = false;

        #ifdef PRINT_OUTPUT__PERIPH_SYS
        sprintf(outStr, "UART configuration error !!!\n");
        Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
        #endif
    }

    // NB: nessuna operazione per l'I2C, si fa un Start/Stop ad ogni comunicazione

    return ret;
}


// deinizializza la gestione delle schede
void PeriphSYS_Stop(void)
{
    // chiude la UART
    PeriphUART_Close();

    // NB: nessuna operazione per l'I2C, si fa un Start/Stop ad ogni comunicazione
}


// effettua il discovery delle schede recuperando diverse informazioni tramite UART e I2C
// return:
//  - PERIPH_RES__OK
//  - PERIPH_RES__UART_CONFIG_ERROR
int PeriphSYS_Discovery(void)
{
    int ret = PERIPH_RES__OK;

    #ifdef PRINT_OUTPUT__PERIPH_SYS
    sprintf(outStr, "Discovery started...\n");
    Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
    #endif

    if(!uartConfigured)
    {
        #ifdef PRINT_OUTPUT__PERIPH_SYS
        sprintf(outStr, "UART not configured !!!\n");
        Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
        #endif

        return PERIPH_RES__UART_CONFIG_ERROR;
    }


    // --- reset della struttura di informazione ---
    //
    // systemType
    systemInfo.systemType = SYS_TYP__UNKNOWN;
    //
    // mainBoardInfo
    memset(&systemInfo.mainBoardInfo, 0, sizeof(MainBoardInfo_TypeDef));
    //
    systemInfo.mainBoardInfo.boardAddr = BA_NONE;
    //
    systemInfo.mainBoardInfo.boardCode = BC_EK26;
    //
    memset(systemInfo.mainBoardInfo.boardName, 0, MAIN_BOARD_NAME_LEN);
    sprintf(systemInfo.mainBoardInfo.boardName, "%s", "EK26    ");    
    //
    systemInfo.mainBoardInfo.fpgaSysType = 0xFF;
    systemInfo.mainBoardInfo.fpgaChanNb  = 0;
    //
    sprintf(systemInfo.mainBoardInfo.fpgaVers, "%s", FPGA_VERS_DEFAULT);
    //
    // busBoardsInfo
    for(int j=0; j<BUS_BOARDS_NUMBER; j++)
    {
        memset(&systemInfo.busBoardsInfo[j], 0, sizeof(BusBoardInfo_TypeDef));
        //
        systemInfo.busBoardsInfo[j].micBoardAddr = BA_NONE;
        //
        systemInfo.busBoardsInfo[j].micBoardCode = BC_NONE;
        //
        sprintf(systemInfo.busBoardsInfo[j].micBoardName, "        ");
        //
        sprintf(systemInfo.busBoardsInfo[j].fpgaData0, "%s", FPGA_DATA_DEFAULT);
        sprintf(systemInfo.busBoardsInfo[j].fpgaData1, "%s", FPGA_DATA_DEFAULT);
    }


    // --- recupero info per la scheda EK26 ---    

    // recupero versione FPGA
    int driver_fd = open(OPEN_STRING, O_RDWR | O_SYNC);
    if (driver_fd < 0)   
    {
        driverOpened = false;
        #ifdef PRINT_OUTPUT__PERIPH_SYS
        sprintf(outStr, "DRV open error (%d) !!!\n", driver_fd);
        Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
        #endif
    }
    else
    {
        driverOpened = true;
        #ifdef PRINT_OUTPUT__PERIPH_SYS
        sprintf(outStr, "DRV opened (%d)\n", driver_fd);
        Sys_PrintOutput(PT_YES, INF_EXT, periphSysPrefix, outStr);
        #endif
    }
    // 
    if(driverOpened)
    {
		    uint32_t reg = 0;
        #if(DRIVER_TO_USE==TEST_DRIVER)
		    int ret = ioctl(driver_fd, TESTDRIVER_GET_FPGA_VER, &reg);
        #endif
        #if(DRIVER_TO_USE==DAQ32_DRIVER)
        int ret = ioctl(driver_fd, DAQ32DRIVER_GET_FPGA_VER, &reg);
        #endif
		    if (ret < 0) 
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "DRV GET_FPGA_VER error (%d) !!!\n", ret);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif
        }
        else
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "DRV GET_FPGA_VER: 0x%08X (addr:%d, vers:%X)\n", reg, (reg&0x00300000)>>20, reg&0x000FFFFF);
            Sys_PrintOutput(PT_NO, INF_EXT, periphSysPrefix, outStr);
            #endif

            systemInfo.mainBoardInfo.boardAddr   = ((reg&0x00300000)>>20) | 0x30;
            //
            systemInfo.mainBoardInfo.fpgaSysType = ((reg&0x80000000)>>31);
            systemInfo.mainBoardInfo.fpgaChanNb  = ((reg&0x7F000000)>>24);
            sprintf(systemInfo.mainBoardInfo.fpgaVers, "%05X", reg&0x000FFFFF);
        }

        close(driver_fd);
    }

    uint8_t i2cBuffer[I2C_BUFF_SIZE__READ] = {};

    //#define SKIP_EK26
    #ifdef SKIP_EK26
    systemInfo.mainBoardInfo.commRes |= COMM_ERR__I2C;
    #else
  
    // lettura prima e seconda pagina
    memset(i2cBuffer, 0, I2C_BUFF_SIZE__READ);
    ret = PeriphSYS_I2c_ReadEeprom(EK26_IDX, 0, i2cBuffer, 64); // 2 pagine 
    if(ret != PERIPH_RES__OK)
    {
        systemInfo.mainBoardInfo.commRes |= COMM_ERR__I2C;
    }
    else
    {
        // memcpy(systemInfo.mainBoardInfo.eepHwInfo1, &i2cBuffer[0], MAIN_EEP_HWINFO_LEN-1);
        for(int j=0; j<(MAIN_EEP_HWINFO_LEN-1); j++)
        {
            uint8_t tmp = i2cBuffer[j];
            if((tmp<0x20) || (tmp>0x7E))
              systemInfo.mainBoardInfo.eepHwInfo1[j] = 0; // stronca la stringa in caso di carattere non valido
            else
              systemInfo.mainBoardInfo.eepHwInfo1[j] = tmp;
        }
        
        // memcpy(systemInfo.mainBoardInfo.eepSerial1, &i2cBuffer[16], MAIN_EEP_SERIAL_LEN-1);
        for(int j=0; j<(MAIN_EEP_HWINFO_LEN-1); j++)
        {
            uint8_t tmp = i2cBuffer[16+j];
            if((tmp<0x20) || (tmp>0x7E))
              systemInfo.mainBoardInfo.eepSerial1[j] = 0; // stronca la stringa in caso di carattere non valido
            else
              systemInfo.mainBoardInfo.eepSerial1[j] = tmp;
        }

        // memcpy(systemInfo.mainBoardInfo.eepHwInfo2, &i2cBuffer[32], MAIN_EEP_HWINFO_LEN-1);
        for(int j=0; j<(MAIN_EEP_HWINFO_LEN-1); j++)
        {
            uint8_t tmp = i2cBuffer[32+j];
            if((tmp<0x20) || (tmp>0x7E))
              systemInfo.mainBoardInfo.eepHwInfo2[j] = 0; // stronca la stringa in caso di carattere non valido
            else
              systemInfo.mainBoardInfo.eepHwInfo2[j] = tmp;
        }

        // memcpy(systemInfo.mainBoardInfo.eepSerial2, &i2cBuffer[48], MAIN_EEP_SERIAL_LEN-1);
        for(int j=0; j<(MAIN_EEP_SERIAL_LEN-1); j++)
        {
            uint8_t tmp = i2cBuffer[48+j];
            if((tmp<0x20) || (tmp>0x7E))
              systemInfo.mainBoardInfo.eepSerial2[j] = 0; // stronca la stringa in caso di carattere non valido
            else
              systemInfo.mainBoardInfo.eepSerial2[j] = tmp;
        }        
    }


    // lettura identification page
    memset(i2cBuffer, 0, I2C_BUFF_SIZE__READ);
    ret = PeriphSYS_I2c_ReadEeprom(EK26_IDX, 256, i2cBuffer, 32); // 1 pagina
    if(ret != PERIPH_RES__OK)
    {
        systemInfo.mainBoardInfo.commRes |= COMM_ERR__I2C;
    }
    else
    {
        // NB: non si usa la m24c64-u ma la m24c64-dr che non ha un UID, e visto i dati che si leggono (32 byte):
        //  0x20 0xe0 0x0d 	0x72 0xc3 0xff 0x47 0x32 0x30 0x15 0x17 0x44 0x30 0x33 0x19 0x41 0x41 0x38 0xff 	0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff
        //  0x20 0xe0 0x0d 	0x72 0xc3 0xff 0x47 0x32 0x30 0x15 0x17 0x44 0x30 0x33 0x18 0x91 0x41 0x38 0xff 	0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff
        //  0x20 0xe0 0x0d 	0x72 0xc3 0xff 0x47 0x32 0x30 0x15 0x17 0x44 0x30 0x33 0x20 0x21 0x40 0x38 0xff 	0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff
        //  0x20 0xe0 0x0d 	0x72 0xc3 0xff 0x47 0x32 0x30 0x15 0x17 0x44 0x30 0x33 0x19 0x71 0x37 0x38 0xff 	0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff 0xff
        // si decide di prendere i 16 byte più univoci (a ragione di logica e in previsione di poter usare una m24c64-u)
        // cmq, vd. i datasheet delle m24c64 per i dettagli e maggiori spiegazioni
        memcpy(systemInfo.mainBoardInfo.eepUID, &i2cBuffer[3], MAIN_EEP_UID_LEN);
    }
    #endif


    // --- recupero info per le altre schede ---

    #define CMD_LEN  7
    uint8_t cmd[CMD_LEN];
    memcpy(cmd, "HI;VSM;", CMD_LEN);

    #define ANS_LEN  50
    uint8_t ans[ANS_LEN];
    uint8_t ans_byte_nb = 0;
    memset(ans, 0, ANS_LEN);

    //#define MIC_MAX_ANS_LEN   ANS_LEN
    //#define FPGA_MAX_ANS_LEN  ANS_LEN    
    #define MIC_MAX_ANS_LEN   28
    #define FPGA_MAX_ANS_LEN  17
    //
    #define MIC_ANS_LEN   28
    #define FPGA_ANS_LEN  17

    // giro sulle schede del bus
    for(int i=0; i<BUS_BOARDS_NUMBER; i++)
    // TEST for(int i=0; i<0; i++)
    // TEST for(int i=5; i<6; i++)
    {
        // --- recupero dati da UART ---

        // invio comandi CAT
        int ret = PeriphSYS_Uart_SendCommand(i, 9, cmd, CMD_LEN, true, ans, MIC_MAX_ANS_LEN, &ans_byte_nb);

        // TEST
        //usleep(50000);

        // NB:     
        //  caso PERIPH_RES__UART_CONFIG_ERROR  : gestito sopra
        //  caso PERIPH_RES__UART_SENDING_ERROR : da trattare come Error Uart
        //  caso PERIPH_RES__NO_ANSWER_RECEIVED : da trattare come Error Uart (probabile scheda non presente)
        //  altri casi: non sono possibili qui
        if(ret == PERIPH_RES__UART_SENDING_ERROR)
        {
            systemInfo.busBoardsInfo[i].commRes |= COMM_ERR__UART_DEMUX;
            //systemInfo.busBoardsInfo[i].commRes |= COMM_ERR__UART_SUBADRD;
            goto Label_I2C;
        }
        if(ret == PERIPH_RES__NO_ANSWER_RECEIVED)
        {
            systemInfo.busBoardsInfo[i].commRes |= COMM_ERR__UART_DEMUX;
            //systemInfo.busBoardsInfo[i].commRes |= COMM_ERR__UART_SUBADRD;
            goto Label_I2C;
        }

        // NB:
        //  si gestisce solo le risposte ai comandi inviati sopra, cioè: "HI;VSM;"
        //  le risposte devono quindi essere nel formato (es.): "HI7|P|PBI5    ;.VSM000.004;."
        //                                                      "0123456789012345678901234567"
        if(ans_byte_nb != MIC_ANS_LEN)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "UART (MIC) wrong number of byte received (%d) !!!\n", ans_byte_nb);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif

            systemInfo.busBoardsInfo[i].commRes |= COMM_ERR__UART_DEMUX;
            //systemInfo.busBoardsInfo[i].commRes |= COMM_ERR__UART_SUBADRD;
            goto Label_I2C;
        }
        if( (ans[0] != 'H')  || (ans[1] != 'I')  || (ans[3] != '|')  || (ans[5] != '|')  || (ans[14] != ';') || (ans[15] != 0x0D) ||
            (ans[16] != 'V') || (ans[17] != 'S') || (ans[18] != 'M') || (ans[22] != '.') || (ans[26] != ';') || (ans[27] != 0x0D) )
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "UART (MIC) wrong data received !!!\n");
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif

            systemInfo.busBoardsInfo[i].commRes |= COMM_ERR__UART_DEMUX; 
            //systemInfo.busBoardsInfo[i].commRes |= COMM_ERR__UART_SUBADRD;
            goto Label_I2C;
        }
        
        // recupero info scheda
        systemInfo.busBoardsInfo[i].micBoardAddr = ans[2];
        systemInfo.busBoardsInfo[i].micBoardCode = ans[4];
        memcpy(systemInfo.busBoardsInfo[i].micBoardName, &ans[6], BUS_BOARD_NAME_LEN-1);

        // recupero versione fw
        char fwVersHigh[4];
        char fwVersLow[4];        
        memset(fwVersHigh, 0, 4);
        memset(fwVersLow, 0, 4);
        memcpy(fwVersHigh, &ans[19], 3);
        memcpy(fwVersLow, &ans[23], 3);
        systemInfo.busBoardsInfo[i].micFwVers[0] = atoi(fwVersHigh);
        systemInfo.busBoardsInfo[i].micFwVers[1] = atoi(fwVersLow);
      

Label_FPGA:
        // --- recupero versioni FPGA ---

        #define DECODE_FPGA_DATA
        //#define TEST_DECODE_FPGA_VERS // TEST/DEBUG

        #define VERS_REQ_LEN  5
        uint8_t vers_req_A[VERS_REQ_LEN];
        //uint8_t vers_req_M[VERS_REQ_LEN];        
        memcpy(vers_req_A, "A0000", VERS_REQ_LEN);
        //memcpy(vers_req_M, "F0000", VERS_REQ_LEN);

        // 1. se la scheda è una A20C5 o A20I2 o AS20P2, si manda il comando all'indirizzo 0
        if( (systemInfo.busBoardsInfo[i].micBoardCode == BC_A20C5) ||
            (systemInfo.busBoardsInfo[i].micBoardCode == BC_A20I2) ||
            (systemInfo.busBoardsInfo[i].micBoardCode == BC_AS20P2))
        {
            // invio comandi CAT
            ans_byte_nb = 0;
            ret = PeriphSYS_Uart_SendCommand(i, SUB_ADDRESS_0, vers_req_A, VERS_REQ_LEN, true, ans, FPGA_MAX_ANS_LEN, &ans_byte_nb);
            // NB:     
            //  caso PERIPH_RES__UART_CONFIG_ERROR  : gestito sopra
            //  caso PERIPH_RES__UART_SENDING_ERROR : da trattare come Error Uart
            //  caso PERIPH_RES__NO_ANSWER_RECEIVED : da trattare come Error Uart 
            //  altri casi: non sono possibili qui
            if(ret == PERIPH_RES__UART_SENDING_ERROR)
            {
                systemInfo.busBoardsInfo[i].commRes |= COMM_ERR__UART_SUBADDR;
                goto Label_I2C;
            }
            if(ret == PERIPH_RES__NO_ANSWER_RECEIVED)
            {
                systemInfo.busBoardsInfo[i].commRes |= COMM_ERR__UART_SUBADDR;
                goto Label_I2C;
            }

            // if(ans_byte_nb == FPGA_OLD_ANS_LEN)
            // {
            //     // NB: risposta tipica a "A0000":
            //     //  "xxx00000K"
            //     //  con xxx uguale alla versione del bitstream
            //     memcpy(systemInfo.busBoardsInfo[i].fpgaVers0, &ans[0], 3);
            // }
            // else 
            if(ans_byte_nb == FPGA_ANS_LEN)
            {
                // NB: risposta di "A0000":
                //   01234567890123456
                //  "8080vvvv000000??." con vvvv uguale alla versione del bitstream
                // si trasforma in (x dove i byte sono decodificati):
                //   0123456789012345678
                //  "8080|vvvv|0000|00FF"
                //  "   x|xxxx|xxxx|xxxx"
                
                //memcpy(systemInfo.busBoardsInfo[i].fpgaData0, &ans[0], 16);

                #ifdef DECODE_FPGA_DATA
                // decodifica Spare (stato relè per la PBI5)
                uint8_t tmpSpare[2];
                Sys_HexToAscii(ans[3] & 0x0F, tmpSpare);
                ans[3] = tmpSpare[1];
                
                // decodifica versione FPGA (2 byte) (modifica v3.1)
                #ifdef TEST_DECODE_FPGA_VERS
                ans[4] = ':';
                ans[5] = ';';
                ans[6] = '<';
                ans[7] = '=';
                #endif
                uint8_t tmpVal[2];
                uint8_t tmpVers[4];
                for(int i=0; i<4; i++)
                { 
                    Sys_HexToAscii(ans[4+i] & 0x0F, tmpVal);
                    tmpVers[i] = tmpVal[1];
                }
                memcpy(&ans[4], &tmpVers[0], 4);                

                // decodifica valore registro (32 bit)
                //uint8_t tmpVal[2];
                uint8_t tmpReg[8];
                for(int i=0; i<8; i++)
                { 
                    Sys_HexToAscii(ans[8+i] & 0x0F, tmpVal);
                    tmpReg[i] = tmpVal[1];
                }
                memcpy(&ans[8], &tmpReg[0], 8);
                #endif

                memcpy(&systemInfo.busBoardsInfo[i].fpgaData0[0],  &ans[0],  4);
                systemInfo.busBoardsInfo[i].fpgaData0[4]  = '|';
                memcpy(&systemInfo.busBoardsInfo[i].fpgaData0[5],  &ans[4],  4);
                systemInfo.busBoardsInfo[i].fpgaData0[9]  = '|';
                memcpy(&systemInfo.busBoardsInfo[i].fpgaData0[10], &ans[8],  4);
                systemInfo.busBoardsInfo[i].fpgaData0[14] = '|';
                memcpy(&systemInfo.busBoardsInfo[i].fpgaData0[15], &ans[12], 4);
                systemInfo.busBoardsInfo[i].fpgaData0[19] = 0;
            }
            else
            {
                #ifdef PRINT_OUTPUT__PERIPH_SYS
                sprintf(outStr, "UART (FPGA 0) wrong number of byte received (%d) !!!\n", ans_byte_nb);
                Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
                #endif

                systemInfo.busBoardsInfo[i].commRes |= COMM_ERR__UART_SUBADDR;
                goto Label_I2C;
            }
        }


        // 2. se la scheda è una A20C5 o A20I2, AS20P2, PBI5 e TICK si manda il comando all'indirizzo 1
        if( (systemInfo.busBoardsInfo[i].micBoardCode == BC_A20C5)  ||
            (systemInfo.busBoardsInfo[i].micBoardCode == BC_A20I2)  ||
            (systemInfo.busBoardsInfo[i].micBoardCode == BC_AS20P2) ||
            (systemInfo.busBoardsInfo[i].micBoardCode == BC_PBI5)   ||
            (systemInfo.busBoardsInfo[i].micBoardCode == BC_TICK)   )
        {
            // invio comandi CAT
            ans_byte_nb = 0;
            //if(systemInfo.busBoardsInfo[i].micBoardCode == BC_TICK)
                //ret = PeriphSYS_Uart_SendCommand(i, SUB_ADDRESS_1, vers_req_M, VERS_REQ_LEN, true, ans, FPGA_MAX_ANS_LEN, &ans_byte_nb);
            //else
                ret = PeriphSYS_Uart_SendCommand(i, SUB_ADDRESS_1, vers_req_A, VERS_REQ_LEN, true, ans, FPGA_MAX_ANS_LEN, &ans_byte_nb);
            // NB:
            //  caso PERIPH_RES__UART_CONFIG_ERROR  : gestito sopra
            //  caso PERIPH_RES__UART_SENDING_ERROR : da trattare come Error Uart
            //  caso PERIPH_RES__NO_ANSWER_RECEIVED : da trattare come Error Uart 
            //  altri casi: non sono possibili qui
            if(ret == PERIPH_RES__UART_SENDING_ERROR)
            {
                systemInfo.busBoardsInfo[i].commRes |= COMM_ERR__UART_SUBADDR;
                goto Label_I2C;
            }
            if(ret == PERIPH_RES__NO_ANSWER_RECEIVED)
            {
                systemInfo.busBoardsInfo[i].commRes |= COMM_ERR__UART_SUBADDR;
                goto Label_I2C;
            }

            // if(ans_byte_nb == FPGA_OLD_ANS_LEN)
            // {
            //     // NB: risposta tipica a "A0000":
            //     //  "xxx00000K"
            //     //  con xxx uguale alla versione del bitstream
            //     memcpy(systemInfo.busBoardsInfo[i].fpgaVers1, &ans[0], 3);
            // }
            // else 
            if(ans_byte_nb == FPGA_ANS_LEN)
            {
                // NB: risposta di "A0000":
                //  "8080vvvv000000??." con vvvv uguale alla versione del bitstream
                // si trasforma in (x dove i byte sono decodificati):
                //   0123456789012345678
                //  "8080|vvvv|0000|00FF"
                //  "   x|xxxx|xxxx|xxxx"
                
                //memcpy(systemInfo.busBoardsInfo[i].fpgaData1, &ans[0], 16);

                #ifdef DECODE_FPGA_DATA
                // decodifica Spare (stato relè per la PBI5)
                uint8_t tmpSpare[2];
                Sys_HexToAscii(ans[3] & 0x0F, tmpSpare);
                ans[3] = tmpSpare[1];  

                // decodifica versione FPGA (2 byte) (modifica v3.1)
                #ifdef TEST_DECODE_FPGA_VERS
                ans[4] = '<';
                ans[5] = '=';
                ans[6] = '>';
                ans[7] = '?';
                #endif            
                uint8_t tmpVal[2];
                uint8_t tmpVers[4];
                for(int i=0; i<4; i++)
                { 
                    Sys_HexToAscii(ans[4+i] & 0x0F, tmpVal);
                    tmpVers[i] = tmpVal[1];
                }
                memcpy(&ans[4], &tmpVers[0], 4);  

                // decodifica valore registro (32 bit)
                //uint8_t tmpVal[2];
                uint8_t tmpReg[8];
                for(int i=0; i<8; i++)
                { 
                    Sys_HexToAscii(ans[8+i] & 0x0F, tmpVal);
                    tmpReg[i] = tmpVal[1];
                }
                memcpy(&ans[8], &tmpReg[0], 8);            
                #endif 

                memcpy(&systemInfo.busBoardsInfo[i].fpgaData1[0],  &ans[0],  4);
                systemInfo.busBoardsInfo[i].fpgaData1[4]  = '|';
                memcpy(&systemInfo.busBoardsInfo[i].fpgaData1[5],  &ans[4],  4);
                systemInfo.busBoardsInfo[i].fpgaData1[9]  = '|';
                memcpy(&systemInfo.busBoardsInfo[i].fpgaData1[10], &ans[8],  4);
                systemInfo.busBoardsInfo[i].fpgaData1[14] = '|';
                memcpy(&systemInfo.busBoardsInfo[i].fpgaData1[15], &ans[12], 4);
                systemInfo.busBoardsInfo[i].fpgaData1[19] = 0;  
            }
            else
            {
                #ifdef PRINT_OUTPUT__PERIPH_SYS
                sprintf(outStr, "UART (FPGA 1) wrong number of byte received (%d) !!!\n", ans_byte_nb);
                Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
                #endif
                systemInfo.busBoardsInfo[i].commRes |= COMM_ERR__UART_SUBADDR;
                goto Label_I2C;
            }        
        }


Label_I2C:
        // --- recupero dati da I2C ---

        // lettura eeprom
        memset(i2cBuffer, 0, I2C_BUFF_SIZE__READ);
        ret = PeriphSYS_I2c_ReadEeprom(i, 0, i2cBuffer, I2C_BUFF_SIZE__READ);
        if(ret != PERIPH_RES__OK)
        {
            systemInfo.busBoardsInfo[i].commRes |= COMM_ERR__I2C;
        }
        else
        {
            //memcpy(systemInfo.busBoardsInfo[i].eepHwInfo1, &i2cBuffer[0], BUS_EEP_HWINFO_LEN-1);
            for(int j=0; j<(BUS_EEP_HWINFO_LEN-1); j++)
            {
                uint8_t tmp = i2cBuffer[j];
                if((tmp<0x20) || (tmp>0x7E))
                  systemInfo.busBoardsInfo[i].eepHwInfo1[j] = 0; // stronca la stringa in caso di carattere non valido
                else
                  systemInfo.busBoardsInfo[i].eepHwInfo1[j] = tmp;
            }

            //memcpy(systemInfo.busBoardsInfo[i].eepSerial1, &i2cBuffer[10], BUS_EEP_SERIAL_LEN-1);
            for(int j=0; j<(BUS_EEP_SERIAL_LEN-1); j++)
            {
                uint8_t tmp = i2cBuffer[10+j];
                if((tmp<0x20) || (tmp>0x7E))
                  systemInfo.busBoardsInfo[i].eepSerial1[j] = 0; // stronca la stringa in caso di carattere non valido
                else
                  systemInfo.busBoardsInfo[i].eepSerial1[j] = tmp;
            }            


            // recupero dati seconda pagina solo per la TICK e la IOHS
            //if(i == BUS_BOARD_IDX__TI)
            if( (systemInfo.busBoardsInfo[i].micBoardCode == BC_TICK)   ||
                (systemInfo.busBoardsInfo[i].micBoardCode == BC_IORX)   ||
                (systemInfo.busBoardsInfo[i].micBoardCode == BC_IORXTX) ||
                (systemInfo.busBoardsInfo[i].micBoardCode == BC_IOTX)   )
            {
                //memcpy(systemInfo.busBoardsInfo[i].eepHwInfo2, &i2cBuffer[16], BUS_EEP_HWINFO_LEN-1);
                for(int j=0; j<(BUS_EEP_HWINFO_LEN-1); j++)
                {
                    uint8_t tmp = i2cBuffer[16+j];
                    if((tmp<0x20) || (tmp>0x7E))
                      systemInfo.busBoardsInfo[i].eepHwInfo2[j] = 0; // stronca la stringa in caso di carattere non valido
                    else
                      systemInfo.busBoardsInfo[i].eepHwInfo2[j] = tmp;
                }

                //memcpy(systemInfo.busBoardsInfo[i].eepSerial2, &i2cBuffer[26], BUS_EEP_SERIAL_LEN-1);
                for(int j=0; j<(BUS_EEP_SERIAL_LEN-1); j++)
                {
                    uint8_t tmp = i2cBuffer[26+j];
                    if((tmp<0x20) || (tmp>0x7E))
                      systemInfo.busBoardsInfo[i].eepSerial2[j] = 0; // stronca la stringa in caso di carattere non valido
                    else
                      systemInfo.busBoardsInfo[i].eepSerial2[j] = tmp;
                }                
            }


            // lettura UID
            // NB: sulle 24AA025 l'UID è fatto di 6B che si trovano alla fine dell'ultima pagina
            memcpy(systemInfo.busBoardsInfo[i].eepUID, &i2cBuffer[I2C_BUFF_SIZE__READ-6], BUS_EEP_UID_LEN);            
        }
    }


    // // --- analisi lista per capire che cassetto è (AARRRGGGGHHHH !!!!!!!!) ---
    // // casi cassetti completi:
    // //        0 1 2 3 4 5 6 7 8
    // // PO   : P C P C P C     T
    // // NP-sx: I I I I I I I I T
    // // NP-dx: I I I I I I I I 
    // int PBI5_cnt = 0;
    // int A20C5_cnt = 0;
    // int A20I2_cnt = 0;
    // int TICK_cnt = 0;
    // int NONE_cnt = 0;
    // for(int i=0; i<BUS_BOARDS_NUMBER; i++)
    // {
    //     if(systemInfo.busBoardsInfo[i].micBoardCode == BC_PBI5)
    //         PBI5_cnt++;
    //     else if(systemInfo.busBoardsInfo[i].micBoardCode == BC_A20C5)
    //         A20C5_cnt++;
    //     else if(systemInfo.busBoardsInfo[i].micBoardCode == BC_A20I2)
    //         A20I2_cnt++;
    //     else if(systemInfo.busBoardsInfo[i].micBoardCode == BC_TICK)
    //         TICK_cnt++;
    //     else
    //         NONE_cnt++;
    // }
    // // casi completi
    // if((PBI5_cnt==3) && (A20C5_cnt==3) && (TICK_cnt==1) && (NONE_cnt==2))
    //     systemInfo.systemType = SYS_TYP__POL;
    // else if((A20I2_cnt==8) && (TICK_cnt==1))    
    //     systemInfo.systemType = SYS_TYP__NPL;        
    // else if((A20I2_cnt==8) && (NONE_cnt==1))
    //     systemInfo.systemType = SYS_TYP__NPR;
    // // casi non completi
    // else if((PBI5_cnt>0) || (A20C5_cnt>0))
    // {
    //     systemInfo.systemType = SYS_TYP__POL;
    //     systemInfo.systemType|= SYS_TYP__ERR;
    // }
    // else if((A20I2_cnt>0) && (TICK_cnt==1))
    // {
    //     systemInfo.systemType = SYS_TYP__NPL;
    //     systemInfo.systemType|= SYS_TYP__ERR;
    // }
    // else if((A20I2_cnt>0) && (TICK_cnt==0)) // qui servirebbe l'analisi dei pin A1:A0, anche se non univoca per tutti i cassetti    
    // {      
    //     systemInfo.systemType = SYS_TYP__NPR;
    //     systemInfo.systemType|= SYS_TYP__ERR;
    // }
    // else
    // {
    //     systemInfo.systemType = SYS_TYP__UNK;
    //     systemInfo.systemType|= SYS_TYP__ERR;
    // }


    // --- analisi lista per capire che cassetto è (AARRRGGGGHHHH !!!!!!!!) ---
    // casi cassetti completi:
    //        0 1 2 3 4 5 6 7 8   EK26_ADDR
    // PO   : P C P C P C     T   1
    // NP-sx: I I I I I I I I T   1
    // NP-dx: I I I I I I I I     2
    // EPICA: A A A A A A A A T   1
    int PBI5_cnt = 0;
    int A20C5_cnt = 0;
    int A20I2_cnt = 0;
    int AS20P2_cnt = 0;
    int TICK_cnt = 0;
    int NONE_cnt = 0;
    for(int i=0; i<BUS_BOARDS_NUMBER; i++)
    {
        if(systemInfo.busBoardsInfo[i].micBoardCode == BC_PBI5)
            PBI5_cnt++;
        else if(systemInfo.busBoardsInfo[i].micBoardCode == BC_A20C5)
            A20C5_cnt++;
        else if(systemInfo.busBoardsInfo[i].micBoardCode == BC_A20I2)
            A20I2_cnt++;
        else if(systemInfo.busBoardsInfo[i].micBoardCode == BC_AS20P2)
            AS20P2_cnt++;
        else if(systemInfo.busBoardsInfo[i].micBoardCode == BC_TICK)
            TICK_cnt++;
        else
            NONE_cnt++;
    }

    // PO o NP-sx o EPICA
    if(systemInfo.mainBoardInfo.boardAddr == 1)
    {
        // caso completo
        if((PBI5_cnt==3) && (A20C5_cnt==3) && (TICK_cnt==1) && (NONE_cnt==2))
            systemInfo.systemType = SYS_TYP__CASES_POL;
        // caso completo
        else if((A20I2_cnt==8) && (TICK_cnt==1))    
            systemInfo.systemType = SYS_TYP__CASES_NPL;        
        // caso completo
        else if((AS20P2_cnt==8) && (TICK_cnt==1))    
            systemInfo.systemType = SYS_TYP__EPICA;
        else
        {
            // caso non completo
            if((PBI5_cnt>0) || (A20C5_cnt>0))
            {
                systemInfo.systemType = SYS_TYP__CASES_POL;

                if((PBI5_cnt!=3) || (A20C5_cnt!=3))
                    systemInfo.systemType|= SYS_TYP__ERR;                
            }
            // caso non completo
            else if(A20I2_cnt>0)
            {
                systemInfo.systemType = SYS_TYP__CASES_NPL;

                if(A20I2_cnt!=8)
                    systemInfo.systemType|= SYS_TYP__ERR;    
            }
            // caso non completo
            else if(AS20P2_cnt>0)
            {
                systemInfo.systemType = SYS_TYP__EPICA;

                if(AS20P2_cnt!=8)
                    systemInfo.systemType|= SYS_TYP__ERR;
            }            
            else
            {
                systemInfo.systemType = SYS_TYP__UNKNOWN;
                systemInfo.systemType|= SYS_TYP__ERR;
            }
                                        
            // se TICK mancante
            if(TICK_cnt!=1)
                systemInfo.systemType|= SYS_TYP__ERR;
        }
    }
    // NP-dx
    else if(systemInfo.mainBoardInfo.boardAddr == 2)
    {
        systemInfo.systemType = SYS_TYP__CASES_NPR;
        if(A20I2_cnt!=8)
            systemInfo.systemType|= SYS_TYP__ERR;
    }
    // analisi senza boardAddr
    else
    {
        // casi completi
        if((PBI5_cnt==3) && (A20C5_cnt==3) && (TICK_cnt==1) && (NONE_cnt==2))
            systemInfo.systemType = SYS_TYP__CASES_POL;
        else if((A20I2_cnt==8) && (TICK_cnt==1))    
            systemInfo.systemType = SYS_TYP__CASES_NPL;        
        else if((A20I2_cnt==8) && (NONE_cnt==1))
            systemInfo.systemType = SYS_TYP__CASES_NPR;          
        else if((AS20P2_cnt==8) && (TICK_cnt==1))
            systemInfo.systemType = SYS_TYP__EPICA;
        // casi non completi
        else if((PBI5_cnt>0) || (A20C5_cnt>0))
        {
            systemInfo.systemType = SYS_TYP__CASES_POL;
            systemInfo.systemType|= SYS_TYP__ERR;
        }
        else if((A20I2_cnt>0) && (TICK_cnt==1))
        {
            systemInfo.systemType = SYS_TYP__CASES_NPL;
            systemInfo.systemType|= SYS_TYP__ERR;
        }
        else if((A20I2_cnt>0) && (TICK_cnt==0)) // qui servirebbe l'analisi dei pin A1:A0, anche se non univoca per tutti i cassetti    
        {      
            systemInfo.systemType = SYS_TYP__CASES_NPR;
            systemInfo.systemType|= SYS_TYP__ERR;
        }
        else if((AS20P2_cnt>0) && (TICK_cnt==1))
        {
            systemInfo.systemType = SYS_TYP__EPICA;
            systemInfo.systemType|= SYS_TYP__ERR;
        }        
        else
        {
            systemInfo.systemType = SYS_TYP__UNKNOWN;
            systemInfo.systemType|= SYS_TYP__ERR;
        }
    }

    return ret;
}


// *** FUNCTION - Print Stuff *************************************************

// prepara l'informazione per la stampa
void PeriphSYS_GetMiscInfoForPrinting(uint8_t *out_str, uint8_t comm_res, uint8_t *in_str)
{
    if(comm_res & COMM_ERR__I2C)
    {
        sprintf(out_str, "%s", "");
    }
    else
    { 
        if(strlen(in_str) > 0)
            sprintf(out_str, "%s", in_str);
        else
            sprintf(out_str, "%s", "");
    }
}


// stampa tutte le informazioni disponibili sul sistema (sull'hardware)
int PeriphSYS_PrintSystemInfo(void)
{
    // TEST
    //systemInfo.systemType = SYS_TYP__POL | SYS_TYP__ERR;
    //systemInfo.systemType = SYS_TYP__NPL;


    #define SYS_TYP_LEN 60
    char sys_type[SYS_TYP_LEN] = {};    

    #define MISC_INFO_LEN 17
    char misc_info[4][MISC_INFO_LEN] = {};

    #define UID_LEN 33
    char uid[UID_LEN] = {};    

    // legenda
    Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, "Discovery:\n");
    #if(HW_TYPE==HW_CASES)
    Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, "* SYSTEM:     CASES POLARIZED | CASES NOT POLARIZED (left) | CASES NOT POLARIZED (right) | UNKNOWN\n");
    #endif
    #if(HW_TYPE==HW_EPICA)
    Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, "* SYSTEM:     EPICA | UNKNOWN\n");
    #endif    
    Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, "* EK26 BOARD: (BOARD:CODE,ADDR)      (ERR:COMM_ERR) (FPGA:VERS,SYS,CHAN) (UID) (EEP:HW_INFO & SERIAL)\n");
    Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, "* BUS BOARD:  (MICRO:CODE,ADDR,VERS) (ERR:COMM_ERR) (FPGA:DATA_0,DATA_1) (UID) (EEP:HW_INFO & SERIAL)\n");
    Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, "\n");

    // formattazione "systemType"
    memset(sys_type, 0, SYS_TYP_LEN);
    #if(HW_TYPE==HW_EPICA)
    if((systemInfo.systemType & SYS_TYP__MSK) == SYS_TYP__EPICA)
        sprintf(sys_type, "%s", "EPICA");    
    #endif
    #if(HW_TYPE==HW_CASES)
    if((systemInfo.systemType & SYS_TYP__MSK) == SYS_TYP__CASES_POL)
        sprintf(sys_type, "%s", "CASES POLARIZED");
    else if((systemInfo.systemType & SYS_TYP__MSK) == SYS_TYP__CASES_NPL)
        sprintf(sys_type, "%s", "CASES NOT POLARIZED (left)");
    else if((systemInfo.systemType & SYS_TYP__MSK) == SYS_TYP__CASES_NPR)
        sprintf(sys_type, "%s", "CASES NOT POLARIZED (right)");
    #endif
    else
        sprintf(sys_type, "%s", "UNKNOWN");
    if(systemInfo.systemType & SYS_TYP__ERR)
        strcat(sys_type, " - error found, probable missing board(s)");

    #ifdef PRINT_OUTPUT__PERIPH_SYS
    sprintf(outStr, "SYSTEM:       %s\n", sys_type);
    Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);


    // formattazione "misc_info" per EK26
    memset(misc_info, 0, MISC_INFO_LEN*4);
    PeriphSYS_GetMiscInfoForPrinting(&misc_info[0][0], systemInfo.mainBoardInfo.commRes, systemInfo.mainBoardInfo.eepHwInfo1);
    PeriphSYS_GetMiscInfoForPrinting(&misc_info[1][0], systemInfo.mainBoardInfo.commRes, systemInfo.mainBoardInfo.eepSerial1);
    PeriphSYS_GetMiscInfoForPrinting(&misc_info[2][0], systemInfo.mainBoardInfo.commRes, systemInfo.mainBoardInfo.eepHwInfo2);
    PeriphSYS_GetMiscInfoForPrinting(&misc_info[3][0], systemInfo.mainBoardInfo.commRes, systemInfo.mainBoardInfo.eepSerial2);

    // formattazione "uid" per EK26
    memset(uid, 0, UID_LEN);
    if(systemInfo.mainBoardInfo.commRes & COMM_ERR__I2C)
        sprintf(uid, "%s", "");
    else
        Sys_EncodeAscii_STR(systemInfo.mainBoardInfo.eepUID, MAIN_EEP_UID_LEN, uid);

    // scheda EK26
    sprintf(outStr, "EK: %s  (BRD:%c,%c) (ERR:%c) (F:%s,%s,%d) (UID:%s) (EEP:%s,%s,%s,%s)\n",
        systemInfo.mainBoardInfo.boardName,         
        systemInfo.mainBoardInfo.boardCode, systemInfo.mainBoardInfo.boardAddr,
        (systemInfo.mainBoardInfo.commRes&COMM_ERR__I2C) ? ERR_CHAR__I2C : ERR_CHAR__NONE,
        systemInfo.mainBoardInfo.fpgaVers, 
        (systemInfo.mainBoardInfo.fpgaSysType==0) ? "NP" : ((systemInfo.mainBoardInfo.fpgaSysType==1) ? "POL" : "UNK"), 
        systemInfo.mainBoardInfo.fpgaChanNb,
        uid,
        &misc_info[0][0], &misc_info[1][0], &misc_info[2][0], &misc_info[3][0]
      );
    Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);    

    // giro sulle schede del bus
    for(int i=0; i<BUS_BOARDS_NUMBER; i++)
    {
        // // TEST
        // systemInfo.busBoardsInfo[i].commRes = 0;
        // sprintf(systemInfo.busBoardsInfo[i].eepHwInfo1, "%s", "BOARD 1.0");
        // sprintf(systemInfo.busBoardsInfo[i].eepSerial1, "%s", "SN3456");

        // formattazione "misc_info" per le schede del bus
        memset(misc_info, 0, MISC_INFO_LEN*4);
        PeriphSYS_GetMiscInfoForPrinting(&misc_info[0][0], systemInfo.busBoardsInfo[i].commRes, systemInfo.busBoardsInfo[i].eepHwInfo1);
        PeriphSYS_GetMiscInfoForPrinting(&misc_info[1][0], systemInfo.busBoardsInfo[i].commRes, systemInfo.busBoardsInfo[i].eepSerial1);
        PeriphSYS_GetMiscInfoForPrinting(&misc_info[2][0], systemInfo.busBoardsInfo[i].commRes, systemInfo.busBoardsInfo[i].eepHwInfo2);
        PeriphSYS_GetMiscInfoForPrinting(&misc_info[3][0], systemInfo.busBoardsInfo[i].commRes, systemInfo.busBoardsInfo[i].eepSerial2);

        // formattazione "uid" per le schede del bus
        memset(uid, 0, UID_LEN);
        if(systemInfo.busBoardsInfo[i].commRes & COMM_ERR__I2C)
            sprintf(uid, "%s", "");
        else
            Sys_EncodeAscii_STR(systemInfo.busBoardsInfo[i].eepUID, BUS_EEP_UID_LEN, uid);

        // stampa
        if(i == BUS_BOARD_IDX__TI)
        {
            // TICK
            sprintf(outStr, "TI: %s  (MIC:%c,%c,v%d.%d) (ERR:%c%c%c) (F:%s,%s) (UID:%s) (EEP:%s,%s,%s,%s)\n",
                systemInfo.busBoardsInfo[i].micBoardName,                
                systemInfo.busBoardsInfo[i].micBoardCode, systemInfo.busBoardsInfo[i].micBoardAddr, systemInfo.busBoardsInfo[i].micFwVers[0], systemInfo.busBoardsInfo[i].micFwVers[1],
                (systemInfo.busBoardsInfo[i].commRes&COMM_ERR__UART_DEMUX) ?   ERR_CHAR__UART_DEMUX   : ERR_CHAR__NONE,
                (systemInfo.busBoardsInfo[i].commRes&COMM_ERR__UART_SUBADDR) ? ERR_CHAR__UART_SUBADDR : ERR_CHAR__NONE,
                (systemInfo.busBoardsInfo[i].commRes&COMM_ERR__I2C) ?          ERR_CHAR__I2C          : ERR_CHAR__NONE,
                FPGA_DATA_NONE, systemInfo.busBoardsInfo[i].fpgaData1,
                uid,
                &misc_info[0][0], &misc_info[1][0], &misc_info[2][0], &misc_info[3][0]
              );            
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);            
        }
        else
        {
            // PBI5
            if(systemInfo.busBoardsInfo[i].micBoardCode == BC_PBI5)
            {
                sprintf(outStr, "S%d: %s  (MIC:%c,%c,v%d.%d) (ERR:%c%c%c) (F:%s,%s) (UID:%s) (EEP:%s,%s,%s,%s)\n",
                    i,
                    systemInfo.busBoardsInfo[i].micBoardName,                    
                    systemInfo.busBoardsInfo[i].micBoardCode, systemInfo.busBoardsInfo[i].micBoardAddr, systemInfo.busBoardsInfo[i].micFwVers[0], systemInfo.busBoardsInfo[i].micFwVers[1],
                    (systemInfo.busBoardsInfo[i].commRes&COMM_ERR__UART_DEMUX) ?   ERR_CHAR__UART_DEMUX   : ERR_CHAR__NONE,
                    (systemInfo.busBoardsInfo[i].commRes&COMM_ERR__UART_SUBADDR) ? ERR_CHAR__UART_SUBADDR : ERR_CHAR__NONE,
                    (systemInfo.busBoardsInfo[i].commRes&COMM_ERR__I2C) ?          ERR_CHAR__I2C          : ERR_CHAR__NONE,
                    FPGA_DATA_NONE, systemInfo.busBoardsInfo[i].fpgaData1,
                    uid,
                    &misc_info[0][0], &misc_info[1][0], &misc_info[2][0], &misc_info[3][0]
                  );                                
                Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            }
            // A20xx e AS20P2
            else if((systemInfo.busBoardsInfo[i].micBoardCode == BC_A20C5) ||
                    (systemInfo.busBoardsInfo[i].micBoardCode == BC_A20I2) ||
                    (systemInfo.busBoardsInfo[i].micBoardCode == BC_AS20P2) )
            {             
                sprintf(outStr, "S%d: %s  (MIC:%c,%c,v%d.%d) (ERR:%c%c%c) (F:%s,%s) (UID:%s) (EEP:%s,%s,%s,%s)\n",
                    i,
                    systemInfo.busBoardsInfo[i].micBoardName,                    
                    systemInfo.busBoardsInfo[i].micBoardCode, systemInfo.busBoardsInfo[i].micBoardAddr, systemInfo.busBoardsInfo[i].micFwVers[0], systemInfo.busBoardsInfo[i].micFwVers[1],
                    (systemInfo.busBoardsInfo[i].commRes&COMM_ERR__UART_DEMUX) ?   ERR_CHAR__UART_DEMUX   : ERR_CHAR__NONE,
                    (systemInfo.busBoardsInfo[i].commRes&COMM_ERR__UART_SUBADDR) ? ERR_CHAR__UART_SUBADDR : ERR_CHAR__NONE,
                    (systemInfo.busBoardsInfo[i].commRes&COMM_ERR__I2C) ?          ERR_CHAR__I2C          : ERR_CHAR__NONE,
                    systemInfo.busBoardsInfo[i].fpgaData0, systemInfo.busBoardsInfo[i].fpgaData1,
                    uid,
                    &misc_info[0][0], &misc_info[1][0], &misc_info[2][0], &misc_info[3][0]
                  );                                
                Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            }
            // IOHS
            else if((systemInfo.busBoardsInfo[i].micBoardCode == BC_IORX)   ||
                    (systemInfo.busBoardsInfo[i].micBoardCode == BC_IORXTX) ||
                    (systemInfo.busBoardsInfo[i].micBoardCode == BC_IOTX)   )
            {             
                sprintf(outStr, "S%d: %s  (MIC:%c,%c,v%d.%d) (ERR:%c%c%c) (F:%s,%s) (UID:%s) (EEP:%s,%s,%s,%s)\n",
                    i,
                    systemInfo.busBoardsInfo[i].micBoardName,                    
                    systemInfo.busBoardsInfo[i].micBoardCode, systemInfo.busBoardsInfo[i].micBoardAddr, systemInfo.busBoardsInfo[i].micFwVers[0], systemInfo.busBoardsInfo[i].micFwVers[1],
                    (systemInfo.busBoardsInfo[i].commRes&COMM_ERR__UART_DEMUX) ?   ERR_CHAR__UART_DEMUX   : ERR_CHAR__NONE,
                    (systemInfo.busBoardsInfo[i].commRes&COMM_ERR__UART_SUBADDR) ? ERR_CHAR__UART_SUBADDR : ERR_CHAR__NONE,
                    (systemInfo.busBoardsInfo[i].commRes&COMM_ERR__I2C) ?          ERR_CHAR__I2C          : ERR_CHAR__NONE,
                    FPGA_DATA_NONE, FPGA_DATA_NONE,
                    uid,
                    &misc_info[0][0], &misc_info[1][0], &misc_info[2][0], &misc_info[3][0]
                  );                                
                Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            }
            else
            {
                sprintf(outStr, "S%d: %s  (MIC:%c,%c,v%d.%d) (ERR:%c%c%c) (F:%s,%s) (UID:%s) (EEP:%s,%s,%s,%s)\n",
                    i,
                    systemInfo.busBoardsInfo[i].micBoardName,                    
                    systemInfo.busBoardsInfo[i].micBoardCode, systemInfo.busBoardsInfo[i].micBoardAddr, systemInfo.busBoardsInfo[i].micFwVers[0], systemInfo.busBoardsInfo[i].micFwVers[1],
                    (systemInfo.busBoardsInfo[i].commRes&COMM_ERR__UART_DEMUX) ?   ERR_CHAR__UART_DEMUX   : ERR_CHAR__NONE,
                    (systemInfo.busBoardsInfo[i].commRes&COMM_ERR__UART_SUBADDR) ? ERR_CHAR__UART_SUBADDR : ERR_CHAR__NONE,
                    (systemInfo.busBoardsInfo[i].commRes&COMM_ERR__I2C) ?          ERR_CHAR__I2C          : ERR_CHAR__NONE,
                    systemInfo.busBoardsInfo[i].fpgaData0, systemInfo.busBoardsInfo[i].fpgaData1,
                    uid,
                    &misc_info[0][0], &misc_info[1][0], &misc_info[2][0], &misc_info[3][0]
                  );                                
                Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            }                 
        }
    }
    #endif

    return 0;
}


// fornisce una stringa con il nome del sistema (per il comando IDN)
// param:
//  - sysTypeStr: array dove viene messo il tipo di cassetto, casi:
//    - CASES-POL o CASES-POL-E
//    - CASES-NPL o CASES-NPL-E
//    - CASES-NPR o CASES-NPR-E
//    - CASES-UNK o CASES-UNK-E
void PeriphSYS_GetSystemType(char *sysTypeStr)
{
    #if(HW_TYPE==HW_EPICA)
    if((systemInfo.systemType & SYS_TYP__MSK) == SYS_TYP__EPICA)
        sprintf(sysTypeStr, "%s", "EPICA");  
    #endif
    #if(HW_TYPE==HW_CASES)
    if((systemInfo.systemType & SYS_TYP__MSK) == SYS_TYP__CASES_POL)
        sprintf(sysTypeStr, "%s", "CASES-POL");
    else if((systemInfo.systemType & SYS_TYP__MSK) == SYS_TYP__CASES_NPL)
        sprintf(sysTypeStr, "%s", "CASES-NPL");
    else if((systemInfo.systemType & SYS_TYP__MSK) == SYS_TYP__CASES_NPR)
        sprintf(sysTypeStr, "%s", "CASES-NPR");
    #endif
    else
        sprintf(sysTypeStr, "%s", "UNK");
    //
    if(systemInfo.systemType & SYS_TYP__ERR)
        strcat(sysTypeStr, "-E");
}


// *** FUNCTION - Communication *************************************************

// invia un comando (e riceve la risposta) per il micro o un fpga di una delle schede
// param:
//  - board_addr    : 0-7 e 8 per la TICK
//  - sub_addr      : 0-1 e 9 per il micro
//  - cmd           : buffer del comando da inviare (!!! non deve contenere '@' !!!)
//  - cmd_len       : lunghezza del comando da inviare
//  - wait_ans      : indica se si aspetta la risposta o no
//  - ans_buff      : buffer dove mettere la risposta
//  - max_ans_len   : numero di byte che si deve ricevere per chiudere la ricezione (se riceve meno c'è il time out nella config)
//  - byte_received : numero di byte ricevuti
//  NB: utilizzare buffer lunghi UART_BUFF_SIZE
// return:
//  - PERIPH_RES__OK
//  - PERIPH_RES__UART_CONFIG_ERROR
//  - PERIPH_RES__WRONG_BOARD_ADDR
//  - PERIPH_RES__WRONG_BOARD_SUB_ADDR
//  - PERIPH_RES__TOO_MANY_BYTE
//  - PERIPH_RES__UART_SENDING_ERROR
//  - PERIPH_RES__NO_ANSWER_RECEIVED
int PeriphSYS_Uart_SendCommand(uint8_t board_addr, uint8_t sub_addr, uint8_t *cmd, uint8_t cmd_len, bool wait_ans, uint8_t *ans_buff, uint8_t max_ans_len, uint8_t *byte_received)
{
    int ret = PERIPH_RES__OK;

    if(!uartConfigured)
    {
        #ifdef PRINT_OUTPUT__PERIPH_SYS
        sprintf(outStr, "UART not configured !!!\n");
        Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
        #endif

        return PERIPH_RES__UART_CONFIG_ERROR;
    }

    if(board_addr > 8)
    {
        #ifdef PRINT_OUTPUT__PERIPH_SYS
        sprintf(outStr, "UART Wrong board addr (%d) !!!\n", board_addr);
        Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
        #endif

        return PERIPH_RES__WRONG_BOARD_ADDR;
    }

    if((sub_addr > 1) && (sub_addr != 9))
    {
        #ifdef PRINT_OUTPUT__PERIPH_SYS
        sprintf(outStr, "UART Wrong sub addr (%d) !!!\n", sub_addr);
        Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
        #endif

        return PERIPH_RES__WRONG_BOARD_SUB_ADDR;
    }

    if(cmd_len > UART_BUFF_SIZE)
    {
        #ifdef PRINT_OUTPUT__PERIPH_SYS
        sprintf(outStr, "UART Too many byte to send (%d) !!!\n", cmd_len);
        Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
        #endif

        return PERIPH_RES__TOO_MANY_BYTE;
    }

    // La struttura del protocollo da rispettare per inviare i comandi è la seguente:
    //  Header(1 byte)   Bus Address(1 byte)   Internal Address(1 byte)    Payload(n byte)   Terminator(1 byte)
    //   ‘@’              ‘0’ a ‘7’ e ‘8’       ‘0’ a ‘1’ e ‘9’             -                 CR (0x0D)
    //
    // L’indirizzamento cambia quindi in funzione della parte alla quale si vuole inviare il comando:
    // - schede PBI5, A20I2 e A20C5, primo slave interno: “@00” a “@70”;
    // - schede PBI5, A20I2 e A20C5, secondo slave interno: “@01” a “@71”;
    // - scheda TICK, primo slave interno: “@80”;
    // - scheda TICK, secondo slave interno: “@81”;
    // - tutte le schede, gestore CAT interno al firmware: “@09” a “@89”.

    uint8_t tx_buffer[UART_BUFF_SIZE + 4];
    uint8_t tx_buffer_len = cmd_len + 4;

    // prepara i dati da inviare
    memset(tx_buffer, 0, UART_BUFF_SIZE + 4);
    tx_buffer[0] = '@';
    tx_buffer[1] = 0x30 | board_addr;
    tx_buffer[2] = 0x30 | sub_addr;
    memcpy(&tx_buffer[3], cmd, cmd_len);
    tx_buffer[tx_buffer_len-1] = 0x0D;

    #ifdef PRINT_OUTPUT__PERIPH_SYS
    sprintf(outStr, "UART Sending : ", tx_buffer);
    Sys_PrintOutput(PT_YES, INF_EXT, periphSysPrefix, outStr);
	  for(int i=0; i<tx_buffer_len; i++)
    {
        if((tx_buffer[i]<0x20) || (tx_buffer[i]>0x7E))
          sprintf(outStr, "%c", '.');
        else
          sprintf(outStr, "%c", tx_buffer[i]);
        Sys_PrintOutput(PT_NO, INF_EXT, "", outStr);
    }
	  Sys_PrintOutput(PT_NO, INF_EXT, "", "\n");
    #endif

    // gestione tx/rx
    ret = PeriphUART_SendReceive(tx_buffer, tx_buffer_len, wait_ans, ans_buff, max_ans_len, byte_received);
    if(ret != UART_RES__OK)
    {
        #ifdef PRINT_OUTPUT__PERIPH_SYS
        sprintf(outStr, "UART Sending error !!!\n");
        Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
        #endif

        return PERIPH_RES__UART_SENDING_ERROR;
    }
    
    // attesa risposta
    if(wait_ans)
    {
        // analisi numero di byte ricevuti
        if(*byte_received == 0)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "UART No answer received !!!\n");
            Sys_PrintOutput(PT_YES, INF_EXT, periphSysPrefix, outStr);
            #endif

            return PERIPH_RES__NO_ANSWER_RECEIVED;
        }

        #ifdef PRINT_OUTPUT__PERIPH_SYS
        sprintf(outStr, "UART Received: ");
        Sys_PrintOutput(PT_YES, INF_EXT, periphSysPrefix, outStr);
        for(int i=0; i<*byte_received; i++)
        {
            if((ans_buff[i]<0x20) || (ans_buff[i]>0x7E))
              sprintf(outStr, "%c", '.');
            else
              sprintf(outStr, "%c", ans_buff[i]);
            Sys_PrintOutput(PT_NO, INF_EXT, "", outStr);
        }
        Sys_PrintOutput(PT_NO, INF_EXT, "", "\n");
        #endif
    }
    else
    {
        #ifdef PRINT_OUTPUT__PERIPH_SYS
        Sys_PrintOutput(PT_YES, INF_EXT, periphSysPrefix, "UART Skip ans !!!\n");
        #endif
    }

    return ret;
}


// permette di leggere un'EEPROM
// param:
//  - board_addr: 0-7, 8 per la TICK, altro valore per la EK26
//  - page_idx  : indice della pagina dove iniziare la lettura:
//    - per la EK26: 0 a 255 o altro valore per la Identification Page
//    - per le altre schede: 0 a 15
//  - data      : buffer dove mettere i dati letti (max 256)
//  - data_len  : numero di byte da leggere (idealmente, multiplo del numero di byte di una pagina)
//  NB: utilizzare un buffer lungo I2C_BUFF_SIZE__READ (256)
// return:
//  - PERIPH_RES__OK
//  - PERIPH_RES__WRONG_PAGE_IDX
//  - PERIPH_RES__IOEXP_CONFIG1_ERROR
//  - PERIPH_RES__IOEXP_CONFIG2_ERROR
//  - PERIPH_RES__IOEXP_DRIVE1_ERROR
//  - PERIPH_RES__IOEXP_DRIVE2_ERROR
//  - PERIPH_RES__EEP_READ_Sx_ERROR
//  - PERIPH_RES__EEP_READ_TI_ERROR
//  - PERIPH_RES__EEP_READ_EK_ERROR
int PeriphSYS_I2c_ReadEeprom(uint8_t board_addr, uint16_t page_idx, uint8_t *data, uint16_t data_len)
{ 
    int ret = PERIPH_RES__OK;

    uint8_t ioexpAddr = 0x20;
    uint8_t eepAddr = 0x57;
    uint16_t pageAddr = 0;


    #ifdef PRINT_OUTPUT__PERIPH_SYS
    sprintf(outStr, "I2C Reading: board %d, page %d, len %d\n", board_addr, page_idx, data_len);
    Sys_PrintOutput(PT_YES, INF_EXT, periphSysPrefix, outStr);
    #endif
    

    // --- PBI5, A20C5 e A20I2 ---
    if(board_addr < BUS_BOARD_IDX__TI)
    {
        // controllo indice pagina
        if(page_idx>15)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C Wrong page index (%d) !!!\n", page_idx);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif

            return PERIPH_RES__WRONG_PAGE_IDX;
        }
        
        // preparazione
        pageAddr  = page_idx * 16; // 0x00, 0x10, 0x20, ... 0xF0
        ioexpAddr = 0x20 + board_addr;
        eepAddr   = 0x54;

        // configura l'IO Expander: tutti pin a 1
        ret = PeriphI2C_IoExpWrite(ioexpAddr, 0x01, 0xFF);
        if(ret != I2C_RES__OK)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C IoExp config1 error (%d) !!!\n", ret);
            Sys_PrintOutput(PT_YES, /*INF_STD*/ INF_EXT, periphSysPrefix, outStr); // INF_EXT per evitare che l'errore venga fuori facendo il discovery quando non c'è la scheda
            #endif
            return PERIPH_RES__IOEXP_CONFIG1_ERROR;
        }

        // configura l'IO Expander: P0 P3 e P4 in output
        ret = PeriphI2C_IoExpWrite(ioexpAddr, 0x03, 0xE6);
        if(ret != I2C_RES__OK)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C IoExp config2 error (%d) !!!\n", ret);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif
            return PERIPH_RES__IOEXP_CONFIG2_ERROR;
        }

        // seleziona l'eeprom (con LED on)
        ret = PeriphI2C_IoExpWrite(ioexpAddr, 0x01, 0xE6);
        if(ret != I2C_RES__OK)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C IoExp drive1 error (%d) !!!\n", ret);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif
            return PERIPH_RES__IOEXP_DRIVE1_ERROR;
        }

        // legge la pagina richiesta
        ret = PeriphI2C_EepRead(eepAddr, EEP_ADDR_LEN__1B, pageAddr, data, data_len);
        if(ret != I2C_RES__OK)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C EEP read S%d error (%d) !!!\n", board_addr, ret);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif
            return PERIPH_RES__EEP_READ_Sx_ERROR;
        }

        // deseleziona l'eeprom (con LED off)
        ret = PeriphI2C_IoExpWrite(ioexpAddr, 0x01, 0xFF);
        if(ret != I2C_RES__OK)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C IoExp drive2 error (%d) !!!\n", ret);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif
            return PERIPH_RES__IOEXP_DRIVE2_ERROR;
        }
    }
    // --- TICK ---
    else if(board_addr == BUS_BOARD_IDX__TI)
    {
        // controllo indice pagina
        if(page_idx>15)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C Wrong page index (%d) !!!\n", page_idx);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif

            return PERIPH_RES__WRONG_PAGE_IDX;
        }
        
        // preparazione
        pageAddr  = page_idx * 16; // 0x00, 0x10, 0x20, ... 0xF0
        eepAddr   = 0x53;

        // legge la pagina richiesta
        ret = PeriphI2C_EepRead(eepAddr, EEP_ADDR_LEN__1B, pageAddr, data, data_len);
        if(ret != I2C_RES__OK)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C EEP read TI error (%d) !!!\n", ret);
            Sys_PrintOutput(PT_YES, /*INF_STD*/ INF_EXT, periphSysPrefix, outStr); // INF_EXT per evitare che l'errore venga fuori facendo il discovery quando non c'è la scheda
            #endif
            return PERIPH_RES__EEP_READ_TI_ERROR;
        }      
    }
    // --- EK26 ---
    else
    {               
        // preparazione     
        if(page_idx < 256)
        {
            pageAddr  = page_idx * 32;  // 0x0000, 0x0020, 0x0040, ... 0x1FE0
            eepAddr   = 0x51;
        }
        else
        {
            pageAddr  = 0;  // Identification Page
            eepAddr   = 0x59;
        }

        // legge la pagina richiesta
        ret = PeriphI2C_EepRead(eepAddr, EEP_ADDR_LEN__2B, pageAddr, data, data_len);
        if(ret != I2C_RES__OK)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C EEP read EK error (%d) !!!\n", ret);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif
            return PERIPH_RES__EEP_READ_EK_ERROR;
        }
    }

    #ifdef PRINT_OUTPUT__PERIPH_SYS
    sprintf(outStr, "I2C Read:");
    Sys_PrintOutput(PT_YES, INF_EXT, periphSysPrefix, outStr);
    for(int i=0; i<data_len; i++)
    {
        sprintf(outStr, " 0x%02X", data[i]);
        Sys_PrintOutput(PT_NO, INF_EXT, "", outStr);
    }
    Sys_PrintOutput(PT_NO, INF_EXT, "", "\n");
    #endif

    return ret;
}


// permette di scrivere una pagina di un'EEPROM
// param:
//  - board_addr: 0-7, 8 per la TICK, altro valore per la EK26
//  - page_idx  : indice della pagina dove iniziare la lettura:
//    - per la EK26: 0 a 255
//    - per le altre schede: 0 a 7
//  - page_data : byte da scrivere (16B, o 32B per la EK26)
//  NB: utilizzare un buffer lungo I2C_BUFF_SIZE__PAGE_WRITE (32)
// return:
//  - PERIPH_RES__OK
//  - PERIPH_RES__WRONG_PAGE_IDX
//  - PERIPH_RES__IOEXP_CONFIG1_ERROR
//  - PERIPH_RES__IOEXP_CONFIG2_ERROR
//  - PERIPH_RES__IOEXP_DRIVE1_ERROR
//  - PERIPH_RES__IOEXP_DRIVE2_ERROR
//  - PERIPH_RES__EEP_READ_Sx_ERROR
//  - PERIPH_RES__EEP_READ_TI_ERROR
//  - PERIPH_RES__EEP_READ_EK_ERROR
int PeriphSYS_I2c_WriteEepromPage(uint8_t board_addr, uint16_t page_idx, uint8_t *page_data)
{
    int ret = PERIPH_RES__OK;

    uint8_t ioexpAddr = 0x20;
    uint8_t eepAddr = 0x57;
    uint16_t pageAddr = 0;


    #ifdef PRINT_OUTPUT__PERIPH_SYS
    sprintf(outStr, "I2C Writing page: board %d, page %d, len %d\n", board_addr, page_idx, (board_addr<=BUS_BOARD_IDX__TI) ? 16 : 32);
    Sys_PrintOutput(PT_YES, INF_EXT, periphSysPrefix, outStr);
    //
    sprintf(outStr, "I2C Write:");
    Sys_PrintOutput(PT_YES, INF_EXT, periphSysPrefix, outStr);
    for(int i=0; i<((board_addr<=BUS_BOARD_IDX__TI) ? 16 : 32); i++)
    {
        sprintf(outStr, " 0x%02X", page_data[i]);
        Sys_PrintOutput(PT_NO, INF_EXT, "", outStr);
    }
    Sys_PrintOutput(PT_NO, INF_EXT, "", "\n");
    #endif

    // --- PBI5, A20C5 e A20I2 ---
    if(board_addr < BUS_BOARD_IDX__TI)
    {
        // controllo indice pagina
        if(page_idx>7)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C Wrong page index (%d) !!!\n", page_idx);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif

            return PERIPH_RES__WRONG_PAGE_IDX;
        }
        
        // preparazione
        pageAddr  = page_idx * 16; // 0x00, 0x10, 0x20, ... 0x70
        ioexpAddr = 0x20 + board_addr;
        eepAddr   = 0x54;

        // configura l'IO Expander: tutti pin a 1
        ret = PeriphI2C_IoExpWrite(ioexpAddr, 0x01, 0xFF);
        if(ret != I2C_RES__OK)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C IoExp config1 error (%d) !!!\n", ret);
            Sys_PrintOutput(PT_YES, /*INF_STD*/ INF_EXT, periphSysPrefix, outStr); // INF_EXT per evitare che l'errore venga fuori facendo il discovery quando non c'è la scheda
            #endif
            return PERIPH_RES__IOEXP_CONFIG1_ERROR;
        }

        // configura l'IO Expander: P0 P3 e P4 in output
        ret = PeriphI2C_IoExpWrite(ioexpAddr, 0x03, 0xE6);
        if(ret != I2C_RES__OK)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C IoExp config2 error (%d) !!!\n", ret);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif
            return PERIPH_RES__IOEXP_CONFIG2_ERROR;
        }

        // seleziona l'eeprom (con LED on)
        ret = PeriphI2C_IoExpWrite(ioexpAddr, 0x01, 0xE6);
        if(ret != I2C_RES__OK)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C IoExp drive1 error (%d) !!!\n", ret);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif
            return PERIPH_RES__IOEXP_DRIVE1_ERROR;
        }

        // scrive la pagina
        ret = PeriphI2C_EepWritePage(eepAddr, EEP_ADDR_LEN__1B, pageAddr, page_data);
        if(ret != I2C_RES__OK)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C EEP write S%d error (%d) !!!\n", board_addr, ret);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif
            return PERIPH_RES__EEP_WRITE_Sx_ERROR;
        }

        // deseleziona l'eeprom (con LED off)
        ret = PeriphI2C_IoExpWrite(ioexpAddr, 0x01, 0xFF);
        if(ret != I2C_RES__OK)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C IoExp drive2 error (%d) !!!\n", ret);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif
            return PERIPH_RES__IOEXP_DRIVE2_ERROR;
        }
    }
    // --- TICK ---
    else if(board_addr == BUS_BOARD_IDX__TI)
    {
        // controllo indice pagina
        if(page_idx>7)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C Wrong page index (%d) !!!\n", page_idx);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif

            return PERIPH_RES__WRONG_PAGE_IDX;
        }
        
        // preparazione
        pageAddr  = page_idx * 16; // 0x00, 0x10, 0x20, ... 0x70
        eepAddr   = 0x53;

        // scrive la pagina
        ret = PeriphI2C_EepWritePage(eepAddr, EEP_ADDR_LEN__1B, pageAddr, page_data);
        if(ret != I2C_RES__OK)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C EEP write TI error (%d) !!!\n", ret);
            Sys_PrintOutput(PT_YES, /*INF_STD*/ INF_EXT, periphSysPrefix, outStr); // INF_EXT per evitare che l'errore venga fuori facendo il discovery quando non c'è la scheda
            #endif
            return PERIPH_RES__EEP_WRITE_TI_ERROR;
        }      
    }
    // --- EK26 ---
    else
    {
        // controllo indice pagina
        if(page_idx>255)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C Wrong page index (%d) !!!\n", page_idx);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif

            return PERIPH_RES__WRONG_PAGE_IDX;
        }

        // preparazione     
        // if(page_idx < 256)
        // {
            pageAddr  = page_idx * 32;  // 0x0000, 0x0020, 0x0040, ... 0x1FE0
            eepAddr   = 0x51;
        // }
        // else
        // {
        //     pageAddr  = 0;  // Identification Page
        //     eepAddr   = 0x59;
        // }

        // scrive la pagina
        ret = PeriphI2C_EepWritePage(eepAddr, EEP_ADDR_LEN__2B, pageAddr, page_data);
        if(ret != I2C_RES__OK)
        {
            #ifdef PRINT_OUTPUT__PERIPH_SYS
            sprintf(outStr, "I2C EEP write EK error (%d) !!!\n", ret);
            Sys_PrintOutput(PT_YES, INF_STD, periphSysPrefix, outStr);
            #endif
            return PERIPH_RES__EEP_WRITE_EK_ERROR;
        }
    }

    return ret;
}

