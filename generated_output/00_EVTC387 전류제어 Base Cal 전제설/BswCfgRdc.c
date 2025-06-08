/*
	<파일 생성 정보>
	  * 파일 생성일 : 2025.06.08
	  * 대상 파일   : 00_EVTC387 전류제어 Base Cal 전제설.db
	  * 생성 시 발견된 오류 리스트
		 >> 발견된 오류가 없습니다
*/

/********************************************************************************************
*                                   S O U R C E   F I L E                                   *
*                             (C) by Hyundai Motor Company LTD.                             *
********************************************************************************************/

/*===========================================================================================
		Origanization
===========================================================================================*/
/**
	@file		:	BswCfgRdc.c
	@brief		:	
	@author		:	JY.Park
	@date		:	

*/
/*=========================================================================================*/

/*===========================================================================================
	INCLUDES
===========================================================================================*/
#include "BswCfgRdc.h"

/*===========================================================================================
	Global Variables
===========================================================================================*/
#include "section_CAL2_begin.h"
const UINT32  BswCfgCal_Rdc_MotPeriod				= BSWCFGRDC_MOT_PERIOD;
const FLOAT32 BswCfgCal_Rdc_MotStartOffset			= BSWCFGRDC_MOT_START_OFFSET;
const FLOAT32 BswCfgCal_Rdc_MotK1					= BSWCFGRDC_MOT_K1_D;
const FLOAT32 BswCfgCal_Rdc_MotK2					= BSWCFGRDC_MOT_K2_D;
const INT32   BswCfgCal_Rdc_MotK1Scale				= BSWCFGRDC_MOT_K1_SCALE;
const INT32   BswCfgCal_Rdc_MotK2Scale				= BSWCFGRDC_MOT_K2_SCALE;
const UINT32  BswCfgCal_Rdc_MotSinDcOffset			= BSWCFGRDC_MOT_SIN_DC_OFFSET;
const UINT32  BswCfgCal_Rdc_MotCosDcOffset			= BSWCFGRDC_MOT_COS_DC_OFFSET;
const INT32   BswCfgCal_Rdc_MotSinScale				= BSWCFGRDC_MOT_SIN_SCALE;
const INT32   BswCfgCal_Rdc_MotCosScale				= BSWCFGRDC_MOT_COS_SCALE;
const UINT32  BswCfgCal_Rdc_MotUnitrigDelay			= BSWCFGRDC_MOT_UNITRIG_DELAY;
const UINT32  BswCfgCal_Rdc_MotUnitrigStartOffset	= BSWCFGRDC_MOT_UNITRIG_START_OFFSET;
const UINT32  BswCfgCal_Rdc_HsgPeriod				= BSWCFGRDC_HSG_PERIOD;
const FLOAT32 BswCfgCal_Rdc_HsgStartOffset			= BSWCFGRDC_HSG_START_OFFSET;
const FLOAT32 BswCfgCal_Rdc_HsgK1					= BSWCFGRDC_HSG_K1_D;
const FLOAT32 BswCfgCal_Rdc_HsgK2					= BSWCFGRDC_HSG_K2_D;
const INT32   BswCfgCal_Rdc_HsgK1Scale				= BSWCFGRDC_HSG_K1_SCALE;
const INT32   BswCfgCal_Rdc_HsgK2Scale				= BSWCFGRDC_HSG_K2_SCALE;
const UINT32  BswCfgCal_Rdc_HsgSinDcOffset			= BSWCFGRDC_HSG_SIN_DC_OFFSET;
const UINT32  BswCfgCal_Rdc_HsgCosDcOffset			= BSWCFGRDC_HSG_COS_DC_OFFSET;
const INT32   BswCfgCal_Rdc_HsgSinScale				= BSWCFGRDC_HSG_SIN_SCALE;
const INT32   BswCfgCal_Rdc_HsgCosScale				= BSWCFGRDC_HSG_COS_SCALE;
const UINT32  BswCfgCal_Rdc_HsgUnitrigDelay			= BSWCFGRDC_HSG_UNITRIG_DELAY;
const UINT32  BswCfgCal_Rdc_HsgUnitrigStartOffset	= BSWCFGRDC_HSG_UNITRIG_START_OFFSET;
#include "section_CAL_end.h"

/********************************************************************************************
*                                        End of File                                        *
********************************************************************************************/
