#pragma once
#include "afxdialogex.h"
#include "experiment_perform.h"
#include "call_back_object.h"


// experiment_dialog 대화 상자

class experiment_dialog : public CDialogEx, public call_back_object
{
	DECLARE_DYNAMIC(experiment_dialog)

public:
	experiment_dialog(CWnd* pParent = nullptr);   // 표준 생성자입니다.
	virtual ~experiment_dialog();

// 대화 상자 데이터입니다.
#ifdef AFX_DESIGN_TIME
	enum { IDD = IDD_experiment_dialog };
#endif

protected:
	virtual void DoDataExchange(CDataExchange* pDX);    // DDX/DDV 지원입니다.
  const CString thread_notice = _T("Number of %d Threads Working on it...");
  const CString task_notice = _T("Totaly %d of hyperparmeter will be perfomred. %d of experiment has be done. %d of experiment are lefted");
  int thread_total = 4;
  int hyperpara_total = 0;
  int experiment_done = 0;
  double alpha_para[3] = {0.13889, 0.83889, 0.1};
  double beta_para[3] = { 70., 95., 5. };
  int d_para[3] = { 100000, 1000000, 100000 };
  int w_para[3] = { 20, 100, 10 };
  bool sch[4] = {true, false, false, false };
  CButton* scheduler_ctrl[4] = {nullptr, };
  string task_file_name, server_file_name;

  experiment_perform experiment_obj;

	DECLARE_MESSAGE_MAP()
  virtual void OnOK();
public:
  afx_msg void OnClickedButtonPickFile();
  afx_msg void OnClickedButtonStop();
  afx_msg void OnClickedButtonPause();
  afx_msg void OnClickedButtonPerform();
  CEdit a_interval;
  CEdit a_max;
  CEdit a_min;
  CEdit b_interval;
  CEdit b_max;
  CEdit b_min;
  CEdit d_interval;
  CEdit d_max;
  CEdit d_min;
  CEdit w_interval;
  CEdit w_max;
  CEdit w_min;
  CEdit thread_count;
  CListBox perform_status;
  CStatic thread_status;
  CStatic hyper_status;
  virtual BOOL OnInitDialog();
  void function_call();
private:
  void SetIntValue(int value, CEdit* control);
  void SetDoubleValue(double value, CEdit* control);
  void GetIntValue(int *value, CEdit* control);
  void GetDoubleValue(double *value, CEdit* control);
  void UpdateStaticInfo();
  void UpdateHyperparameters();
  vector<double> generate_double_values(double start, double end, double step);
  vector<int> generate_int_values(int start, int end, int step);
  vector<global_structure::scheduler_option> hyperparameter_searchspace;
public:
  CButton compact_sch;
  CButton mcts_sch;
  CButton mostwanted_sch;
  CButton round_robin_sch;
  afx_msg void OnClickedButtonPickServer();
  CEdit file_name_ctrl;
  CEdit server_name_ctrl;
};
