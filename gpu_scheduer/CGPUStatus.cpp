// CGPUStatus.cpp: 구현 파일
//

#include "pch.h"
#include "gpu_scheduer.h"
#include "afxdialogex.h"
#include "CGPUStatus.h"
#include <string>

#include <atlbase.h>

using namespace std;

// CGPUStatus 대화 상자

IMPLEMENT_DYNAMIC(CGPUStatus, CDialog)

CGPUStatus::CGPUStatus(CWnd* pParent /*=nullptr*/)
	: CDialog(IDD_DIALOG_GPU_LIST, pParent)
{

}

CGPUStatus::~CGPUStatus()
{
}

void CGPUStatus::DoDataExchange(CDataExchange* pDX)
{
  CDialog::DoDataExchange(pDX);
  DDX_Control(pDX, IDC_LIST_GPU_SERVER, server_list_ctrl);
}


BEGIN_MESSAGE_MAP(CGPUStatus, CDialog)
END_MESSAGE_MAP()


// CGPUStatus 메시지 처리기


BOOL CGPUStatus::OnInitDialog()
{
  CDialog::OnInitDialog();
  USES_CONVERSION;

  server_list_ctrl.InsertColumn(0, _T("server_name"), LVCFMT_LEFT, 200);
  server_list_ctrl.InsertColumn(1, _T("accelator_type"), LVCFMT_LEFT, 150);
  server_list_ctrl.InsertColumn(2, _T("accelator #"), LVCFMT_LEFT, 150);


  for (auto&& server : *server_list) {
    int index = server_list_ctrl.InsertItem(server_list_ctrl.GetItemCount(), CA2T(server.get_server_name().c_str()));
    server_list_ctrl.SetItemText(index, 1, [](server_entry::accelator_type type)->LPCTSTR {
      switch (type) {
      case server_entry::accelator_type::a100:
        return _T("A100");
        break;
      case server_entry::accelator_type::a30:
        return _T("A30");
        break;
      case server_entry::accelator_type::cpu:
        return _T("CPU");
        break;
      default:
        return _T("CPU");
        break;
      }
      }(server.get_accelator_type()));
    server_list_ctrl.SetItemText(index, 2, CA2T(to_string(server.get_accelerator_count()).c_str()));
  }

  return TRUE;  // return TRUE unless you set the focus to a control
  // 예외: OCX 속성 페이지는 FALSE를 반환해야 합니다.
}
