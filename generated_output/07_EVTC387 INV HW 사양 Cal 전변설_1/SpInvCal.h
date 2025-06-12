/*
	<파일 생성 정보>
	  * 파일 생성일 : 2025.06.12
	  * 대상 파일   : 07_EVTC387 INV HW 사양 Cal 전변설_1.db
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
	@file		:	SpInvCal.h
	@brief		:	
	@author		:	JY.Park
	@date		:	

*/
/*=========================================================================================*/

#ifndef _SPINVCAL_H_
#define _SPINVCAL_H_

/*===========================================================================================
	INCLUDES
===========================================================================================*/
#include "common.h"

/*===========================================================================================
	Macros
===========================================================================================*/

/*===========================================================================================
	Defines
===========================================================================================*/
#define	VAR_FSW_JNC_COMP_TAB_SIZE	3

#define	HILL_HOLD_SPEED_SIZE		3
#define	HILL_HOLD_TRQ_SIZE			5
#define	INV_TMP_TAB_SIZE			22
#define	JNV_LIFE_CYCLE_TAB_SIZE		24
#define	EWP_TAB_COL_SIZE			4
#define	RAD_TAB_COL_SIZE			5
#define	RAD_TAB_ROW_SIZE			3

/*-------------------------------------------------------------------------------------------
	@name	: INV UVW 상순 SPEC
-------------------------------------------------------------------------------------------*/
#define	ABC_TO_UVW	1	// 보드-인버터 터미널 간 UVW 상순 사양 (A-U, B-V, C-W)
#define	ABC_TO_WVU	2	// 보드-인버터 터미널 간 UVW 상순 사양 (A-W, B-V, C-U)
#define	A_TO_INV1	1	// 보드-인버터 터미널 간 보드-인버터12 연결 사양 (A-U/W)
#define	A_TO_INV2	2	// 보드-인버터 터미널 간 보드-인버터12 연결 사양 (A-NU/NW)

/*===========================================================================================
	Typedefs
===========================================================================================*/

/*===========================================================================================
	DEFINES
===========================================================================================*/
/*-------------------------------------------------------------------------------------------
	@name	: GATE IC사양에 따른 구분
-------------------------------------------------------------------------------------------*/

#if (_GATE_IC_TYPE == _UNDEFINED_OPTION)
	#error undefined _GATE_IC_TYPE MACRO (check #define!!)


#elif (_GATE_IC_TYPE == _GATE_IC_TYPE_1)
	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_INV1_MIN_WIDTH	1	// 단위 [ns]
	#define	BSWCFGPWM_MOT_INV2_MIN_WIDTH	1	// 단위 [ns]
	#define	BSWCFGPWM_MOT_ASAC_EDGE_OFFSET	0	// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_HSG_INV1_MIN_WIDTH	1	// 단위 [ns]
	#define	BSWCFGPWM_HSG_INV2_MIN_WIDTH	1	// 단위 [ns]
	#define	BSWCFGPWM_HSG_ASAC_EDGE_OFFSET	0	// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

#elif (_GATE_IC_TYPE == _GATE_IC_TYPE_2)
	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_INV1_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_INV2_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_ASAC_EDGE_OFFSET	3000	// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_HSG_INV1_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_HSG_INV2_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_HSG_ASAC_EDGE_OFFSET	3000	// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

#elif (_GATE_IC_TYPE == _GATE_IC_TYPE_3)
	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_INV1_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_INV2_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_ASAC_EDGE_OFFSET	0		// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_HSG_INV1_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_HSG_INV2_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_HSG_ASAC_EDGE_OFFSET	0		// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

#elif (_GATE_IC_TYPE == _GATE_IC_TYPE_4)
	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_INV1_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_INV2_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_ASAC_EDGE_OFFSET	3000	// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_HSG_INV1_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_HSG_INV2_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_HSG_ASAC_EDGE_OFFSET	3000	// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

#elif (_GATE_IC_TYPE == _GATE_IC_TYPE_5)
	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_INV1_MIN_WIDTH	4000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_INV2_MIN_WIDTH	4000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_ASAC_EDGE_OFFSET	0		// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_HSG_INV1_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_HSG_INV2_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_HSG_ASAC_EDGE_OFFSET	0		// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

#elif (_GATE_IC_TYPE == _GATE_IC_TYPE_6)
	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_INV1_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_INV2_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_ASAC_EDGE_OFFSET	2600	// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_HSG_INV1_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_HSG_INV2_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_HSG_ASAC_EDGE_OFFSET	0		// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

#elif (_GATE_IC_TYPE == _GATE_IC_TYPE_7)
	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_INV1_MIN_WIDTH	300		// 단위 [ns]
	#define	BSWCFGPWM_MOT_INV2_MIN_WIDTH	300		// 단위 [ns]
	#define	BSWCFGPWM_MOT_ASAC_EDGE_OFFSET	390		// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_HSG_INV1_MIN_WIDTH	300		// 단위 [ns]
	#define	BSWCFGPWM_HSG_INV2_MIN_WIDTH	300		// 단위 [ns]
	#define	BSWCFGPWM_HSG_ASAC_EDGE_OFFSET	390		// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

