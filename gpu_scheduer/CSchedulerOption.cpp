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
  , using_preemtion(FALSE)
{

}

CSchedulerOption::~CSchedulerOption()
{
}

void CSchedulerOption::DoDataExchange(CDataExchange* pDX)
{
  CDialog::DoDataExchange(pDX);
  DDX_Check(pDX, IDC_CHECK_PREEMTION, using_preemtion);
  DDX_Control(pDX, IDC_COMBO_SCHEDULER, scheduler_combo);
}


BEGIN_MESSAGE_MAP(CSchedulerOption, CDialog)
  ON_BN_CLICKED(IDOK, &CSchedulerOption::OnBnClickedOk)
  ON_CBN_SELCHANGE(IDC_COMBO_SCHEDULER, &CSchedulerOption::OnSelchangeComboScheduler)
  ON_BN_CLICKED(IDC_CHECK_PREEMTION, &CSchedulerOption::OnClickedCheckPreemtion)
END_MESSAGE_MAP()


// CSchedulerOption 메시지 처리기

BOOL CSchedulerOption::OnInitDialog()
{
  CDialog::OnInitDialog();

  // TODO:  Add extra initialization here
  scheduler_combo.AddString(_T("Mostallocated"));
  scheduler_combo.AddString(_T("Compact"));
  scheduler_combo.AddString(_T("Round Robin"));
  scheduler_combo.AddString(_T("Fare Share"));

  //select_scheduler = 0;
  scheduler_combo.SetCurSel(select_scheduler);

  return TRUE;  // return TRUE unless you set the focus to a control
  // EXCEPTION: OCX Property Pages should return FALSE
}

int CSchedulerOption::get_scheduler_type() {
  return select_scheduler;
}

void CSchedulerOption::set_scheduler_type(int index) {
  select_scheduler = index;
}


void CSchedulerOption::OnBnClickedOk()
{
    // TODO: 여기에 컨트롤 알림 처리기 코드를 추가합니다.
    CDialog::OnOK();
}


void CSchedulerOption::OnSelchangeComboScheduler()
{
  // TODO: 여기에 컨트롤 알림 처리기 코드를 추가합니다.
  select_scheduler = scheduler_combo.GetCurSel();
  if (nullptr != scheduler_selection) {
    *scheduler_selection = select_scheduler;
  }
}


void CSchedulerOption::OnClickedCheckPreemtion()
{
  // TODO: 여기에 컨트롤 알림 처리기 코드를 추가합니다.
}
