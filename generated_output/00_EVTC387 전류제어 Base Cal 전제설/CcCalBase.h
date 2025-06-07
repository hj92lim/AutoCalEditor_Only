/*
	<파일 생성 정보>
	  * 파일 생성일 : 2025.06.06
	  * 대상 파일   : 00_EVTC387 전류제어 Base Cal 전제설
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
	@file		:	CcCalBase.h
	@brief		:	Motor Control Current calibration
	@author		:	$Author: 박주영 (6001983) $
	@date		:	$Date: 2017/01/13 11:37:37KST $
	@version	:	$Revision: 1.8 $

*/
/*=========================================================================================*/

#ifndef _CCCALBASE_H_
#define _CCCALBASE_H_

/*===========================================================================================
	INCLUDES
===========================================================================================*/
#include "common.h"
#include "BswCfgPwm.h"
#include "BswCfgRdc.h"

/*===========================================================================================
	Macros
===========================================================================================*/

/*===========================================================================================
	Defines
===========================================================================================*/

#define	POSITIVE_TO_VEHICLE_DIRECTION	1
#define	NEGATIVE_TO_VEHICLE_DIRECTION	2

#define	IDX_AD_CH_MAX_NUM			15
#define	VARIABLE_FSW_TAB_OUT_SIZE	9

#define	VAR_FSW_JNC_COMP_TAB_SIZE	3

/* 전류, 전압 센서 스케일 계산 */
#define	CUR_SENSOR_OFFSET_MOT	2048
#define	CUR_SENSOR_SCALE_MOT	CUR_SENSOR_RANGE_MOT*0.00061035
#define	HVBATT_SENSOR_OFFSET	0
#define	HVBATT_SENSOR_SCALE		(HVBATT_SENSOR_RANGE/HVBATT_SENSOR_RANGE_TYP)*0.0012207
#define	CUR_SENSOR_OFFSET_HSG	2048
#define	CUR_SENSOR_SCALE_HSG	CUR_SENSOR_RANGE_HSG*0.00061035
#define	LVBATT_SENSOR_OFFSET	LVBATT_SENSOR_RANGE_OFFSET
#define	LVBATT_SENSOR_SCALE		((LVBATT_SENSOR_RANGE-LVBATT_SENSOR_RANGE_OFFSET)/LVBATT_SENSOR_RANGE_TYP)*0.0012207

/*===========================================================================================
	Typedefs
===========================================================================================*/

/*===========================================================================================
	NVRAM data
===========================================================================================*/

/*===========================================================================================
	SAVED data
===========================================================================================*/

/*===========================================================================================
	CAL data
===========================================================================================*/

/*-------------------------------------------------------------------------------------------
	@name	: 레졸버 옵셋 관련 변수
-------------------------------------------------------------------------------------------*/
#include "section_CAL1_begin.h"
extern const FLOAT32 BswCfgCal_Rsv_DefaultOffset[TOTAL_TARGET];
extern const UINT16  BswCfgCal_Rsv_RotDir[TOTAL_TARGET];

/*-------------------------------------------------------------------------------------------
	@name	: RSPWM Test Cal
-------------------------------------------------------------------------------------------*/

#if (_SA_2STAGE_PWM_MODE == _2STG_SVPWM)
	extern const BOOL TestCal_RSPWM_Enb;

#elif (_SA_2STAGE_PWM_MODE == _2STG_RSPWM)
	extern const BOOL TestCal_RSPWM_Enb;

#else
	#error undefined _SA_2STAGE_PWM_MODE MACRO

#endif
extern const BOOL TestCal_VnCtrl_Enb;

/*-------------------------------------------------------------------------------------------
	@name	: SQPWM Regen Disable Cal
-------------------------------------------------------------------------------------------*/

#if (_SA_SQPWM_REGEN_DIS == _SQPWM_REGEN_ENB)
	extern const UINT8 CcCal_SQPWM_Mode_Regen_Disable[TOTAL_TARGET];

#elif (_SA_SQPWM_REGEN_DIS == _SQPWM_REGEN_DIS)
	extern const UINT8 CcCal_SQPWM_Mode_Regen_Disable[TOTAL_TARGET];

#else
	#error undefined _SA_SQPWM_REGEN_DIS MACRO

#endif
/*-------------------------------------------------------------------------------------------
	@name	: 원리시험 및 강제보정 용도 설계변수 리스트 모음
-------------------------------------------------------------------------------------------*/
extern const FLOAT32 CcCal_Motor_frated[TOTAL_TARGET];	// 075 Motor rated frequency[Hz] (NV/P2)

