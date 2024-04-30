#pragma once
#include "afxdialogex.h"


// CSchedulerOption 대화 상자

class CSchedulerOption : public CDialog
{
	DECLARE_DYNAMIC(CSchedulerOption)

public:
	CSchedulerOption(CWnd* pParent = nullptr);   // 표준 생성자입니다.
	virtual ~CSchedulerOption();
  int get_scheduler_type();
  void set_scheduler_type(int index);
  void set_option_value(bool* preemtion, int* scheduler) {
    preemtion_enabling = preemtion;
    scheduler_selection = scheduler;
  };

private:
  int select_scheduler = 0;
  bool* preemtion_enabling = nullptr;
  int* scheduler_selection = nullptr;

// 대화 상자 데이터입니다.
#ifdef AFX_DESIGN_TIME
	enum { IDD = IDD_CSchedulerOption };
#endif

protected:
	virtual void DoDataExchange(CDataExchange* pDX);    // DDX/DDV 지원입니다.

	DECLARE_MESSAGE_MAP()
public:
  BOOL using_preemtion;
  virtual BOOL OnInitDialog();
  afx_msg void OnBnClickedOk();
//  CString scheduler_type;
  CComboBox scheduler_combo;
  afx_msg void OnSelchangeComboScheduler();
  afx_msg void OnClickedCheckPreemtion();
};
