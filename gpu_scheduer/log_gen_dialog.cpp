// log_gen_dialog.cpp: 구현 파일
//

#include "pch.h"
#include "gpu_scheduer.h"
#include "afxdialogex.h"
#include "log_gen_dialog.h"


// log_gen_dialog 대화 상자

IMPLEMENT_DYNAMIC(log_gen_dialog, CDialogEx)

log_gen_dialog::log_gen_dialog(CWnd* pParent /*=nullptr*/)
	: CDialogEx(IDD_DIALOG_log_gen, pParent)
  , task_count_string(_T(""))
  , run_after_gen(FALSE)
{

}

log_gen_dialog::~log_gen_dialog()
{
}

void log_gen_dialog::DoDataExchange(CDataExchange* pDX)
{
  CDialogEx::DoDataExchange(pDX);
  DDX_Text(pDX, IDC_EDIT_TASK_COUNT, task_count_string);
  DDX_Check(pDX, IDC_RADIO_RUN, run_after_gen);
  DDX_Control(pDX, IDC_CHECK_RAMDOM, all_random_check);
  DDX_Control(pDX, IDC_LIST_CTL_PARAM_DIST, param_distribution_list);
}


BEGIN_MESSAGE_MAP(log_gen_dialog, CDialogEx)
  ON_BN_CLICKED(IDC_CHECK_RAMDOM, &log_gen_dialog::OnBnClickedCheckRamdom)
  ON_NOTIFY(LVN_ITEMCHANGED, IDC_LIST_CTL_PARAM_DIST, &log_gen_dialog::OnLvnItemchangedListCtlParamDist)
  ON_NOTIFY(NM_CUSTOMDRAW, IDC_LIST_CTL_PARAM_DIST, &log_gen_dialog::OnNMCustomDrawListCtrl)
  ON_NOTIFY(NM_CLICK, IDC_LIST_CTL_PARAM_DIST, &log_gen_dialog::OnClickListCtlParamDist)
  ON_BN_CLICKED(IDOK, &log_gen_dialog::OnBnClickedOk)
END_MESSAGE_MAP()


void log_gen_dialog::OnBnClickedCheckRamdom()
{
  bool disable = false;
  if (TRUE == all_random_check.GetCheck()) {
    disable = true;
  }
  change_option_diable(disable);
  all_random_dist = disable;
}

void log_gen_dialog::change_option_diable(bool disable) {
  param_distribution_list.EnableWindow((BOOL)!disable);
}


BOOL log_gen_dialog::OnInitDialog()
{
  CDialogEx::OnInitDialog();

  // TODO:  여기에 추가 초기화 작업을 추가합니다.
  param_distribution_list.SetExtendedStyle(LVS_EX_FULLROWSELECT | LVS_EX_GRIDLINES);
  param_distribution_list.InsertColumn(0, _T("Parameter"), LVCFMT_LEFT, 150);
  param_distribution_list.InsertColumn(1, _T("Norm"), LVCFMT_CENTER, 100);
  param_distribution_list.InsertColumn(2, _T("Expon"), LVCFMT_CENTER, 100);
  param_distribution_list.InsertColumn(3, _T("Lognorm"), LVCFMT_CENTER, 100);
  param_distribution_list.InsertColumn(4, _T("Gamma"), LVCFMT_CENTER, 100);
  param_distribution_list.InsertColumn(5, _T("Beta"), LVCFMT_CENTER, 100);
  param_distribution_list.InsertColumn(6, _T("Weibull_min"), LVCFMT_CENTER, 100);
  param_distribution_list.InsertColumn(7, _T("Uniform"), LVCFMT_CENTER, 100);
  param_distribution_list.InsertColumn(8, _T("Poisson"), LVCFMT_CENTER, 100);
  param_distribution_list.InsertColumn(9, _T("Chi2"), LVCFMT_CENTER, 100);

  const int parameter_count = 5;
  CString param[parameter_count] = { _T("GPU Count"), _T("Walltime"), _T("Computation Load"), _T("Flavor"), _T("Preemetion") };
  for (int i = 0; i < parameter_count; ++i) {
    CString itemText;
    itemText.Format(param[i], i + 1);
    param_distribution_list.InsertItem(i, itemText);

    param_distribution_list.SetItemText(i, 1, _T("1")); // "Norm" 컬럼에 체크박스 설정
    for (int j = 2; j < 10; ++j) {
      param_distribution_list.SetItemText(i, j, _T(""));
    }
  }

  return TRUE;  // return TRUE unless you set the focus to a control
  // 예외: OCX 속성 페이지는 FALSE를 반환해야 합니다.
}


