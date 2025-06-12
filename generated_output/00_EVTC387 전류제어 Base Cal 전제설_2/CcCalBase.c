/*
	<파일 생성 정보>
	  * 파일 생성일 : 2025.06.12
	  * 대상 파일   : 00_EVTC387 전류제어 Base Cal 전제설_2.db
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
	@file		:	CcCalBase.c
	@brief		:	Motor Control Current calibration
	@author		:	$Author: 박주영 (6001983) $
	@date		:	$Date: 2017/01/13 12:36:26KST $
	@version	:	$Revision: 1.12 $

*/
/*=========================================================================================*/

/*===========================================================================================
	INCLUDES
===========================================================================================*/
#include "CcCalBase.h"
#include "BswCfgPwm.h"
#include "BswCfgRdc.h"

/*===========================================================================================
	DEFINES
===========================================================================================*/

/*===========================================================================================
	TYPE DEFINITIONS
===========================================================================================*/

/*===========================================================================================
	PARAMETERIZED MACROS
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
const FLOAT32 BswCfgCal_Rsv_DefaultOffset[TOTAL_TARGET]	= {	DEFAULT_OFFSET_MOT,	DEFAULT_OFFSET_HSG	};
const UINT16  BswCfgCal_Rsv_RotDir[TOTAL_TARGET]		= {	RESOLVER_DIRECTION_MOT,	RESOLVER_DIRECTION_HSG	};

/*-------------------------------------------------------------------------------------------
	@name	: RSPWM Test Cal
-------------------------------------------------------------------------------------------*/

#if (_SA_2STAGE_PWM_MODE == _2STG_SVPWM)
	const BOOL TestCal_RSPWM_Enb	= CLR_FLAG;

#elif (_SA_2STAGE_PWM_MODE == _2STG_RSPWM)
	const BOOL TestCal_RSPWM_Enb	= SET_FLAG;

#else
	#error undefined _SA_2STAGE_PWM_MODE MACRO

#endif
const BOOL TestCal_VnCtrl_Enb	= SET_FLAG;

/*-------------------------------------------------------------------------------------------
	@name	: SQPWM Regen Disable Cal
-------------------------------------------------------------------------------------------*/

#if (_SA_SQPWM_REGEN_DIS == _SQPWM_REGEN_ENB)
	const UINT8 CcCal_SQPWM_Mode_Regen_Disable[TOTAL_TARGET]	= {	CLR_FLAG,	CLR_FLAG	};

#elif (_SA_SQPWM_REGEN_DIS == _SQPWM_REGEN_DIS)
	const UINT8 CcCal_SQPWM_Mode_Regen_Disable[TOTAL_TARGET]	= {	SET_FLAG,	SET_FLAG	};

#else
	#error undefined _SA_SQPWM_REGEN_DIS MACRO

#endif
/*-------------------------------------------------------------------------------------------
	@name	: 원리시험 및 강제보정 용도 설계변수 리스트 모음
-------------------------------------------------------------------------------------------*/
const FLOAT32 CcCal_Motor_frated[TOTAL_TARGET]	= {	0.f,	0.f	};// 075 Motor rated frequency[Hz] (NV/P2)

/* SWRDC ATO GAIN테스트 */
const UINT8       CcCal_SWRDC_GainUpdateCal[TOTAL_TARGET]			= {	CLR_FLAG,	CLR_FLAG	};
const signed long CcCal_SWRDC_GainUpdate_K1D[TOTAL_TARGET]			= {	0.64339817*0x800000,	0.64339817*0x800000	};
const signed long CcCal_SWRDC_GainUpdate_K1SCALE[TOTAL_TARGET]		= {	7,	7	};
const signed long CcCal_SWRDC_GainUpdate_K2D[TOTAL_TARGET]			= {	0.99471843*0x800000,	0.99471843*0x800000	};
const signed long CcCal_SWRDC_GainUpdate_K2SCALE[TOTAL_TARGET]		= {	4,	4	};
const INT32       CcCal_SWRDC_GainUpdate_NaturalFreq[TOTAL_TARGET]	= {	200,	200	};
const FLOAT32     CcCal_SWRDC_GainUpdate_DampFac[TOTAL_TARGET]		= {	1.f,	1.f	};

