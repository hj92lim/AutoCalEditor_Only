/*
	<파일 생성 정보>
	  * 파일 생성일 : 2025.06.08
	  * 대상 파일   : 01_EVTC387 프로젝트별 CcCal 사양.db
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
	@file		:	CcCalPrjCfg.h
	@brief		:	
	@author		:	JY.Park
	@date		:	

*/
/*=========================================================================================*/

#ifndef _CCCALPRJCFG_H_
#define _CCCALPRJCFG_H_

/*===========================================================================================
	INCLUDES
===========================================================================================*/
#include "CcCalPrjCfg.h"

/*===========================================================================================
	DEFINES
===========================================================================================*/

#if (_PROJECT_NAME == _MV_RWD_PROJ)

	/*-------------------------------------------------------------------------------------------
		@name	: 출력 타입에 의한 사양 구분
	-------------------------------------------------------------------------------------------*/
	
	#if (_PERFORMANCE_TYPE == _STANDARD_VERSION || _PERFORMANCE_TYPE == _PERFORMANCE_VERSION || _PERFORMANCE_TYPE == _LONG_RANGE_VERSION || _PERFORMANCE_TYPE == _eM_160kW_VERSION || _PERFORMANCE_TYPE == _eM_200kW_VERSION || _PERFORMANCE_TYPE == _eM_250kW_VERSION)
		/*-------------------------------------------------------------------------------------------
			@name	: 파워 모듈 및 회로에 의한 사양 구분
		-------------------------------------------------------------------------------------------*/
	
		#if (_DEVELOPMENT_PHASE == _TCAR_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_100							// MV/RWD/160kW/TCAR
			#define	_12SMP_COND				_12SMP_OFF							// MV/RWD/160kW/TCAR
			#define	_RPWM_COND				_RPWM_OFF							// MV/RWD/160kW/TCAR
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF					// MV/RWD/160kW/TCAR
			#define	_SW_RDC_SETTING			_MV_EV_TCAR_REAR_SW_RDC				// MV/RWD/160kW/TCAR
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE					// MV/RWD/160kW/TCAR
			#define	_FSW_FSAMP_FREQ			_7kHz_DOUBLE						// MV/RWD/160kW/TCAR
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_6_5kHz_DOUBLE					// MV/RWD/160kW/TCAR
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL				// MV/RWD/160kW/TCAR
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG						// MV/RWD/160kW/TCAR
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON						// MV/RWD/160kW/TCAR
			#define	_CUR_MAP_VERSION		_MV_TCAR_REAR_CUR_MAP				// MV/RWD/160kW/TCAR
			#define	_MOTOR_TYPE				_MV_TCAR_REAR_MOTOR					// MV/RWD/160kW/TCAR
			#define	_POWER_CAL_VERSION		_MV_EV_TCAR_REAR_154KW_POWER_CAL	// MV/RWD/160kW/TCAR
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4						// MV/RWD/160kW/TCAR
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_TCAR_REAR_TQ_COMP_CAL	// MV/RWD/160kW/TCAR
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_TCAR_REAR_TQ_COMP_CAL	// MV/RWD/160kW/TCAR
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
		#elif (_DEVELOPMENT_PHASE == _PROTO_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_103							// MV/RWD/160kW/PROTO
			#define	_12SMP_COND				_12SMP_OFF							// MV/RWD/160kW/PROTO
			#define	_RPWM_COND				_RPWM_01_03_ON						// MV/RWD/160kW/PROTO
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF					// MV/RWD/160kW/PROTO
			#define	_SW_RDC_SETTING			_MV_EV_PROTO_REAR_SW_RDC			// MV/RWD/160kW/PROTO
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE					// MV/RWD/160kW/PROTO
			#define	_FSW_FSAMP_FREQ			_12kHz_SINGLE_ALL					// MV/RWD/160kW/PROTO
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_6_5kHz_DOUBLE					// MV/RWD/160kW/PROTO
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL				// MV/RWD/160kW/PROTO
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG						// MV/RWD/160kW/PROTO
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON						// MV/RWD/160kW/PROTO
			#define	_CUR_MAP_VERSION		_MV_PROTO_REAR_CUR_MAP				// MV/RWD/160kW/PROTO
			#define	_MOTOR_TYPE				_MV_PROTO_REAR_MOTOR				// MV/RWD/160kW/PROTO
			#define	_POWER_CAL_VERSION		_MV_EV_PROTO_REAR_160KW_POWER_CAL	// MV/RWD/160kW/PROTO
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4						// MV/RWD/160kW/PROTO
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_PROTO_REAR_TQ_COMP_CAL	// MV/RWD/160kW/PROTO
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_PROTO_REAR_TQ_COMP_CAL	// MV/RWD/160kW/PROTO
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
		#elif (_DEVELOPMENT_PHASE == _MASTER_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_103							// MV/RWD/160kW/MASTER
			#define	_12SMP_COND				_12SMP_OFF							// MV/RWD/160kW/MASTER
			#define	_RPWM_COND				_RPWM_01_03_ON						// MV/RWD/160kW/MASTER
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF					// MV/RWD/160kW/MASTER
			#define	_SW_RDC_SETTING			_MV_EV_PROTO_REAR_SW_RDC			// MV/RWD/160kW/MASTER
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE					// MV/RWD/160kW/MASTER
			#define	_FSW_FSAMP_FREQ			_12kHz_SINGLE_ALL					// MV/RWD/160kW/MASTER
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_12kHz_SINGLE_ALL				// MV/RWD/160kW/MASTER
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL				// MV/RWD/160kW/MASTER
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG						// MV/RWD/160kW/MASTER
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON						// MV/RWD/160kW/MASTER
			#define	_CUR_MAP_VERSION		_MV_PROTO_REAR_CUR_MAP				// MV/RWD/160kW/MASTER
			#define	_MOTOR_TYPE				_MV_PROTO_REAR_MOTOR				// MV/RWD/160kW/MASTER
			#define	_POWER_CAL_VERSION		_MV_EV_PROTO_REAR_160KW_POWER_CAL	// MV/RWD/160kW/MASTER
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4						// MV/RWD/160kW/MASTER
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_PROTO_REAR_TQ_COMP_CAL	// MV/RWD/160kW/MASTER
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_PROTO_REAR_TQ_COMP_CAL	// MV/RWD/160kW/MASTER
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
		#elif (_DEVELOPMENT_PHASE == _PILOT_1_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_103							// MV/RWD/160kW/PILOT_1
			#define	_12SMP_COND				_12SMP_OFF							// MV/RWD/160kW/PILOT_1
			#define	_RPWM_COND				_RPWM_01_03_ON						// MV/RWD/160kW/PILOT_1
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF					// MV/RWD/160kW/PILOT_1
			#define	_SW_RDC_SETTING			_MV_EV_P1_REAR_SW_RDC				// MV/RWD/160kW/PILOT_1
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE					// MV/RWD/160kW/PILOT_1
			#define	_FSW_FSAMP_FREQ			_12kHz_SINGLE_ALL					// MV/RWD/160kW/PILOT_1
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_12kHz_SINGLE_ALL				// MV/RWD/160kW/PILOT_1
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL				// MV/RWD/160kW/PILOT_1
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG						// MV/RWD/160kW/PILOT_1
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON						// MV/RWD/160kW/PILOT_1
			#define	_CUR_MAP_VERSION		_MV_PROTO_REAR_CUR_MAP				// MV/RWD/160kW/PILOT_1
			#define	_MOTOR_TYPE				_MV_P2_REAR_MOTOR					// MV/RWD/160kW/PILOT_1
			#define	_POWER_CAL_VERSION		_MV_EV_PROTO_REAR_160KW_POWER_CAL	// MV/RWD/160kW/PILOT_1
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4						// MV/RWD/160kW/PILOT_1
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MVa_EV_P1_REAR_TQ_COMP_CAL		// MV/RWD/160kW/PILOT_1
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_P1_REAR_TQ_COMP_CAL	// MV/RWD/160kW/PILOT_1
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
		#elif (_DEVELOPMENT_PHASE == _PILOT_2_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_103							// MV/RWD/160kW/PILOT_2
			#define	_12SMP_COND				_12SMP_OFF							// MV/RWD/160kW/PILOT_2
			#define	_RPWM_COND				_RPWM_01_03_ON						// MV/RWD/160kW/PILOT_2
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF					// MV/RWD/160kW/PILOT_2
			#define	_SW_RDC_SETTING			_MV_EV_P1_REAR_SW_RDC				// MV/RWD/160kW/PILOT_2
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE					// MV/RWD/160kW/PILOT_2
			#define	_FSW_FSAMP_FREQ			_12kHz_SINGLE_ALL					// MV/RWD/160kW/PILOT_2
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_12kHz_SINGLE_ALL				// MV/RWD/160kW/PILOT_2
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL				// MV/RWD/160kW/PILOT_2
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG						// MV/RWD/160kW/PILOT_2
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON						// MV/RWD/160kW/PILOT_2
			#define	_CUR_MAP_VERSION		_MV_PROTO_REAR_CUR_MAP				// MV/RWD/160kW/PILOT_2
			#define	_MOTOR_TYPE				_MV_P2_REAR_MOTOR					// MV/RWD/160kW/PILOT_2
			#define	_POWER_CAL_VERSION		_MV_EV_PROTO_REAR_160KW_POWER_CAL	// MV/RWD/160kW/PILOT_2
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4						// MV/RWD/160kW/PILOT_2
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MVa_EV_P1_REAR_TQ_COMP_CAL		// MV/RWD/160kW/PILOT_1
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_P1_REAR_TQ_COMP_CAL	// MV/RWD/160kW/PILOT_1
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
		#elif (_DEVELOPMENT_PHASE == _M_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_103							// MV/RWD/160kW/M
			#define	_12SMP_COND				_12SMP_OFF							// MV/RWD/160kW/M
			#define	_RPWM_COND				_RPWM_01_03_ON						// MV/RWD/160kW/M
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF					// MV/RWD/160kW/M
			#define	_SW_RDC_SETTING			_MV_EV_P1_REAR_SW_RDC				// MV/RWD/160kW/M
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE					// MV/RWD/160kW/M
			#define	_FSW_FSAMP_FREQ			_12kHz_SINGLE_ALL					// MV/RWD/160kW/M
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_12kHz_SINGLE_ALL				// MV/RWD/160kW/M
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL				// MV/RWD/160kW/M
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG						// MV/RWD/160kW/M
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON						// MV/RWD/160kW/M
			#define	_CUR_MAP_VERSION		_MV_PROTO_REAR_CUR_MAP				// MV/RWD/160kW/M
			#define	_MOTOR_TYPE				_MV_P2_REAR_MOTOR					// MV/RWD/160kW/M
			#define	_POWER_CAL_VERSION		_MV_EV_PROTO_REAR_160KW_POWER_CAL	// MV/RWD/160kW/M
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4						// MV/RWD/160kW/M
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MVa_EV_P1_REAR_TQ_COMP_CAL		// MV/RWD/160kW/M
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_P1_REAR_TQ_COMP_CAL	// MV/RWD/160kW/M
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
		#elif (_DEVELOPMENT_PHASE == _SOP_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_103							// MV/RWD/160kW/SOP
			#define	_12SMP_COND				_12SMP_OFF							// MV/RWD/160kW/SOP
			#define	_RPWM_COND				_RPWM_01_03_ON						// MV/RWD/160kW/SOP
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF					// MV/RWD/160kW/SOP
			#define	_SW_RDC_SETTING			_MV_EV_P1_REAR_SW_RDC				// MV/RWD/160kW/SOP
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE					// MV/RWD/160kW/SOP
			#define	_FSW_FSAMP_FREQ			_12kHz_SINGLE_ALL					// MV/RWD/160kW/SOP
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_12kHz_SINGLE_ALL				// MV/RWD/160kW/SOP
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL				// MV/RWD/160kW/SOP
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG						// MV/RWD/160kW/SOP
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON						// MV/RWD/160kW/SOP
			#define	_CUR_MAP_VERSION		_MV_PROTO_REAR_CUR_MAP				// MV/RWD/160kW/SOP
			#define	_MOTOR_TYPE				_MV_P2_REAR_MOTOR					// MV/RWD/160kW/SOP
			#define	_POWER_CAL_VERSION		_MV_EV_PROTO_REAR_160KW_POWER_CAL	// MV/RWD/160kW/SOP
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4						// MV/RWD/160kW/SOP
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MVa_EV_P1_REAR_TQ_COMP_CAL		// MV/RWD/160kW/SOP
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_P1_REAR_TQ_COMP_CAL	// MV/RWD/160kW/SOP
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
		#elif (_DEVELOPMENT_PHASE == _RC_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_103							// MV/RWD/160kW/RC
			#define	_12SMP_COND				_12SMP_OFF							// MV/RWD/160kW/RC
			#define	_RPWM_COND				_RPWM_01_03_ON						// MV/RWD/160kW/RC
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF					// MV/RWD/160kW/RC
			#define	_SW_RDC_SETTING			_MV_EV_P1_REAR_SW_RDC				// MV/RWD/160kW/RC
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE					// MV/RWD/160kW/RC
			#define	_FSW_FSAMP_FREQ			_12kHz_SINGLE_ALL					// MV/RWD/160kW/RC
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_12kHz_SINGLE_ALL				// MV/RWD/160kW/RC
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL				// MV/RWD/160kW/RC
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG						// MV/RWD/160kW/RC
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON						// MV/RWD/160kW/RC
			#define	_CUR_MAP_VERSION		_MV_PROTO_REAR_CUR_MAP				// MV/RWD/160kW/RC
			#define	_MOTOR_TYPE				_MV_P2_REAR_MOTOR					// MV/RWD/160kW/RC
			#define	_POWER_CAL_VERSION		_MV_EV_PROTO_REAR_160KW_POWER_CAL	// MV/RWD/160kW/RC
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4						// MV/RWD/160kW/RC
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MVa_EV_P1_REAR_TQ_COMP_CAL		// MV/RWD/160kW/RC
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_P1_REAR_TQ_COMP_CAL	// MV/RWD/160kW/RC
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
	#else
		#error undefined _DEVELOPMENT_PHASE MACRO
	
	#endif
	#else
		#error undefined _PERFORMANCE_TYPE MACRO
	
	#endif

