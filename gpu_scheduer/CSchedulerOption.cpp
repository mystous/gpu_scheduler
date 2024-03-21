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
  , scheduler_selection(0)
  , using_preemtion(FALSE)
{

}

CSchedulerOption::~CSchedulerOption()
{
}

void CSchedulerOption::DoDataExchange(CDataExchange* pDX)
{
  CDialog::DoDataExchange(pDX);
  DDX_Radio(pDX, IDC_RADIO_MOST_WANTED, scheduler_selection);
  DDX_Check(pDX, IDC_CHECK_PREEMTION, using_preemtion);
}


BEGIN_MESSAGE_MAP(CSchedulerOption, CDialog)
END_MESSAGE_MAP()


// CSchedulerOption 메시지 처리기


BOOL CSchedulerOption::OnInitDialog()
{
  CDialog::OnInitDialog();

  // TODO:  Add extra initialization here

  CButton* pCheck;
  pCheck = (CButton*)GetDlgItem(IDC_RADIO_ROUND_ROBIN);
  pCheck->SetCheck(TRUE);
  pCheck = (CButton*)GetDlgItem(IDC_RADIO_MOST_WANTED);
  pCheck->SetCheck(FALSE);

  

  return TRUE;  // return TRUE unless you set the focus to a control
  // EXCEPTION: OCX Property Pages should return FALSE
}