/* SWRDC ATO GAIN테스트 */
extern const UINT8       CcCal_SWRDC_GainUpdateCal[TOTAL_TARGET];
extern const signed long CcCal_SWRDC_GainUpdate_K1D[TOTAL_TARGET];
extern const signed long CcCal_SWRDC_GainUpdate_K1SCALE[TOTAL_TARGET];
extern const signed long CcCal_SWRDC_GainUpdate_K2D[TOTAL_TARGET];
extern const signed long CcCal_SWRDC_GainUpdate_K2SCALE[TOTAL_TARGET];
extern const INT32       CcCal_SWRDC_GainUpdate_NaturalFreq[TOTAL_TARGET];
extern const FLOAT32     CcCal_SWRDC_GainUpdate_DampFac[TOTAL_TARGET];

/* Toggle enable flag */
extern const UINT16 CcCal_ToggleEnb[TOTAL_TARGET];

/* 최대 샘플링 주파수 제한 */
extern const FLOAT32 CcCal_Fsamp_High_Limit[TOTAL_TARGET];

/*-------------------------------------------------------------------------------------------
	@name	: 제어 알고리즘 설계변수 중 FIX되어 바뀌지 않는것들 (추후 변경시 이동 필요)
-------------------------------------------------------------------------------------------*/

/* Init시 입력 초기값 */
extern const FLOAT32 CcCal_Motor_Ld[TOTAL_TARGET];			// 091 Motor cyclic inductance  [H] (NV/P2) //Initial시에 적용되는 초기값
extern const FLOAT32 CcCal_Motor_Lq[TOTAL_TARGET];			// 092 Motor magnetic reactance [Ω] (NV/P2) //Initial시에 적용되는 초기값
extern const FLOAT32 CcCal_Motor_Llk[TOTAL_TARGET];			// 092 Motor magnetic reactance [Ω] (NV/P2) //Initial시에 적용되는 초기값
extern const FLOAT32 CcCal_DaxisCurCtrlBW[TOTAL_TARGET];	// Initial시에 적용되는 초기값
extern const FLOAT32 CcCal_QaxisCurCtrlBW[TOTAL_TARGET];	// Initial시에 적용되는 초기값
extern const FLOAT32 CcCal_NaxisCurCtrlBW[TOTAL_TARGET];	// Initial시에 적용되는 초기값
extern const FLOAT32 CcCal_PaxisCurCtrlBW[TOTAL_TARGET];	// Initial시에 적용되는 초기값

/* 속도 관측기, SWRDC관련 */
extern const UINT16  CcCal_SWRDC_Speed_Override[TOTAL_TARGET];
extern const FLOAT32 L1;
extern const FLOAT32 L2;
extern const FLOAT32 L3;

/* 지연보상 */
extern const FLOAT32 CcCal_Cur_lag[TOTAL_TARGET];

/* 속도 기반 스위칭 주파수 보간로직(현재 토크-속도 기반으로 사용중) */
extern const FLOAT32 FSW_TAB[TOTAL_TARGET][VARIABLE_FSW_TAB_OUT_SIZE];
extern const FLOAT32 HSG_VAR_HOVMGAIN_TAB[VARIABLE_HOVM_TAB_ROW_SIZE][VARIABLE_HOVM_TAB_COL_SIZE];

/* 가변 스위칭 SPECTRUM 방식을 위한 Cal */
extern const FLOAT32 MAGINJ_TAB[TOTAL_TARGET][VARIABLE_FSW_TAB_OUT_SIZE];

/* <전류맵 입력 관련> */

/* Back-EMF Temperature Compensation */
extern const UINT8   CcCal_BETC_SetFlag[TOTAL_TARGET];
extern const FLOAT32 CcCal_BETC_CoeffLAMpm_Tmp[TOTAL_TARGET];
extern const FLOAT32 CcCal_BETC_LAMpmAt90MAP[TOTAL_TARGET];
extern const UINT32  CcCal_BETC_EndCnt[TOTAL_TARGET];
extern const FLOAT32 CcCal_BETC_DeltaTmpComp_Lmt[TOTAL_TARGET];

/* 데드타임 보상 관련 */

/* Dead Time Compensation Logic oriented by current direction */
extern const UINT8 CcCal_DeadTimeCompEnb[TOTAL_TARGET];

extern FLOAT32 CcCal_DeadTimeComp_INVIcompZCC_INV1[TOTAL_TARGET];	// 전류센서 사양과 연동
extern FLOAT32 CcCal_DeadTimeComp_INVIcompZCC_INV2[TOTAL_TARGET];	// 전류센서 사양과 연동

extern const FLOAT32 CcCal_DeadTimeComp_TdeadComp_INV1[TOTAL_TARGET];	// POWER모듈 사양과 연동
extern const FLOAT32 CcCal_DeadTimeComp_TdeadComp_INV2[TOTAL_TARGET];	// POWER모듈 사양과 연동
extern const FLOAT32 CcCal_DeadTimeComp_IcompZCC_INV1[TOTAL_TARGET];	// 전류센서 사양과 연동
extern const FLOAT32 CcCal_DeadTimeComp_IcompZCC_INV2[TOTAL_TARGET];	// 전류센서 사양과 연동