/* Toggle enable flag */
const UINT16 CcCal_ToggleEnb[TOTAL_TARGET]	= {	CLR_FLAG,	CLR_FLAG	};

/* 최대 샘플링 주파수 제한 */
const FLOAT32 CcCal_Fsamp_High_Limit[TOTAL_TARGET]	= {	19800.f,	19700.f	};

/*-------------------------------------------------------------------------------------------
	@name	: 제어 알고리즘 설계변수 중 FIX되어 바뀌지 않는것들 (추후 변경시 이동 필요)
-------------------------------------------------------------------------------------------*/

/* Init시 입력 초기값 */
const FLOAT32 CcCal_Motor_Ld[TOTAL_TARGET]			= {	0.00016f,	0.0002f	};	// 091 Motor cyclic inductance  [H] (NV/P2) //Initial시에 적용되는 초기값
const FLOAT32 CcCal_Motor_Lq[TOTAL_TARGET]			= {	0.00027f,	0.0004f	};	// 092 Motor magnetic reactance [Ω] (NV/P2) //Initial시에 적용되는 초기값
const FLOAT32 CcCal_Motor_Llk[TOTAL_TARGET]			= {	0.003f,	0.0003f	};		// 092 Motor magnetic reactance [Ω] (NV/P2) //Initial시에 적용되는 초기값
const FLOAT32 CcCal_DaxisCurCtrlBW[TOTAL_TARGET]	= {	350.f,	350.f	};		// Initial시에 적용되는 초기값
const FLOAT32 CcCal_QaxisCurCtrlBW[TOTAL_TARGET]	= {	350.f,	350.f	};		// Initial시에 적용되는 초기값
const FLOAT32 CcCal_NaxisCurCtrlBW[TOTAL_TARGET]	= {	350.f,	350.f	};		// Initial시에 적용되는 초기값
const FLOAT32 CcCal_PaxisCurCtrlBW[TOTAL_TARGET]	= {	350.f,	350.f	};		// Initial시에 적용되는 초기값

/* 속도 관측기, SWRDC관련 */
const UINT16  CcCal_SWRDC_Speed_Override[TOTAL_TARGET]	= {	CLR_FLAG,	CLR_FLAG	};
const FLOAT32 L1										= 3.f * (400.f * PI * 0.3f);
const FLOAT32 L2										= 3.f * (400.f * PI * 0.3f) * (400.f * PI * 0.3f);
const FLOAT32 L3										= (400.f * PI * 0.3f) * (400.f * PI * 0.3f) * (400.f * PI * 0.3f);

/* 지연보상 */
const FLOAT32 CcCal_Cur_lag[TOTAL_TARGET]	= {	0.f,	0.f	};

/* 속도 기반 스위칭 주파수 보간로직(현재 토크-속도 기반으로 사용중) */
const FLOAT32 FSW_TAB[TOTAL_TARGET][VARIABLE_FSW_TAB_OUT_SIZE] =
{
/*		   Idx,    		0,		1,		2,		3,		4,		5,		6,		7,		8		*/
	{	/* MOT   */		4000.f,	4000.f,	4000.f,	4000.f,	4000.f,	4000.f,	4000.f,	4000.f,	4000.f	},	// 설계(더블용 MOT)
	{	/* HSG   */		4000.f,	4000.f,	4000.f,	4000.f,	4000.f,	4000.f,	4000.f,	4000.f,	4000.f	}	// 설계(더블용 HSG)
};

