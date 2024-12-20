﻿// gpu_log_dialog.cpp: 구현 파일
//

#include "pch.h"
#include "gpu_scheduer.h"
#include "afxdialogex.h"
#include "gpu_log_dialog.h"
#include "utility_class.h"

#include <atlbase.h>

using namespace std;

// gpu_log_dialog 대화 상자

IMPLEMENT_DYNAMIC(gpu_log_dialog, CDialog)

gpu_log_dialog::gpu_log_dialog(CWnd* pParent /*=nullptr*/)
	: CDialog(IDD_gpu_log_dialog, pParent)
{

}

gpu_log_dialog::~gpu_log_dialog()
{
}

void gpu_log_dialog::DoDataExchange(CDataExchange* pDX)
{
  CDialog::DoDataExchange(pDX);
  DDX_Control(pDX, IDC_LIST_JOB_LIST, job_list_ctrl);
}


BEGIN_MESSAGE_MAP(gpu_log_dialog, CDialog)
END_MESSAGE_MAP()


// gpu_log_dialog 메시지 처리기


INT_PTR gpu_log_dialog::DoModal()
{
    // TODO: 여기에 특수화된 코드를 추가 및/또는 기본 클래스를 호출합니다.

   
    return CDialog::DoModal();
}


BOOL gpu_log_dialog::OnInitDialog()
{
  CDialog::OnInitDialog();
  USES_CONVERSION;




  job_list_ctrl.InsertColumn(0, _T("pod_name"), LVCFMT_LEFT, 350);
  job_list_ctrl.InsertColumn(1, _T("pd_type"), LVCFMT_LEFT, 80);
  job_list_ctrl.InsertColumn(2, _T("GPU #"), LVCFMT_LEFT, 80);
  job_list_ctrl.InsertColumn(3, _T("start"), LVCFMT_LEFT, 250);
  job_list_ctrl.InsertColumn(4, _T("end"), LVCFMT_LEFT, 250);
  job_list_ctrl.InsertColumn(5, _T("wall time(min)"), LVCFMT_LEFT, 200);

  for (auto && job : *job_list) {
    int index = job_list_ctrl.InsertItem(job_list_ctrl.GetItemCount(), CA2T(job.get_pod_name().c_str()));
    job_list_ctrl.SetItemText(index, 1, job.get_job_type() == job_entry::job_type::task ? _T("task") : _T("instance"));
    job_list_ctrl.SetItemText(index, 2, CA2T(to_string(job.get_accelerator_count()).c_str()));

    job_list_ctrl.SetItemText(index, 3, CA2T(utility_class::conver_tp_str(job.get_start_tp()).c_str()));
    job_list_ctrl.SetItemText(index, 4, CA2T(utility_class::conver_tp_str(job.get_finish_tp()).c_str()));
    job_list_ctrl.SetItemText(index, 5, CA2T(utility_class::double_to_string(job.get_wall_time().count()).c_str()));
  }

  return TRUE;  // return TRUE unless you set the focus to a control
  // 예외: OCX 속성 페이지는 FALSE를 반환해야 합니다.
}