#elif (_PROJECT_NAME == _ME_RWD_PROJ)

	/*-------------------------------------------------------------------------------------------
		@name	: 출력 타입에 의한 사양 구분
	-------------------------------------------------------------------------------------------*/
	
	#if (_PERFORMANCE_TYPE == _STANDARD_VERSION || _PERFORMANCE_TYPE == _PERFORMANCE_VERSION || _PERFORMANCE_TYPE == _LONG_RANGE_VERSION || _PERFORMANCE_TYPE == _eM_160kW_VERSION || _PERFORMANCE_TYPE == _eM_200kW_VERSION || _PERFORMANCE_TYPE == _eM_250kW_VERSION)
		/*-------------------------------------------------------------------------------------------
			@name	: 파워 모듈 및 회로에 의한 사양 구분
		-------------------------------------------------------------------------------------------*/
	
		#if (_DEVELOPMENT_PHASE == _TCAR_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_103							// ME/RWD/160kW/TCAR
			#define	_12SMP_COND				_12SMP_OFF							// ME/RWD/160kW/TCAR
			#define	_RPWM_COND				_RPWM_01_03_ON						// ME/RWD/160kW/TCAR
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF					// ME/RWD/160kW/TCAR
			#define	_SW_RDC_SETTING			_MV_EV_PROTO_REAR_SW_RDC			// ME/RWD/160kW/TCAR
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE					// ME/RWD/160kW/TCAR
			#define	_FSW_FSAMP_FREQ			_12kHz_SINGLE_ALL					// ME/RWD/160kW/TCAR
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_6_5kHz_DOUBLE					// ME/RWD/160kW/TCAR
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL				// ME/RWD/160kW/TCAR
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG						// ME/RWD/160kW/TCAR
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON						// ME/RWD/160kW/TCAR
			#define	_CUR_MAP_VERSION		_MV_PROTO_REAR_CUR_MAP				// ME/RWD/160kW/TCAR
			#define	_MOTOR_TYPE				_MV_PROTO_REAR_MOTOR				// ME/RWD/160kW/TCAR
			#define	_POWER_CAL_VERSION		_MV_EV_PROTO_REAR_160KW_POWER_CAL	// ME/RWD/160kW/TCAR
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4						// ME/RWD/160kW/TCAR
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_PROTO_REAR_TQ_COMP_CAL	// ME/RWD/160kW/TCAR
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_PROTO_REAR_TQ_COMP_CAL	// ME/RWD/160kW/TCAR
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
		#elif (_DEVELOPMENT_PHASE == _PROTO_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_103				// ME/RWD/160kW/PROTO
			#define	_12SMP_COND				_12SMP_OFF				// ME/RWD/160kW/PROTO
			#define	_RPWM_COND				_RPWM_01_03_ON			// ME/RWD/160kW/PROTO
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF		// ME/RWD/160kW/PROTO
			#define	_SW_RDC_SETTING			_MV_EV_P1_REAR_SW_RDC	// ME/RWD/160kW/PROTO
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE		// ME/RWD/160kW/PROTO
			#define	_FSW_FSAMP_FREQ			_12kHz_SINGLE_ALL		// ME/RWD/160kW/PROTO
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_12kHz_SINGLE_ALL	// ME/RWD/160kW/PROTO
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL	// ME/RWD/160kW/PROTO
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG			// ME/RWD/160kW/PROTO
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON			// ME/RWD/160kW/PROTO
			#define	_CUR_MAP_VERSION		_MV_PROTO_REAR_CUR_MAP	// ME/RWD/160kW/PROTO
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4			// ME/RWD/160kW/PROTO
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MVa_EV_P1_REAR_TQ_COMP_CAL		// MEa/RWD/160kW/PROTO
				#define	_POWER_CAL_VERSION		_ME_EV_P2_REAR_160KW_POWER_CAL	// MEa/RWD/160kW/PROTO
				#define	_MOTOR_TYPE				_ME_P1_REAR_MOTOR				// MEa/RWD/160kW/PROTO
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_P1_REAR_TQ_COMP_CAL			// ME/RWD/160kW/PROTO
				#define	_POWER_CAL_VERSION		_MV_EV_PROTO_REAR_160KW_POWER_CAL	// ME/RWD/160kW/PROTO
				#define	_MOTOR_TYPE				_MV_PROTO_REAR_MOTOR				// ME/RWD/160kW/PROTO
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
		#elif (_DEVELOPMENT_PHASE == _MASTER_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_103				// ME/RWD/160kW/MASTER
			#define	_12SMP_COND				_12SMP_OFF				// ME/RWD/160kW/MASTER
			#define	_RPWM_COND				_RPWM_01_03_ON			// ME/RWD/160kW/MASTER
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF		// ME/RWD/160kW/MASTER
			#define	_SW_RDC_SETTING			_MV_EV_P1_REAR_SW_RDC	// ME/RWD/160kW/MASTER
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE		// ME/RWD/160kW/MASTER
			#define	_FSW_FSAMP_FREQ			_12kHz_SINGLE_ALL		// ME/RWD/160kW/MASTER
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_12kHz_SINGLE_ALL	// ME/RWD/160kW/MASTER
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL	// ME/RWD/160kW/MASTER
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG			// ME/RWD/160kW/MASTER
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON			// ME/RWD/160kW/MASTER
			#define	_CUR_MAP_VERSION		_MV_PROTO_REAR_CUR_MAP	// ME/RWD/160kW/MASTER
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4			// ME/RWD/160kW/MASTER
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MVa_EV_P1_REAR_TQ_COMP_CAL		// MEa/RWD/160kW/MASTER
				#define	_POWER_CAL_VERSION		_ME_EV_P2_REAR_160KW_POWER_CAL	// MEa/RWD/160kW/MASTER
				#define	_MOTOR_TYPE				_ME_P1_REAR_MOTOR				// MEa/RWD/160kW/MASTER
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_P1_REAR_TQ_COMP_CAL			// ME/RWD/160kW/MASTER
				#define	_POWER_CAL_VERSION		_MV_EV_PROTO_REAR_160KW_POWER_CAL	// ME/RWD/160kW/MASTER
				#define	_MOTOR_TYPE				_MV_PROTO_REAR_MOTOR				// ME/RWD/160kW/MASTER
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
		#elif (_DEVELOPMENT_PHASE == _PILOT_1_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_103				// ME/RWD/160kW/PILOT_1
			#define	_12SMP_COND				_12SMP_OFF				// ME/RWD/160kW/PILOT_1
			#define	_RPWM_COND				_RPWM_01_03_ON			// ME/RWD/160kW/PILOT_1
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF		// ME/RWD/160kW/PILOT_1
			#define	_SW_RDC_SETTING			_MV_EV_P1_REAR_SW_RDC	// ME/RWD/160kW/PILOT_1
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE		// ME/RWD/160kW/PILOT_1
			#define	_FSW_FSAMP_FREQ			_12kHz_SINGLE_ALL		// ME/RWD/160kW/PILOT_1
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_12kHz_SINGLE_ALL	// ME/RWD/160kW/PILOT_1
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL	// ME/RWD/160kW/PILOT_1
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG			// ME/RWD/160kW/PILOT_1
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON			// ME/RWD/160kW/PILOT_1
			#define	_CUR_MAP_VERSION		_MV_PROTO_REAR_CUR_MAP	// ME/RWD/160kW/PILOT_1
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4			// ME/RWD/160kW/PILOT_1
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MVa_EV_P1_REAR_TQ_COMP_CAL		// MEa/RWD/160kW/PILOT_1
				#define	_POWER_CAL_VERSION		_ME_EV_P2_REAR_160KW_POWER_CAL	// MEa/RWD/160kW/PILOT_1
				#define	_MOTOR_TYPE				_ME_P1_REAR_MOTOR				// MEa/RWD/160kW/PILOT_1
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MV_EV_P1_REAR_TQ_COMP_CAL			// ME/RWD/160kW/PILOT_1
				#define	_POWER_CAL_VERSION		_MV_EV_PROTO_REAR_160KW_POWER_CAL	// ME/RWD/160kW/PILOT_1
				#define	_MOTOR_TYPE				_ME_P1_REAR_MOTOR					// ME/RWD/160kW/PILOT_1
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
		#elif (_DEVELOPMENT_PHASE == _PILOT_2_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_103				// ME/RWD/160kW/PILOT_2
			#define	_12SMP_COND				_12SMP_OFF				// ME/RWD/160kW/PILOT_2
			#define	_RPWM_COND				_RPWM_01_03_ON			// ME/RWD/160kW/PILOT_2
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF		// ME/RWD/160kW/PILOT_2
			#define	_SW_RDC_SETTING			_MV_EV_P1_REAR_SW_RDC	// ME/RWD/160kW/PILOT_2
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE		// ME/RWD/160kW/PILOT_2
			#define	_FSW_FSAMP_FREQ			_12kHz_SINGLE_ALL		// ME/RWD/160kW/PILOT_2
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_12kHz_SINGLE_ALL	// ME/RWD/160kW/PILOT_2
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL	// ME/RWD/160kW/PILOT_2
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG			// ME/RWD/160kW/PILOT_2
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON			// ME/RWD/160kW/PILOT_2
			#define	_CUR_MAP_VERSION		_MV_PROTO_REAR_CUR_MAP	// ME/RWD/160kW/PILOT_2
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4			// ME/RWD/160kW/PILOT_2
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MVa_EV_P1_REAR_TQ_COMP_CAL		// MEa/RWD/160kW/PILOT_2
				#define	_POWER_CAL_VERSION		_ME_EV_P2_REAR_160KW_POWER_CAL	// MEa/RWD/160kW/PILOT_2
				#define	_MOTOR_TYPE				_ME_P1_REAR_MOTOR				// MEa/RWD/160kW/PILOT_2
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_ME_EV_P2_REAR_TQ_COMP_CAL		// ME/RWD/160kW/PILOT_2
				#define	_POWER_CAL_VERSION		_ME_EV_P2_REAR_160KW_POWER_CAL	// ME/RWD/160kW/PILOT_2
				#define	_MOTOR_TYPE				_ME_P1_REAR_MOTOR				// ME/RWD/160kW/PILOT_2
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
		#elif (_DEVELOPMENT_PHASE == _M_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_103				// ME/RWD/160kW/M
			#define	_12SMP_COND				_12SMP_OFF				// ME/RWD/160kW/M
			#define	_RPWM_COND				_RPWM_01_03_ON			// ME/RWD/160kW/M
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF		// ME/RWD/160kW/M
			#define	_SW_RDC_SETTING			_MV_EV_P1_REAR_SW_RDC	// ME/RWD/160kW/M
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE		// ME/RWD/160kW/M
			#define	_FSW_FSAMP_FREQ			_12kHz_SINGLE_ALL		// ME/RWD/160kW/M
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_12kHz_SINGLE_ALL	// ME/RWD/160kW/M
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL	// ME/RWD/160kW/M
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG			// ME/RWD/160kW/M
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON			// ME/RWD/160kW/M
			#define	_CUR_MAP_VERSION		_MV_PROTO_REAR_CUR_MAP	// ME/RWD/160kW/M
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4			// ME/RWD/160kW/M
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MVa_EV_P1_REAR_TQ_COMP_CAL		// MEa/RWD/160kW/M
				#define	_POWER_CAL_VERSION		_ME_EV_P2_REAR_160KW_POWER_CAL	// MEa/RWD/160kW/M
				#define	_MOTOR_TYPE				_ME_P1_REAR_MOTOR				// MEa/RWD/160kW/M
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_ME_EV_P2_REAR_TQ_COMP_CAL		// ME/RWD/160kW/M
				#define	_POWER_CAL_VERSION		_ME_EV_P2_REAR_160KW_POWER_CAL	// ME/RWD/160kW/M
				#define	_MOTOR_TYPE				_ME_P1_REAR_MOTOR				// ME/RWD/160kW/M
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
		#elif (_DEVELOPMENT_PHASE == _SOP_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_103				// ME/RWD/160kW/SOP
			#define	_12SMP_COND				_12SMP_OFF				// ME/RWD/160kW/SOP
			#define	_RPWM_COND				_RPWM_01_03_ON			// ME/RWD/160kW/SOP
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF		// ME/RWD/160kW/SOP
			#define	_SW_RDC_SETTING			_MV_EV_P1_REAR_SW_RDC	// ME/RWD/160kW/SOP
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE		// ME/RWD/160kW/SOP
			#define	_FSW_FSAMP_FREQ			_12kHz_SINGLE_ALL		// ME/RWD/160kW/SOP
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_12kHz_SINGLE_ALL	// ME/RWD/160kW/SOP
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL	// ME/RWD/160kW/SOP
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG			// ME/RWD/160kW/SOP
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON			// ME/RWD/160kW/SOP
			#define	_CUR_MAP_VERSION		_MV_PROTO_REAR_CUR_MAP	// ME/RWD/160kW/SOP
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4			// ME/RWD/160kW/SOP
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MVa_EV_P1_REAR_TQ_COMP_CAL		// MEa/RWD/160kW/SOP
				#define	_POWER_CAL_VERSION		_ME_EV_P2_REAR_160KW_POWER_CAL	// MEa/RWD/160kW/SOP
				#define	_MOTOR_TYPE				_ME_P1_REAR_MOTOR				// MEa/RWD/160kW/SOP
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_ME_EV_P2_REAR_TQ_COMP_CAL		// ME/RWD/160kW/SOP
				#define	_POWER_CAL_VERSION		_ME_EV_P2_REAR_160KW_POWER_CAL	// ME/RWD/160kW/SOP
				#define	_MOTOR_TYPE				_ME_P1_REAR_MOTOR				// ME/RWD/160kW/SOP
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
		#elif (_DEVELOPMENT_PHASE == _RC_VERSION)
			/* 전류제어용 사양 선정 */
			#define	_MI_REF_SETTING			_MI_REF_103				// ME/RWD/160kW/RC
			#define	_12SMP_COND				_12SMP_OFF				// ME/RWD/160kW/RC
			#define	_RPWM_COND				_RPWM_01_03_ON			// ME/RWD/160kW/RC
			#define	_NO_LOAD_TQ_COMP_COND	NO_LOAD_TQ_COMP_OFF		// ME/RWD/160kW/RC
			#define	_SW_RDC_SETTING			_MV_EV_P1_REAR_SW_RDC	// ME/RWD/160kW/RC
			#define	_ROC_RPWM_FUNCTION		_ROC_RPWM_DISABLE		// ME/RWD/160kW/RC
			#define	_FSW_FSAMP_FREQ			_12kHz_SINGLE_ALL		// ME/RWD/160kW/RC
			#define	_OEW_FSW_FSAMP_FREQ		_OEW_12kHz_SINGLE_ALL	// ME/RWD/160kW/RC
			#define	_ODC_FSW_FSAMP_FREQ		_ODC_12kHz_SINGLE_ALL	// ME/RWD/160kW/RC
			#define	_MULTI_DC_METHOD_		_MULTI_INTEG			// ME/RWD/160kW/RC
			#define	_MULTI_NON_LINEAR_COMP	_LENEAR_COMP_ON			// ME/RWD/160kW/RC
			#define	_CUR_MAP_VERSION		_MV_PROTO_REAR_CUR_MAP	// ME/RWD/160kW/RC
			#define	_DELTA_TRQREF			_DELTA_TRQREF_4			// ME/RWD/160kW/RC
	
			/* Cal 이원화 */
	
			#if (_MARKET_VERSION == _NORTH_AMERICA_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_MVa_EV_P1_REAR_TQ_COMP_CAL		// MEa/RWD/160kW/RC
				#define	_POWER_CAL_VERSION		_ME_EV_P2_REAR_160KW_POWER_CAL	// MEa/RWD/160kW/RC
				#define	_MOTOR_TYPE				_ME_P1_REAR_MOTOR				// MEa/RWD/160kW/RC
	
			#elif (_MARKET_VERSION == _DOMESTIC_VERSION || _MARKET_VERSION == _EUROPE_VERSION || _MARKET_VERSION == _CHINA_VERSION || _MARKET_VERSION == _COMMON_COUNTRY_VERSION  || _MARKET_VERSION == _JAPAN_VERSION)
				#define	_TQ_COMP_CAL_VERSION	_ME_EV_P2_REAR_TQ_COMP_CAL		// ME/RWD/160kW/RC
				#define	_POWER_CAL_VERSION		_ME_EV_P2_REAR_160KW_POWER_CAL	// ME/RWD/160kW/RC
				#define	_MOTOR_TYPE				_ME_P1_REAR_MOTOR				// ME/RWD/160kW/RC
	
		#else
			#error undefined _MARKET_VERSION MACRO
	
		#endif
	#else
		#error undefined _DEVELOPMENT_PHASE MACRO
	
	#endif
	#else
		#error undefined _PERFORMANCE_TYPE MACRO
	
	#endif

#else

	/* 프로젝트 미선언 Error 삭제 (헤더 세분화 실시) */
	
	/* DEFAULT 선언 Excel 시트 작성 금지! */

#endif


#endif /* #ifndef _CCCALPRJCFG_H_ */

/********************************************************************************************
*                                        End of File                                        *
********************************************************************************************/