const FLOAT32 HSG_VAR_HOVMGAIN_TAB[VARIABLE_HOVM_TAB_ROW_SIZE][VARIABLE_HOVM_TAB_COL_SIZE] =
{
/*		   Idx,                  	0,	1,		2,		3,		4,		5,		6,		7,		8,		9,		10		*/
/*		            Tq/Delwrpm,  	0,	400,	800,	1200,	1600,	2000,	2400,	2800,	3200,	3600,	4000	*/
	{	/* 0,       90         */	1.f,1.f,	1.f,	1.f,	1.f,	1.f,	1.f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 1,       80         */	1.f,1.f,	1.f,	1.f,	1.f,	1.f,	1.f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 2,       70         */	1.f,1.f,	1.f,	1.f,	1.f,	1.f,	1.f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 3,       60         */	1.f,1.f,	1.f,	1.f,	1.f,	1.f,	1.f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 4,       50         */	1.f,1.f,	1.f,	1.f,	1.f,	1.f,	1.f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 5,       40         */	1.f,1.f,	1.f,	1.f,	1.f,	1.f,	1.f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 6,       30         */	1.f,1.f,	1.f,	1.f,	1.f,	1.f,	1.f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 7,       20         */	1.f,1.f,	1.f,	1.f,	1.f,	1.f,	1.f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 8,       10         */	1.f,1.f,	1.f,	1.f,	1.f,	1.f,	1.f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 9,       0          */	1.f,1.f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 10,      -10        */	1.f,1.f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 11,      -20        */	1.f,1.f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 12,      -30        */	1.f,1.f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 13,      -40        */	1.f,1.f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 14,      -50        */	1.f,1.f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 15,      -60        */	1.f,1.f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 16,      -70        */	1.f,1.f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 17,      -80        */	1.f,1.f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f	},
	{	/* 18,      -90        */	1.f,1.f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f,	1.1f	}
};

/* 가변 스위칭 SPECTRUM 방식을 위한 Cal */
const FLOAT32 MAGINJ_TAB[TOTAL_TARGET][VARIABLE_FSW_TAB_OUT_SIZE] =
{
/*		   Idx,    		0,	1,	2,	3,	4,	5,	6,	7,	8	*/
	{	/* MOT   */		0.f,0.f,0.f,0.f,0.f,0.f,0.f,0.f,0.f	},	// 설계(더블용 MOT)
	{	/* HSG   */		0.f,0.f,0.f,0.f,0.f,0.f,0.f,0.f,0.f	}	// 설계(더블용 HSG)
};

/* <전류맵 입력 관련> */

/* Back-EMF Temperature Compensation */
const UINT8   CcCal_BETC_SetFlag[TOTAL_TARGET]			= {	CLR_FLAG,	CLR_FLAG	};
const FLOAT32 CcCal_BETC_CoeffLAMpm_Tmp[TOTAL_TARGET]	= {	0.001f,	0.001f	};
const FLOAT32 CcCal_BETC_LAMpmAt90MAP[TOTAL_TARGET]		= {	0.052f,	0.052f	};
const UINT32  CcCal_BETC_EndCnt[TOTAL_TARGET]			= {	3,	3	};
const FLOAT32 CcCal_BETC_DeltaTmpComp_Lmt[TOTAL_TARGET]	= {	40.f,	40.f	};

/* 데드타임 보상 관련 */

/* Dead Time Compensation Logic oriented by current direction */
const UINT8 CcCal_DeadTimeCompEnb[TOTAL_TARGET]	= {	SET_FLAG,	SET_FLAG	};

FLOAT32 CcCal_DeadTimeComp_INVIcompZCC_INV1[TOTAL_TARGET]	= {	1.f/(CUR_SENSOR_RANGE_MOT*0.05f),	1.f/(CUR_SENSOR_RANGE_HSG*0.05f)	};// 전류센서 사양과 연동
FLOAT32 CcCal_DeadTimeComp_INVIcompZCC_INV2[TOTAL_TARGET]	= {	1.f/(CUR_SENSOR_RANGE_MOT*0.05f),	1.f/(CUR_SENSOR_RANGE_HSG*0.05f)	};// 전류센서 사양과 연동

