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
  void set_option_value(bool* preemtion, int* scheduler, bool *scheduer_with_flavor_opt, bool *doing_till_end) {
    preemtion_enabling = preemtion;
    scheduler_selection = scheduler;
    scheduler_with_defined = scheduer_with_flavor_opt;
    infinity_working = doing_till_end;
  };

private:
  int select_scheduler = 0;
  bool* preemtion_enabling = nullptr;
  int* scheduler_selection = nullptr;
  bool* scheduler_with_defined = nullptr;
  bool* infinity_working = nullptr;

// 대화 상자 데이터입니다.
#ifdef AFX_DESIGN_TIME
	enum { IDD = IDD_CSchedulerOption };
#endif

protected:
	virtual void DoDataExchange(CDataExchange* pDX);    // DDX/DDV 지원입니다.

	DECLARE_MESSAGE_MAP()
public:
//  BOOL using_preemtion;
  virtual BOOL OnInitDialog();
  afx_msg void OnBnClickedOk();
//  CString scheduler_type;
  CComboBox scheduler_combo;
  afx_msg void OnSelchangeComboScheduler();
  afx_msg void OnClickedCheckPreemtion();
//  BOOL scheduler_with_flavor;
  afx_msg void OnClickedCheckFlavor();
  CButton scheduler_flavor;
  CButton preemtion_option;
  CButton perform_until_finish;
  afx_msg void OnClickedCheckInf();
};