#elif (_GATE_IC_TYPE == _GATE_IC_TYPE_8_NV74_TCAR)
	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_INV1_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_INV2_MIN_WIDTH	3000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_ASAC_EDGE_OFFSET	390		// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_HSG_INV1_MIN_WIDTH	300		// 단위 [ns]
	#define	BSWCFGPWM_HSG_INV2_MIN_WIDTH	300		// 단위 [ns]
	#define	BSWCFGPWM_HSG_ASAC_EDGE_OFFSET	390		// DSC용 전류샘플링 및 각외삽시점 지연 (PWM LOW CENTER대비)

#else
	#error undefined _GATE_IC_TYPE MACRO

#endif
/*-------------------------------------------------------------------------------------------
	@name	: 파워 모듈 및 회로에 의한 사양 구분
-------------------------------------------------------------------------------------------*/

#if (_POWER_MODULE_TYPE == _UNDEFINED_OPTION)
	#error undefined POWER_MODULE_TYPE MACRO (check #define!!)

#elif (_POWER_MODULE_TYPE == _PM_CASE_TYPE)		// **MULTI의 경우 Deadtime 이원화 되지 않으면 모터와 같게 작업되어있음. '20. 06.02 J.M. YU
	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_INV1_DEADTIME		2200	// 단위 [ns]
	#define	BSWCFGPWM_MOT_INV2_DEADTIME		2200	// 단위 [ns]

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_MOT_DEADTIME_MULTI	2200	// 단위 [ns]

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_HSG_INV1_DEADTIME		2200	// 단위 [ns]
	#define	BSWCFGPWM_HSG_INV2_DEADTIME		2200	// 단위 [ns]

#elif (_POWER_MODULE_TYPE == _PM_DSC_TYPE_1)	// **MULTI의 경우 Deadtime 이원화 되지 않으면 모터와 같게 작업되어있음. '20. 06.02 J.M. YU
	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_INV1_DEADTIME		2500	// 단위 [ns]
	#define	BSWCFGPWM_MOT_INV2_DEADTIME		2500	// 단위 [ns]

	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_DEADTIME_MULTI	2500	// 단위 [ns]

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_HSG_INV1_DEADTIME		2500	// 단위 [ns]
	#define	BSWCFGPWM_HSG_INV2_DEADTIME		2500	// 단위 [ns]

#elif (_POWER_MODULE_TYPE == _PM_DSC_TYPE_2)	// **MULTI의 경우 Deadtime 이원화 되지 않으면 모터와 같게 작업되어있음. '20. 06.02 J.M. YU
	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_INV1_DEADTIME		4000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_INV2_DEADTIME		4000	// 단위 [ns]

	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_DEADTIME_MULTI	4000	// 단위 [ns]

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_HSG_INV1_DEADTIME		4000
	#define	BSWCFGPWM_HSG_INV2_DEADTIME		4000	// 단위 [ns]

#elif (_POWER_MODULE_TYPE == _PM_HP_DRIVE_TYPE)		// **MULTI의 경우 Deadtime 이원화 되지 않으면 모터와 같게 작업되어있음. '20. 06.02 J.M. YU
	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_INV1_DEADTIME		2000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_INV2_DEADTIME		2000	// 단위 [ns]

	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_DEADTIME_MULTI	4000	// 단위 [ns]

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_HSG_INV1_DEADTIME		2000	// 단위 [ns]
	#define	BSWCFGPWM_HSG_INV2_DEADTIME		2000	// 단위 [ns]

#elif (_POWER_MODULE_TYPE == _PM_CVeGT_TYPE)	// **MULTI의 경우 Deadtime 이원화 되지 않으면 모터와 같게 작업되어있음. '20. 06.02 J.M. YU
	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_INV1_DEADTIME		2000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_INV2_DEADTIME		4000	// 단위 [ns]

	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_DEADTIME_MULTI	4000	// 단위 [ns]

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_HSG_INV1_DEADTIME		2000	// 단위 [ns]
	#define	BSWCFGPWM_HSG_INV2_DEADTIME		2000	// 단위 [ns]

#elif (_POWER_MODULE_TYPE == _PM_NV74_TYPE)		// **MULTI의 경우 Deadtime 이원화 되지 않으면 모터와 같게 작업되어있음. '20. 06.02 J.M. YU
	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_INV1_DEADTIME		2000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_INV2_DEADTIME		4000	// 단위 [ns]

	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_DEADTIME_MULTI	4000	// 단위 [ns]

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_HSG_INV1_DEADTIME		2000	// 단위 [ns]
	#define	BSWCFGPWM_HSG_INV2_DEADTIME		2000	// 단위 [ns]