const FLOAT32 CcCal_DeadTimeComp_TdeadComp_INV1[TOTAL_TARGET]	= {	(BSWCFGPWM_MOT_INV1_DEADTIME-100.f)*0.000000001f,	(BSWCFGPWM_HSG_INV1_DEADTIME-100.f)*0.000000001f	};// POWER모듈 사양과 연동
const FLOAT32 CcCal_DeadTimeComp_TdeadComp_INV2[TOTAL_TARGET]	= {	(BSWCFGPWM_MOT_INV2_DEADTIME-100.f)*0.000000001f,	(BSWCFGPWM_HSG_INV2_DEADTIME-100.f)*0.000000001f	};// POWER모듈 사양과 연동
const FLOAT32 CcCal_DeadTimeComp_IcompZCC_INV1[TOTAL_TARGET]	= {	(CUR_SENSOR_RANGE_MOT*0.05f),	(CUR_SENSOR_RANGE_HSG*0.05f)	};										// 전류센서 사양과 연동
const FLOAT32 CcCal_DeadTimeComp_IcompZCC_INV2[TOTAL_TARGET]	= {	(CUR_SENSOR_RANGE_MOT*0.05f),	(CUR_SENSOR_RANGE_HSG*0.05f)	};										// 전류센서 사양과 연동

const INT16   CcCal_CurA_InitialOffset[TOTAL_TARGET]	= {	CUR_SENSOR_OFFSET_MOT,	CUR_SENSOR_OFFSET_HSG	};	// 전류센서 사양과 연동
const INT16   CcCal_CurB_InitialOffset[TOTAL_TARGET]	= {	CUR_SENSOR_OFFSET_MOT,	CUR_SENSOR_OFFSET_HSG	};	// 전류센서 사양과 연동
const INT16   CcCal_CurC_InitialOffset[TOTAL_TARGET]	= {	CUR_SENSOR_OFFSET_MOT,	CUR_SENSOR_OFFSET_HSG	};	// 전류센서 사양과 연동
const FLOAT32 CcCal_Cur_ScaleFactor[TOTAL_TARGET]		= {	CUR_SENSOR_SCALE_MOT,	CUR_SENSOR_SCALE_HSG	};	// 전류센서 사양과 연동

const UINT16  CcCal_HvBatt_InitialOffset[TOTAL_TARGET]				= {	HVBATT_SENSOR_OFFSET,	HVBATT_SENSOR_OFFSET	};	// 전압센서 사양과 연동
const FLOAT32 CcCal_HvBatt_ScaleFactor[TOTAL_TARGET]				= {	HVBATT_SENSOR_SCALE,	HVBATT_SENSOR_SCALE	};		// 전압센서 사양과 연동
const UINT8   CcCal_OffsetValidityChk_ZeroCurOverride[TOTAL_TARGET]	= {	SET_FLAG,	SET_FLAG	};

const FLOAT32 CcCal_LvAdToPhyOffset[TOTAL_TARGET]	= {	LVBATT_SENSOR_OFFSET,	LVBATT_SENSOR_OFFSET	};	// 전압센서 사양과 연동
const FLOAT32 CcCal_LvAdToPhySclFct[TOTAL_TARGET]	= {	LVBATT_SENSOR_SCALE,	LVBATT_SENSOR_SCALE	};		// 전압센서 사양과 연동

#if (_PWM_BURST_MODE == _UNDEFINED_OPTION)
	#error undefined _PWM_BURST_MODE MACRO (check #define!!)

#elif (_PWM_BURST_MODE == _BURST_MODE_ENABLE)
	const FLOAT32 CcCal_PwmOff_MotTqLvl_Max[TOTAL_TARGET]	= {	1.f,	0.f	};
	const FLOAT32 CcCal_PwmOff_MotTqLvl_Min[TOTAL_TARGET]	= {	0.f,	0.f	};
	const FLOAT32 CcCal_PwmOn_MotTqLvl_Max[TOTAL_TARGET]	= {	2.f,	0.f	};
	const FLOAT32 CcCal_PwmOn_MotTqLvl_Min[TOTAL_TARGET]	= {	0.f,	0.f	};

	const UINT32 CcCal_PwmOff_WaitTime[TOTAL_TARGET]	= {	100,	100	};

