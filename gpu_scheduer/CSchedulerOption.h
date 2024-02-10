#pragma once
#include "afxdialogex.h"


// CSchedulerOption 대화 상자

class CSchedulerOption : public CDialog
{
	DECLARE_DYNAMIC(CSchedulerOption)

public:
	CSchedulerOption(CWnd* pParent = nullptr);   // 표준 생성자입니다.
	virtual ~CSchedulerOption();

// 대화 상자 데이터입니다.
#ifdef AFX_DESIGN_TIME
	enum { IDD = IDD_CSchedulerOption };
#endif

protected:
	virtual void DoDataExchange(CDataExchange* pDX);    // DDX/DDV 지원입니다.

	DECLARE_MESSAGE_MAP()
public:
  int scheduler_selection;
  BOOL using_preemtion;
};
