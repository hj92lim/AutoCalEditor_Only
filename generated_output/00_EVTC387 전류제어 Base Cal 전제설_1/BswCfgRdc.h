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
	@file		:	BswCfgRdc.h
	@brief		:	
	@author		:	JY.Park
	@date		:	

*/
/*=========================================================================================*/

#ifndef _BSWCFGRDC_H_
#define _BSWCFGRDC_H_

/*===========================================================================================
	INCLUDES
===========================================================================================*/
#include "ItrPlatformType.h"
#include "common.h"
#include "CcCal.h"

/*===========================================================================================
	DEFINES
===========================================================================================*/
/*-------------------------------------------------------------------------------------------
	@name	: SW RDC관련 일반 사양(ATO GAIN등)
-------------------------------------------------------------------------------------------*/

/* MOTOR Resolver Configuration */
#define	BSWCFGRDC_MOT_K1_D				0.5605666	// Natural Frequency 200Hz, Damping Ratio 1.0
#define	BSWCFGRDC_MOT_K2_D				0.7535489
#define	BSWCFGRDC_MOT_K1_SCALE			6
#define	BSWCFGRDC_MOT_K2_SCALE			5
#define	BSWCFGRDC_MOT_SIN_DC_OFFSET		0
#define	BSWCFGRDC_MOT_COS_DC_OFFSET		0
#define	BSWCFGRDC_MOT_SIN_SCALE			1200
#define	BSWCFGRDC_MOT_COS_SCALE			1200

/* HSG Resolver Configuration */
#define	BSWCFGRDC_HSG_K1_D				0.5605666	// Natural Frequency 200Hz, Damping Ratio 1.0
#define	BSWCFGRDC_HSG_K2_D				0.7535489
#define	BSWCFGRDC_HSG_K1_SCALE			6
#define	BSWCFGRDC_HSG_K2_SCALE			5
#define	BSWCFGRDC_HSG_SIN_DC_OFFSET		0
#define	BSWCFGRDC_HSG_COS_DC_OFFSET		0
#define	BSWCFGRDC_HSG_SIN_SCALE			1200
#define	BSWCFGRDC_HSG_COS_SCALE			1200

/*-------------------------------------------------------------------------------------------
	@name	: 파워 모듈 및 회로에 의한 사양 구분
-------------------------------------------------------------------------------------------*/

/* MOTOR UINTRIG configuration */
#define	BSWCFGRDC_MOT_PERIOD				66		// 중요! 단위us
#define	BSWCFGRDC_MOT_START_OFFSET			5		// 중요! 단위us
#define	BSWCFGRDC_MOT_UNITRIG_START_OFFSET	33005	// 중요! 단위us

/* HSG UINTRIG configuration */
#define	BSWCFGRDC_HSG_PERIOD				66		// 중요! 단위us
#define	BSWCFGRDC_HSG_START_OFFSET			30		// 중요! 단위us
#define	BSWCFGRDC_HSG_UNITRIG_START_OFFSET	33030	// 중요! 단위us

/*===========================================================================================
	TYPE DEFINITIONS
===========================================================================================*/

/*===========================================================================================
	Global Variables
===========================================================================================*/
#include "section_CAL2_begin.h"
extern const UINT32  BswCfgCal_Rdc_MotPeriod;
extern const FLOAT32 BswCfgCal_Rdc_MotStartOffset;
extern const FLOAT32 BswCfgCal_Rdc_MotK1;
extern const FLOAT32 BswCfgCal_Rdc_MotK2;
extern const INT32   BswCfgCal_Rdc_MotK1Scale;
extern const INT32   BswCfgCal_Rdc_MotK2Scale;
extern const UINT32  BswCfgCal_Rdc_MotSinDcOffset;
extern const UINT32  BswCfgCal_Rdc_MotCosDcOffset;
extern const INT32   BswCfgCal_Rdc_MotSinScale;
extern const INT32   BswCfgCal_Rdc_MotCosScale;
extern const UINT32  BswCfgCal_Rdc_MotUnitrigDelay;
extern const UINT32  BswCfgCal_Rdc_MotUnitrigStartOffset;
extern const UINT32  BswCfgCal_Rdc_HsgPeriod;
extern const FLOAT32 BswCfgCal_Rdc_HsgStartOffset;
extern const FLOAT32 BswCfgCal_Rdc_HsgK1;
extern const FLOAT32 BswCfgCal_Rdc_HsgK2;
extern const INT32   BswCfgCal_Rdc_HsgK1Scale;
extern const INT32   BswCfgCal_Rdc_HsgK2Scale;
extern const UINT32  BswCfgCal_Rdc_HsgSinDcOffset;
extern const UINT32  BswCfgCal_Rdc_HsgCosDcOffset;
extern const INT32   BswCfgCal_Rdc_HsgSinScale;
extern const INT32   BswCfgCal_Rdc_HsgCosScale;
extern const UINT32  BswCfgCal_Rdc_HsgUnitrigDelay;
extern const UINT32  BswCfgCal_Rdc_HsgUnitrigStartOffset;
#include "section_CAL_end.h"

#endif /* #ifndef _BSWCFGRDC_H_ */

/********************************************************************************************
*                                        End of File                                        *
********************************************************************************************/