#elif (_PWM_BURST_MODE == _BURST_MODE_DISABLE)
	const FLOAT32 CcCal_PwmOff_MotTqLvl_Max[TOTAL_TARGET]	= {	0.f,	0.f	};
	const FLOAT32 CcCal_PwmOff_MotTqLvl_Min[TOTAL_TARGET]	= {	0.f,	0.f	};
	const FLOAT32 CcCal_PwmOn_MotTqLvl_Max[TOTAL_TARGET]	= {	0.f,	0.f	};
	const FLOAT32 CcCal_PwmOn_MotTqLvl_Min[TOTAL_TARGET]	= {	0.f,	0.f	};

	const UINT32 CcCal_PwmOff_WaitTime[TOTAL_TARGET]	= {	100,	100	};

#else
	#error undefined _PWM_BURST_MODE MACRO

#endif
#if (_VAR_DTGS_OPTION == _UNDEFINED_OPTION)
	#error undefined _VAR_DTGS_OPTION MACRO (check #define!!)

#elif (_VAR_DTGS_OPTION == _VAR_DTGS_OPTION_INCLUDED)
	const UINT8 CcCal_VarDTGS_Enb[TOTAL_TARGET]	= {	SET_FLAG,	SET_FLAG	};

#elif (_VAR_DTGS_OPTION == _VAR_DTGS_OPTION_NOT_INCLUDED)
	const UINT8 CcCal_VarDTGS_Enb[TOTAL_TARGET]	= {	CLR_FLAG,	CLR_FLAG	};

#else
	#error undefined _VAR_DTGS_OPTION MACRO

#endif

const FLOAT32 CcCal_VarDTGS_MotTqLvl1_Max_HysIn[TOTAL_TARGET]	= {	80.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotTqLvl1_Min_HysIn[TOTAL_TARGET]	= {	-45.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotSpdLvl1_Max_HysIn[TOTAL_TARGET]	= {	8200.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotSpdLvl1_Min_HysIn[TOTAL_TARGET]	= {	866.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotTqLvl1_Max_HysOut[TOTAL_TARGET]	= {	88.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotTqLvl1_Min_HysOut[TOTAL_TARGET]	= {	-50.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotSpdLvl1_Max_HysOut[TOTAL_TARGET]	= {	8500.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotSpdLvl1_Min_HysOut[TOTAL_TARGET]	= {	709.f,	0.f	};

const FLOAT32 CcCal_VarDTGS_MotTqLvl2_Max_HysIn[TOTAL_TARGET]	= {	0.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotTqLvl2_Min_HysIn[TOTAL_TARGET]	= {	0.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotSpdLvl2_Max_HysIn[TOTAL_TARGET]	= {	0.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotSpdLvl2_Min_HysIn[TOTAL_TARGET]	= {	0.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotTqLvl2_Max_HysOut[TOTAL_TARGET]	= {	0.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotTqLvl2_Min_HysOut[TOTAL_TARGET]	= {	0.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotSpdLvl2_Max_HysOut[TOTAL_TARGET]	= {	0.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotSpdLvl2_Min_HysOut[TOTAL_TARGET]	= {	0.f,	0.f	};

const FLOAT32 CcCal_VarDTGS_MotTqLvl3_Max_HysIn[TOTAL_TARGET]	= {	0.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotTqLvl3_Min_HysIn[TOTAL_TARGET]	= {	0.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotSpdLvl3_Max_HysIn[TOTAL_TARGET]	= {	0.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotSpdLvl3_Min_HysIn[TOTAL_TARGET]	= {	0.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotTqLvl3_Max_HysOut[TOTAL_TARGET]	= {	0.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotTqLvl3_Min_HysOut[TOTAL_TARGET]	= {	0.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotSpdLvl3_Max_HysOut[TOTAL_TARGET]	= {	0.f,	0.f	};
const FLOAT32 CcCal_VarDTGS_MotSpdLvl3_Min_HysOut[TOTAL_TARGET]	= {	0.f,	0.f	};

#include "section_CAL_end.h"

/********************************************************************************************
*                                        End of File                                        *
********************************************************************************************/
