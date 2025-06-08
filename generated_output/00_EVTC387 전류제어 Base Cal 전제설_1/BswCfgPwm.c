/*
	<파일 생성 정보>
	  * 파일 생성일 : 2025.06.08
	  * 대상 파일   : 00_EVTC387 전류제어 Base Cal 전제설_1.db
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
	@file		:	BswCfgPwm.c
	@brief		:	
	@author		:	JY.Park
	@date		:	

*/
/*=========================================================================================*/

/*===========================================================================================
	INCLUDES
===========================================================================================*/
#include "BswCfgPwm.h"

/*===========================================================================================
	Global Variables
===========================================================================================*/
#include "section_CAL2_begin.h"
const UINT32 BswCfgCal_Pwm_MotStartTime				= BSWCFGPWM_MOT_START;
const UINT32 BswCfgCal_Pwm_MotPeriod				= BSWCFGPWM_MOT_PERIOD;
const UINT32 BswCfgCal_Pwm_MotDeadTime_INV1			= BSWCFGPWM_MOT_INV1_DEADTIME;
const UINT32 BswCfgCal_Pwm_MotDeadTime_INV2			= BSWCFGPWM_MOT_INV2_DEADTIME;
const UINT32 BswCfgCal_Pwm_MotDeadTime_Multi		= BSWCFGPWM_MOT_DEADTIME_MULTI;
const UINT32 BswCfgCal_Pwm_MotMinPulseWidth_INV1	= BSWCFGPWM_MOT_INV1_MIN_WIDTH;
const UINT32 BswCfgCal_Pwm_MotMinPulseWidth_INV2	= BSWCFGPWM_MOT_INV2_MIN_WIDTH;
const UINT32 BswCfgCal_Pwm_MotUpdateTime_INV1		= BSWCFGPWM_MOT_INV1_UPDATE_TIME;
const UINT32 BswCfgCal_Pwm_MotUpdateTime_INV2		= BSWCFGPWM_MOT_INV2_UPDATE_TIME;
const UINT8  BswCfgCal_Pwm_MotPwmMode				= BSWCFGPWM_MOT_PWMMAC_MODE;
const UINT32 BswCfgCal_Pwm_MotAsacEdgeOffset		= BSWCFGPWM_MOT_ASAC_EDGE_OFFSET;
const UINT8  BswCfgCal_Pwm_MotUpdatetime_AutoMode	= BSWCFGPWM_MOT_UPDATETIME_AUTO_MODE;
const UINT32 BswCfgCal_Pwm_MoteTPULoad_SYNC			= BSWCFGPWM_MOT_eTPULoad_SYNC;
const UINT32 BswCfgCal_Pwm_MoteTPULoad_RSLV			= BSWCFGPWM_MOT_eTPULoad_RSLV;
const UINT32 BswCfgCal_Pwm_MoteTPULoad_PWM			= BSWCFGPWM_MOT_eTPULoad_PWM;
const UINT32 BswCfgCal_Pwm_HsgStartTime				= BSWCFGPWM_HSG_START;
const UINT32 BswCfgCal_Pwm_HsgPeriod				= BSWCFGPWM_HSG_PERIOD;
const UINT32 BswCfgCal_Pwm_HsgDeadTime_INV1			= BSWCFGPWM_HSG_INV1_DEADTIME;
const UINT32 BswCfgCal_Pwm_HsgDeadTime_INV2			= BSWCFGPWM_HSG_INV2_DEADTIME;
const UINT32 BswCfgCal_Pwm_HsgMinPulseWidth_INV1	= BSWCFGPWM_HSG_INV1_MIN_WIDTH;
const UINT32 BswCfgCal_Pwm_HsgMinPulseWidth_INV2	= BSWCFGPWM_HSG_INV2_MIN_WIDTH;
const UINT32 BswCfgCal_Pwm_HsgUpdateTime_INV1		= BSWCFGPWM_HSG_INV1_UPDATE_TIME;
const UINT32 BswCfgCal_Pwm_HsgUpdateTime_INV2		= BSWCFGPWM_HSG_INV2_UPDATE_TIME;
const UINT8  BswCfgCal_Pwm_HsgPwmMode				= BSWCFGPWM_HSG_PWMMAC_MODE;
const UINT32 BswCfgCal_Pwm_HsgAsacEdgeOffset		= BSWCFGPWM_HSG_ASAC_EDGE_OFFSET;
const UINT8  BswCfgCal_Pwm_HsgUpdatetime_AutoMode	= BSWCFGPWM_HSG_UPDATETIME_AUTO_MODE;
const UINT32 BswCfgCal_Pwm_HsgeTPULoad_SYNC			= BSWCFGPWM_HSG_eTPULoad_SYNC;
const UINT32 BswCfgCal_Pwm_HsgeTPULoad_RSLV			= BSWCFGPWM_HSG_eTPULoad_RSLV;
const UINT32 BswCfgCal_Pwm_HsgeTPULoad_PWM			= BSWCFGPWM_HSG_eTPULoad_PWM;
#include "section_CAL_end.h"
UINT32 BswCfgVal_Pwm_MotUpdateTime_INV1		= BSWCFGPWM_MOT_INV1_UPDATE_TIME;
UINT32 BswCfgVal_Pwm_MotUpdateTime_INV2		= BSWCFGPWM_MOT_INV2_UPDATE_TIME;
UINT32 BswCfgVal_Pwm_HsgUpdateTime_INV1		= BSWCFGPWM_HSG_INV1_UPDATE_TIME;
UINT32 BswCfgVal_Pwm_HsgUpdateTime_INV2		= BSWCFGPWM_HSG_INV2_UPDATE_TIME;

/********************************************************************************************
*                                        End of File                                        *
********************************************************************************************/
