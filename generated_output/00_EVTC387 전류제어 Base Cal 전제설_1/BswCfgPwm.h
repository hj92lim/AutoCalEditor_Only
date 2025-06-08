/*
	<파일 생성 정보>
	  * 파일 생성일 : 2025.06.08
	  * 대상 파일   : 00_EVTC387 전류제어 Base Cal 전제설_1.db
	  * 생성 시 발견된 오류 리스트
		 >> 발견된 오류가 없습니다
*/

/********************************************************************************************
*                                   H E A D E R   F I L E                                   *
*                             (C) by Hyundai Motor Company LTD.                             *
********************************************************************************************/

/*===========================================================================================
		Origanization
===========================================================================================*/
/**
	@file		:	BswCfgPwm.h
	@brief		:	
	@author		:	JY.Park
	@date		:	

*/
/*=========================================================================================*/

#ifndef _BSWCFGPWM_H_
#define _BSWCFGPWM_H_

/*===========================================================================================
	INCLUDES
===========================================================================================*/
#include "common.h"
#include "ItrPlatformType.h"
#include "ItrCpx.h"

/*===========================================================================================
	DEFINES
===========================================================================================*/
/*-------------------------------------------------------------------------------------------
	@name	: 공통 적용 사양(Micom 관련)
-------------------------------------------------------------------------------------------*/

/* MOTOR PWM Configuration */
#define	BSWCFGPWM_MOT_START			125000						// ns
#define	BSWCFGPWM_MOT_PERIOD		250000						// ns
#define	BSWCFGPWM_MOT_PWMMAC_MODE	ITRCPX_SAMPLMODE_DOUBLE

/* HSG PWM Configuration */
#define	BSWCFGPWM_HSG_START			125000
#define	BSWCFGPWM_HSG_PERIOD		250000
#define	BSWCFGPWM_HSG_PWMMAC_MODE	ITRCPX_SAMPLMODE_DOUBLE

/*-------------------------------------------------------------------------------------------
	@name	: PWM UPDATE TIME 자동화
-------------------------------------------------------------------------------------------*/

#if (_ETPU_CALCULATION_TIME_OPTION == _UNDEFINED_OPTION)
	#error undefined _ETPU_CALCULATION_TIME_OPTION_ (check #define!!)

#elif (_ETPU_CALCULATION_TIME_OPTION == _SINGLE_STAGE_SYSTEM)
	#define	BSWCFGPWM_MOT_INV1_UPDATE_TIME	3800	// 모든 프로젝트 19us적용(INV1 Worst적용)
	#define	BSWCFGPWM_MOT_INV2_UPDATE_TIME	3000	// 모든 프로젝트 15us적용(INV2 Worst적용)
	#define	BSWCFGPWM_MOT_eTPULoad_SYNC		500
	#define	BSWCFGPWM_MOT_eTPULoad_RSLV		3500
	#define	BSWCFGPWM_MOT_eTPULoad_PWM		9500
	#define	BSWCFGPWM_HSG_INV1_UPDATE_TIME	3800	// 모든 프로젝트 19us적용(INV1 Worst적용)
	#define	BSWCFGPWM_HSG_INV2_UPDATE_TIME	3000	// 모든 프로젝트 15us적용(INV2 Worst적용)
	#define	BSWCFGPWM_HSG_eTPULoad_SYNC		0
	#define	BSWCFGPWM_HSG_eTPULoad_RSLV		3500
	#define	BSWCFGPWM_HSG_eTPULoad_PWM		9500

#elif (_ETPU_CALCULATION_TIME_OPTION == _TWO_STAGE_SYSTEM)
	#define	BSWCFGPWM_MOT_INV1_UPDATE_TIME	3800	// 모든 프로젝트 19us적용(INV1 Worst적용)
	#define	BSWCFGPWM_MOT_INV2_UPDATE_TIME	3000	// 모든 프로젝트 15us적용(INV2 Worst적용)
	#define	BSWCFGPWM_MOT_eTPULoad_SYNC		500
	#define	BSWCFGPWM_MOT_eTPULoad_RSLV		3500
	#define	BSWCFGPWM_MOT_eTPULoad_PWM		9500
	#define	BSWCFGPWM_HSG_INV1_UPDATE_TIME	3800	// 모든 프로젝트 19us적용(INV1 Worst적용)
	#define	BSWCFGPWM_HSG_INV2_UPDATE_TIME	3000	// 모든 프로젝트 15us적용(INV2 Worst적용)
	#define	BSWCFGPWM_HSG_eTPULoad_SYNC		0
	#define	BSWCFGPWM_HSG_eTPULoad_RSLV		3500
	#define	BSWCFGPWM_HSG_eTPULoad_PWM		9500

