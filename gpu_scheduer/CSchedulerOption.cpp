// CSchedulerOption.cpp: 구현 파일
//

#include "pch.h"
#include "gpu_scheduer.h"
#include "afxdialogex.h"
#include "CSchedulerOption.h"


// CSchedulerOption 대화 상자

IMPLEMENT_DYNAMIC(CSchedulerOption, CDialog)

CSchedulerOption::CSchedulerOption(CWnd* pParent /*=nullptr*/)
	: CDialog(IDD_CSchedulerOption, pParent)
{

}

CSchedulerOption::~CSchedulerOption()
{
}

void CSchedulerOption::DoDataExchange(CDataExchange* pDX)
{
    CDialog::DoDataExchange(pDX);
    //  DDX_Check(pDX, IDC_CHECK_PREEMTION, using_preemtion);
    DDX_Control(pDX, IDC_COMBO_SCHEDULER, scheduler_combo);
    //  DDX_Check(pDX, IDC_CHECK_FLAVOR, scheduler_with_flavor);
    DDX_Control(pDX, IDC_CHECK_FLAVOR, scheduler_flavor);
    DDX_Control(pDX, IDC_CHECK_PREEMTION, preemtion_option);
    DDX_Control(pDX, IDC_CHECK_INF, perform_until_finish);
    DDX_Control(pDX, IDC_STARVATION_PREVENTION, starvation_prevention_opt);
    DDX_Control(pDX, IDC_EDIT_AGE_WEIGHT, age_weight_const);
    DDX_Control(pDX, IDC_EDIT_REORDER_SIZE, reorder_target_count);
    DDX_Control(pDX, IDC_EDIT_UPPER_BOUND, starvation_upper_bound);
    DDX_Control(pDX, IDC_EDIT_WAIT_WINDOW, preemption_wait_window);
}


BEGIN_MESSAGE_MAP(CSchedulerOption, CDialog)
  ON_BN_CLICKED(IDOK, &CSchedulerOption::OnBnClickedOk)
  ON_CBN_SELCHANGE(IDC_COMBO_SCHEDULER, &CSchedulerOption::OnSelchangeComboScheduler)
  ON_BN_CLICKED(IDC_CHECK_PREEMTION, &CSchedulerOption::OnClickedCheckPreemtion)
  ON_BN_CLICKED(IDC_CHECK_FLAVOR, &CSchedulerOption::OnClickedCheckFlavor)
  ON_BN_CLICKED(IDC_CHECK_INF, &CSchedulerOption::OnClickedCheckInf)
    ON_BN_CLICKED(IDC_STARVATION_PREVENTION, &CSchedulerOption::OnClickedStarvationPrevention)
  ON_EN_CHANGE(IDC_EDIT_AGE_WEIGHT, &CSchedulerOption::OnEnChangeEditAgeWeight)
END_MESSAGE_MAP()


// CSchedulerOption 메시지 처리기

BOOL CSchedulerOption::OnInitDialog()
{
  CDialog::OnInitDialog();

  // TODO:  Add extra initialization here
  scheduler_combo.AddString(_T("Mostallocated"));
  scheduler_combo.AddString(_T("Compact"));
  scheduler_combo.AddString(_T("Round Robin"));
  scheduler_combo.AddString(_T("MCTS"));
  scheduler_combo.AddString(_T("Fare Share"));

  //select_scheduler = 0;
  scheduler_combo.SetCurSel(get_scheduler_type());
  scheduler_flavor.SetCheck(*scheduler_with_defined);
  preemtion_option.SetCheck(*preemtion_enabling);
  perform_until_finish.SetCheck(*infinity_working);
  starvation_prevention_opt.SetCheck(*starvation_prevention);

  CString strValue;
  strValue.Format(_T("%.1f"), *starvation_upper_bound_value);
  starvation_upper_bound.SetWindowText(strValue);
  strValue.Format(_T("%f"), *age_weight_const_value);
  age_weight_const.SetWindowText(strValue);
  strValue.Format(_T("%d"), *reorder_target_value);
  reorder_target_count.SetWindowText(strValue);
  strValue.Format(_T("%d"), *preemption_task_window_value);
  preemption_wait_window.SetWindowText(strValue);


  return TRUE;  // return TRUE unless you set the focus to a control
  // EXCEPTION: OCX Property Pages should return FALSE
}

int CSchedulerOption::get_scheduler_type() {
  return static_cast<int>(*scheduler_selection);
}

void CSchedulerOption::set_scheduler_type(int index) {
  select_scheduler = index;
}


void CSchedulerOption::OnBnClickedOk()
{
    // TODO: 여기에 컨트롤 알림 처리기 코드를 추가합니다.

  CString strValue;
  starvation_upper_bound.GetWindowText(strValue);
  *starvation_upper_bound_value = _ttof(strValue);
  age_weight_const.GetWindowText(strValue);
  *age_weight_const_value = _ttof(strValue);
  reorder_target_count.GetWindowText(strValue);
  *reorder_target_value = _ttoi(strValue);
  preemption_wait_window.GetWindowText(strValue);
  *preemption_task_window_value = _ttoi(strValue);
  *starvation_prevention = starvation_prevention_opt.GetCheck();
  *scheduler_with_defined = scheduler_flavor.GetCheck();
  *infinity_working = perform_until_finish.GetCheck();
  *preemtion_enabling = preemtion_option.GetCheck();
  select_scheduler = scheduler_combo.GetCurSel();
  if (nullptr != scheduler_selection) {
    *scheduler_selection = static_cast<scheduler_type>(select_scheduler);
  }
  CDialog::OnOK();
}


void CSchedulerOption::OnSelchangeComboScheduler()
{
  // TODO: 여기에 컨트롤 알림 처리기 코드를 추가합니다.
  
}


void CSchedulerOption::OnClickedCheckPreemtion()
{
  // TODO: 여기에 컨트롤 알림 처리기 코드를 추가합니다.
  
}


void CSchedulerOption::OnClickedCheckFlavor()
{
  // TODO: 여기에 컨트롤 알림 처리기 코드를 추가합니다.
}


void CSchedulerOption::OnClickedCheckInf()
{
}


void CSchedulerOption::OnClickedStarvationPrevention()
{
}


void CSchedulerOption::OnEnChangeEditAgeWeight()
{
  // TODO:  RICHEDIT 컨트롤인 경우, 이 컨트롤은
  // CDialog::OnInitDialog() 함수를 재지정 
  //하고 마스크에 OR 연산하여 설정된 ENM_CHANGE 플래그를 지정하여 CRichEditCtrl().SetEventMask()를 호출하지 않으면
  // 이 알림 메시지를 보내지 않습니다.

  // TODO:  여기에 컨트롤 알림 처리기 코드를 추가합니다.
}