extern const INT16   CcCal_CurA_InitialOffset[TOTAL_TARGET];	// 전류센서 사양과 연동
extern const INT16   CcCal_CurB_InitialOffset[TOTAL_TARGET];	// 전류센서 사양과 연동
extern const INT16   CcCal_CurC_InitialOffset[TOTAL_TARGET];	// 전류센서 사양과 연동
extern const FLOAT32 CcCal_Cur_ScaleFactor[TOTAL_TARGET];		// 전류센서 사양과 연동

extern const UINT16  CcCal_HvBatt_InitialOffset[TOTAL_TARGET];					// 전압센서 사양과 연동
extern const FLOAT32 CcCal_HvBatt_ScaleFactor[TOTAL_TARGET];					// 전압센서 사양과 연동
extern const UINT8   CcCal_OffsetValidityChk_ZeroCurOverride[TOTAL_TARGET];

extern const FLOAT32 CcCal_LvAdToPhyOffset[TOTAL_TARGET];	// 전압센서 사양과 연동
extern const FLOAT32 CcCal_LvAdToPhySclFct[TOTAL_TARGET];	// 전압센서 사양과 연동

#if (_PWM_BURST_MODE == _UNDEFINED_OPTION)
	#error undefined _PWM_BURST_MODE MACRO (check #define!!)

#elif (_PWM_BURST_MODE == _BURST_MODE_ENABLE)
	extern const FLOAT32 CcCal_PwmOff_MotTqLvl_Max[TOTAL_TARGET];
	extern const FLOAT32 CcCal_PwmOff_MotTqLvl_Min[TOTAL_TARGET];
	extern const FLOAT32 CcCal_PwmOn_MotTqLvl_Max[TOTAL_TARGET];
	extern const FLOAT32 CcCal_PwmOn_MotTqLvl_Min[TOTAL_TARGET];

	extern const UINT32 CcCal_PwmOff_WaitTime[TOTAL_TARGET];

#elif (_PWM_BURST_MODE == _BURST_MODE_DISABLE)
	extern const FLOAT32 CcCal_PwmOff_MotTqLvl_Max[TOTAL_TARGET];
	extern const FLOAT32 CcCal_PwmOff_MotTqLvl_Min[TOTAL_TARGET];
	extern const FLOAT32 CcCal_PwmOn_MotTqLvl_Max[TOTAL_TARGET];
	extern const FLOAT32 CcCal_PwmOn_MotTqLvl_Min[TOTAL_TARGET];

	extern const UINT32 CcCal_PwmOff_WaitTime[TOTAL_TARGET];

#else
	#error undefined _PWM_BURST_MODE MACRO

#endif
#if (_VAR_DTGS_OPTION == _UNDEFINED_OPTION)
	#error undefined _VAR_DTGS_OPTION MACRO (check #define!!)

#elif (_VAR_DTGS_OPTION == _VAR_DTGS_OPTION_INCLUDED)
	extern const UINT8 CcCal_VarDTGS_Enb[TOTAL_TARGET];

#elif (_VAR_DTGS_OPTION == _VAR_DTGS_OPTION_NOT_INCLUDED)
	extern const UINT8 CcCal_VarDTGS_Enb[TOTAL_TARGET];

#else
	#error undefined _VAR_DTGS_OPTION MACRO

#endif

extern const FLOAT32 CcCal_VarDTGS_MotTqLvl1_Max_HysIn[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotTqLvl1_Min_HysIn[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotSpdLvl1_Max_HysIn[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotSpdLvl1_Min_HysIn[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotTqLvl1_Max_HysOut[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotTqLvl1_Min_HysOut[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotSpdLvl1_Max_HysOut[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotSpdLvl1_Min_HysOut[TOTAL_TARGET];

extern const FLOAT32 CcCal_VarDTGS_MotTqLvl2_Max_HysIn[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotTqLvl2_Min_HysIn[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotSpdLvl2_Max_HysIn[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotSpdLvl2_Min_HysIn[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotTqLvl2_Max_HysOut[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotTqLvl2_Min_HysOut[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotSpdLvl2_Max_HysOut[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotSpdLvl2_Min_HysOut[TOTAL_TARGET];

extern const FLOAT32 CcCal_VarDTGS_MotTqLvl3_Max_HysIn[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotTqLvl3_Min_HysIn[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotSpdLvl3_Max_HysIn[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotSpdLvl3_Min_HysIn[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotTqLvl3_Max_HysOut[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotTqLvl3_Min_HysOut[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotSpdLvl3_Max_HysOut[TOTAL_TARGET];
extern const FLOAT32 CcCal_VarDTGS_MotSpdLvl3_Min_HysOut[TOTAL_TARGET];

#include "section_CAL_end.h"

#endif /* #ifndef _CCCALBASE_H_ */

/********************************************************************************************
*                                        End of File                                        *
********************************************************************************************/