#elif (_POWER_MODULE_TYPE == _PM_MV_TYPE)	// **MULTI의 경우 Deadtime 이원화 되지 않으면 모터와 같게 작업되어있음. '20. 06.02 J.M. YU
	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_INV1_DEADTIME		2000	// 단위 [ns]
	#define	BSWCFGPWM_MOT_INV2_DEADTIME		4000	// 단위 [ns]

	/* MOTOR PWM Configuration */
	#define	BSWCFGPWM_MOT_DEADTIME_MULTI	2000	// 단위 [ns]

	/* HSG PWM Configuration */
	#define	BSWCFGPWM_HSG_INV1_DEADTIME		2000	// 단위 [ns]
	#define	BSWCFGPWM_HSG_INV2_DEADTIME		2000	// 단위 [ns]

#else
	#error undefined _POWER_MODULE_TYPE MACRO

#endif
/*-------------------------------------------------------------------------------------------
	@name	: _MOT_CUR_SENSOR_TYPE 사양에 따라 변경되는 Cal
-------------------------------------------------------------------------------------------*/

#if (_MOT_CUR_SENSOR_TYPE == _UNDEFINED_OPTION)

	#error undefined _MOT_CUR_SENSOR_TYPE MACRO (check #define!!)


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_400A_SCALE_HALL)

	#define	CUR_SENSOR_RANGE_MOT	400		// 2.5V 센터 기준 4.5V 해당 전류 값


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_400A_SCALE_SHUNT_TYPE1)

	#define	CUR_SENSOR_RANGE_MOT	400		// 2.5V 센터 기준 4.5V 해당 전류 값


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_500A_SCALE_SHUNT_TYPE1)

	#define	CUR_SENSOR_RANGE_MOT	500		// 2.5V 센터 기준 4.5V 해당 전류 값


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_600A_SCALE_SHUNT_TYPE1)

	#define	CUR_SENSOR_RANGE_MOT	588.2353	// 2.5V 센터 기준 4.5V 해당 전류 값


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_400A_SCALE_SHUNT_TYPE2)

	#define	CUR_SENSOR_RANGE_MOT	394.2829	// 2.5V 센터 기준 4.5V 해당 전류 값 (400A@4.529V)


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_500A_SCALE_HALL)

	#define	CUR_SENSOR_RANGE_MOT	500		// 2.5V 센터 기준 4.5V 해당 전류 값


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_700A_SCALE_HALL)

	#define	CUR_SENSOR_RANGE_MOT	700		// 2.5V 센터 기준 4.5V 해당 전류 값


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_700A_SCALE_SHUNT_0)

	#define	CUR_SENSOR_RANGE_MOT	700		// 2.5V 센터 기준 4.5V 해당 전류 값


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_850A_SCALE_HALL)

	#define	CUR_SENSOR_RANGE_MOT	850		// 2.5V 센터 기준 4.5V 해당 전류 값


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_850A_SCALE_HALL_FOR_HPV)

	#define	CUR_SENSOR_RANGE_MOT	850		// 2.5V 센터 기준 4.5V 해당 전류 값


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_1000A_SCALE_HALL)

	#define	CUR_SENSOR_RANGE_MOT	1000	// 2.5V 센터 기준 4.5V 해당 전류 값


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_1300A_SCALE_HALL)

	#define	CUR_SENSOR_RANGE_MOT	1300	// 2.5V 센터 기준 4.5V 해당 전류 값


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_1100A_SCALE_HALL)

	#define	CUR_SENSOR_RANGE_MOT	1100	// 2.5V 센터 기준 4.5V 해당 전류 값


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_1500A_SCALE_HALL)

	#define	CUR_SENSOR_RANGE_MOT	1500	// 2.5V 센터 기준 4.5V 해당 전류 값


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_700A_SCALE_CORELESS)

	#define	CUR_SENSOR_RANGE_MOT	833.3333	// 2.5V 센터 기준 4.5V 해당 전류 값(700A@4.18V)

#elif (_MOT_CUR_SENSOR_TYPE == _MOT_700A_SCALE_CORELESS_TYPE2)

	#define	CUR_SENSOR_RANGE_MOT	909.5043	// 2.5V 센터 기준 4.5V 해당 전류 값(700A@4.039V) 보그워너 제작 오류


#elif (_MOT_CUR_SENSOR_TYPE == _MOT_650A_SCALE_CORELESS_TYPE)

	#define	CUR_SENSOR_RANGE_MOT	682.0567	// 2.5V 센터 기준 4.5V 해당 전류 값(650A@4.406V)


#else
	#error undefined _MOT_CUR_SENSOR_TYPE MACRO

#endif
#include "section_CAL_end.h"

#endif /* #ifndef _SPINVCAL_H_ */

/********************************************************************************************
*                                        End of File                                        *
********************************************************************************************/