#else
	#error undefined _ETPU_CALCULATION_TIME_OPTION MACRO

#endif
/*-------------------------------------------------------------------------------------------
	@name	: PWM UPDATE TIME 자동화
-------------------------------------------------------------------------------------------*/

#if (_PWM_UPDATETIME_AUTO_MODE == _UNDEFINED_OPTION)
	#error undefined _PWM_UPDATETIME_AUTO_MODE_ (check #define!!)

#elif (_PWM_UPDATETIME_AUTO_MODE == _UPDATETIME_AUTO)
	#define	BSWCFGPWM_MOT_UPDATETIME_AUTO_MODE	SET_FLAG
	#define	BSWCFGPWM_HSG_UPDATETIME_AUTO_MODE	SET_FLAG

#elif (_PWM_UPDATETIME_AUTO_MODE == _UPDATETIME_MANUAL)
	#define	BSWCFGPWM_MOT_UPDATETIME_AUTO_MODE	CLR_FLAG
	#define	BSWCFGPWM_HSG_UPDATETIME_AUTO_MODE	CLR_FLAG

#else
	#error undefined _PWM_UPDATETIME_AUTO_MODE MACRO

#endif

/*===========================================================================================
	TYPE DEFINITIONS
===========================================================================================*/

/*===========================================================================================
	Global Variables
===========================================================================================*/
#include "section_CAL2_begin.h"
extern const UINT32 BswCfgCal_Pwm_MotStartTime;
extern const UINT32 BswCfgCal_Pwm_MotPeriod;
extern const UINT32 BswCfgCal_Pwm_MotDeadTime_INV1;
extern const UINT32 BswCfgCal_Pwm_MotDeadTime_INV2;
extern const UINT32 BswCfgCal_Pwm_MotDeadTime_Multi;
extern const UINT32 BswCfgCal_Pwm_MotMinPulseWidth_INV1;
extern const UINT32 BswCfgCal_Pwm_MotMinPulseWidth_INV2;
extern const UINT32 BswCfgCal_Pwm_MotUpdateTime_INV1;
extern const UINT32 BswCfgCal_Pwm_MotUpdateTime_INV2;
extern const UINT8  BswCfgCal_Pwm_MotPwmMode;
extern const UINT32 BswCfgCal_Pwm_MotAsacEdgeOffset;
extern const UINT8  BswCfgCal_Pwm_MotUpdatetime_AutoMode;
extern const UINT32 BswCfgCal_Pwm_MoteTPULoad_SYNC;
extern const UINT32 BswCfgCal_Pwm_MoteTPULoad_RSLV;
extern const UINT32 BswCfgCal_Pwm_MoteTPULoad_PWM;
extern const UINT32 BswCfgCal_Pwm_HsgStartTime;
extern const UINT32 BswCfgCal_Pwm_HsgPeriod;
extern const UINT32 BswCfgCal_Pwm_HsgDeadTime_INV1;
extern const UINT32 BswCfgCal_Pwm_HsgDeadTime_INV2;
extern const UINT32 BswCfgCal_Pwm_HsgMinPulseWidth_INV1;
extern const UINT32 BswCfgCal_Pwm_HsgMinPulseWidth_INV2;
extern const UINT32 BswCfgCal_Pwm_HsgUpdateTime_INV1;
extern const UINT32 BswCfgCal_Pwm_HsgUpdateTime_INV2;
extern const UINT8  BswCfgCal_Pwm_HsgPwmMode;
extern const UINT32 BswCfgCal_Pwm_HsgAsacEdgeOffset;
extern const UINT8  BswCfgCal_Pwm_HsgUpdatetime_AutoMode;
extern const UINT32 BswCfgCal_Pwm_HsgeTPULoad_SYNC;
extern const UINT32 BswCfgCal_Pwm_HsgeTPULoad_RSLV;
extern const UINT32 BswCfgCal_Pwm_HsgeTPULoad_PWM;
#include "section_CAL_end.h"
extern UINT32 BswCfgVal_Pwm_MotUpdateTime_INV1;
extern UINT32 BswCfgVal_Pwm_MotUpdateTime_INV2;
extern UINT32 BswCfgVal_Pwm_HsgUpdateTime_INV1;
extern UINT32 BswCfgVal_Pwm_HsgUpdateTime_INV2;

#endif /* #ifndef _BSWCFGPWM_H_ */

/********************************************************************************************
*                                        End of File                                        *
********************************************************************************************/