void log_gen_dialog::OnLvnItemchangedListCtlParamDist(NMHDR* pNMHDR, LRESULT* pResult)
{
  LPNMLISTVIEW pNMLV = reinterpret_cast<LPNMLISTVIEW>(pNMHDR);
  // TODO: 여기에 컨트롤 알림 처리기 코드를 추가합니다.
  *pResult = 0;
}

void log_gen_dialog::OnNMCustomDrawListCtrl(NMHDR* pNMHDR, LRESULT* pResult)
{
  LPNMLVCUSTOMDRAW pLVCD = reinterpret_cast<LPNMLVCUSTOMDRAW>(pNMHDR);

  if (pLVCD->nmcd.dwDrawStage == CDDS_PREPAINT)
  {
    *pResult = CDRF_NOTIFYITEMDRAW;
  }
  else if (pLVCD->nmcd.dwDrawStage == CDDS_ITEMPREPAINT)
  {
    *pResult = CDRF_NOTIFYSUBITEMDRAW;
  }
  else if (pLVCD->nmcd.dwDrawStage == CDDS_SUBITEM | CDDS_ITEMPREPAINT)
  {
    if (pLVCD->iSubItem >= 1 && pLVCD->iSubItem <= 9)
    {
      CRect rect;
      param_distribution_list.GetSubItemRect(pLVCD->nmcd.dwItemSpec, pLVCD->iSubItem, LVIR_BOUNDS, rect);
      CDC* pDC = CDC::FromHandle(pLVCD->nmcd.hdc);

      CRect checkboxRect = rect;
      checkboxRect.DeflateRect(5, 5);
      CPoint center = checkboxRect.CenterPoint();
      checkboxRect.left = center.x - 8;
      checkboxRect.right = center.x + 8;
      checkboxRect.top = center.y - 8;
      checkboxRect.bottom = center.y + 8;

      pDC->DrawFrameControl(&checkboxRect, DFC_BUTTON, DFCS_BUTTONCHECK |
        (param_distribution_list.GetItemText(pLVCD->nmcd.dwItemSpec, pLVCD->iSubItem) == _T("1") ? DFCS_CHECKED : 0));

      *pResult = CDRF_SKIPDEFAULT;
    }
    else
    {
      *pResult = CDRF_DODEFAULT;
    }
  }
}

void log_gen_dialog::GetSelectedCheckboxes(std::vector<distribution_type>& selected_dist)
{
  for (int i = 0; i < param_distribution_list.GetItemCount(); ++i)
  {
    for (int j = 1; j < param_distribution_list.GetHeaderCtrl()->GetItemCount(); ++j)
    {
      if (param_distribution_list.GetItemText(i, j) == _T("1"))
      {
        selected_dist.push_back(static_cast<distribution_type>(j - 1));
      }
    }
  }
}

void log_gen_dialog::OnClickListCtlParamDist(NMHDR* pNMHDR, LRESULT* pResult)
{
  LPNMITEMACTIVATE pNMItemActivate = reinterpret_cast<LPNMITEMACTIVATE>(pNMHDR);
  int row = pNMItemActivate->iItem;
  int col = pNMItemActivate->iSubItem;

  if (col >= 1 && col <= 9)
  {
    CString currentState = param_distribution_list.GetItemText(row, col);
    bool isChecked = (currentState == _T("1"));

    // 같은 열의 다른 항목 체크 해제
    for (int j = 1; j <= 9; ++j)
    {
      if (j != col)
      {
        param_distribution_list.SetItemText(row, j, _T(""));
      }
    }

    // 클릭한 항목 체크 상태 토글
    param_distribution_list.SetItemText(row, col, isChecked ? _T("") : _T("1"));

    // 리스트 컨트롤을 다시 그립니다.
    param_distribution_list.RedrawItems(row, row);
  }
  *pResult = 0;
}


void log_gen_dialog::OnBnClickedOk()
{
  GetSelectedCheckboxes(selected_parameter_distribution);
  CDialogEx::OnOK();
}
