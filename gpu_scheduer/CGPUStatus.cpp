// CGPUStatus.cpp: 구현 파일
//

#include "pch.h"
#include "gpu_scheduer.h"
#include "afxdialogex.h"
#include "CGPUStatus.h"


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
}


BEGIN_MESSAGE_MAP(CGPUStatus, CDialog)
END_MESSAGE_MAP()


// CGPUStatus 메시지 처리기
