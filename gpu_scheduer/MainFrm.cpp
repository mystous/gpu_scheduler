
// MainFrm.cpp : implementation of the CMainFrame class
//

#include "pch.h"
#include "framework.h"
#include "gpu_scheduer.h"

#include "MainFrm.h"
#include "CSchedulerOption.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

// CMainFrame

IMPLEMENT_DYNAMIC(CMainFrame, CMDIFrameWnd)

BEGIN_MESSAGE_MAP(CMainFrame, CMDIFrameWnd)
	ON_WM_CREATE()
  ON_COMMAND(ID_FILE_OPEN, &CMainFrame::OnFileOpen)
  ON_UPDATE_COMMAND_UI(ID_FILE_SAVE, &CMainFrame::OnUpdateFileSave)
//  ON_UPDATE_COMMAND_UI(ID_FILE_NEW, &CMainFrame::OnUpdateFileNew)
//  ON_COMMAND(ID_FILE_NEW, &CMainFrame::OnFileNew)
  ON_UPDATE_COMMAND_UI(ID_FILE_OPEN, &CMainFrame::OnUpdateFileOpen)
    ON_WM_CLOSE()
END_MESSAGE_MAP()

static UINT indicators[] =
{
	ID_SEPARATOR,           // status line indicator
	ID_INDICATOR_CAPS,
	ID_INDICATOR_NUM,
	ID_INDICATOR_SCRL,
};

// CMainFrame construction/destruction

CMainFrame::CMainFrame() noexcept
{
	// TODO: add member initialization code here
}

CMainFrame::~CMainFrame()
{
}

int CMainFrame::OnCreate(LPCREATESTRUCT lpCreateStruct)
{
	if (CMDIFrameWnd::OnCreate(lpCreateStruct) == -1)
		return -1;

	if (!m_wndToolBar.CreateEx(this, TBSTYLE_FLAT, WS_CHILD | WS_VISIBLE | CBRS_TOP | CBRS_GRIPPER | CBRS_TOOLTIPS | CBRS_FLYBY | CBRS_SIZE_DYNAMIC) ||
		!m_wndToolBar.LoadToolBar(IDR_MAINFRAME))
	{
		TRACE0("Failed to create toolbar\n");
		return -1;      // fail to create
	}

	if (!m_wndStatusBar.Create(this))
	{
		TRACE0("Failed to create status bar\n");
		return -1;      // fail to create
	}
	m_wndStatusBar.SetIndicators(indicators, sizeof(indicators)/sizeof(UINT));

	// TODO: Delete these three lines if you don't want the toolbar to be dockable
	m_wndToolBar.EnableDocking(CBRS_ALIGN_ANY);
	EnableDocking(CBRS_ALIGN_ANY);
	DockControlBar(&m_wndToolBar);

  WINDOWPLACEMENT wp;
  wp.length = sizeof(WINDOWPLACEMENT);
  CWinApp* pApp = AfxGetApp();
  wp.flags = pApp->GetProfileInt(_T("WindowPlacement"), _T("flags"), 0);
  wp.showCmd = pApp->GetProfileInt(_T("WindowPlacement"), _T("showCmd"), SW_SHOWNORMAL);
  wp.ptMinPosition.x = pApp->GetProfileInt(_T("WindowPlacement"), _T("ptMinPosition_x"), 0);
  wp.ptMinPosition.y = pApp->GetProfileInt(_T("WindowPlacement"), _T("ptMinPosition_y"), 0);
  wp.ptMaxPosition.x = pApp->GetProfileInt(_T("WindowPlacement"), _T("ptMaxPosition_x"), 0);
  wp.ptMaxPosition.y = pApp->GetProfileInt(_T("WindowPlacement"), _T("ptMaxPosition_y"), 0);
  wp.rcNormalPosition.left = pApp->GetProfileInt(_T("WindowPlacement"), _T("rcNormalPosition_left"), 0);
  wp.rcNormalPosition.top = pApp->GetProfileInt(_T("WindowPlacement"), _T("rcNormalPosition_top"), 0);
  wp.rcNormalPosition.right = pApp->GetProfileInt(_T("WindowPlacement"), _T("rcNormalPosition_right"), 0);
  wp.rcNormalPosition.bottom = pApp->GetProfileInt(_T("WindowPlacement"), _T("rcNormalPosition_bottom"), 0);

  // 크기와 위치 정보를 적용합니다.
  SetWindowPlacement(&wp);


	return 0;
}

BOOL CMainFrame::PreCreateWindow(CREATESTRUCT& cs)
{
	if( !CMDIFrameWnd::PreCreateWindow(cs) )
		return FALSE;
	// TODO: Modify the Window class or styles here by modifying
	//  the CREATESTRUCT cs

	return TRUE;
}

// CMainFrame diagnostics

#ifdef _DEBUG
void CMainFrame::AssertValid() const
{
	CMDIFrameWnd::AssertValid();
}

void CMainFrame::Dump(CDumpContext& dc) const
{
	CMDIFrameWnd::Dump(dc);
}
#endif //_DEBUG


// CMainFrame message handlers



void CMainFrame::OnFileOpen()
{
}


void CMainFrame::OnUpdateFileSave(CCmdUI* pCmdUI)
{

}


//void CMainFrame::OnUpdateFileNew(CCmdUI* pCmdUI)
//{
//}


//void CMainFrame::OnFileNew()
//{
//
//}


void CMainFrame::OnUpdateFileOpen(CCmdUI* pCmdUI)
{
  pCmdUI->Enable(FALSE);
}


void CMainFrame::OnClose()
{
  // 윈도우의 크기와 위치를 얻습니다.
  WINDOWPLACEMENT wp;
  wp.length = sizeof(WINDOWPLACEMENT);
  GetWindowPlacement(&wp);

  // 크기와 위치 정보를 레지스트리에 저장합니다.
  CWinApp* pApp = AfxGetApp();
  pApp->WriteProfileInt(_T("WindowPlacement"), _T("flags"), wp.flags);
  pApp->WriteProfileInt(_T("WindowPlacement"), _T("showCmd"), wp.showCmd);
  pApp->WriteProfileInt(_T("WindowPlacement"), _T("ptMinPosition_x"), wp.ptMinPosition.x);
  pApp->WriteProfileInt(_T("WindowPlacement"), _T("ptMinPosition_y"), wp.ptMinPosition.y);
  pApp->WriteProfileInt(_T("WindowPlacement"), _T("ptMaxPosition_x"), wp.ptMaxPosition.x);
  pApp->WriteProfileInt(_T("WindowPlacement"), _T("ptMaxPosition_y"), wp.ptMaxPosition.y);
  pApp->WriteProfileInt(_T("WindowPlacement"), _T("rcNormalPosition_left"), wp.rcNormalPosition.left);
  pApp->WriteProfileInt(_T("WindowPlacement"), _T("rcNormalPosition_top"), wp.rcNormalPosition.top);
  pApp->WriteProfileInt(_T("WindowPlacement"), _T("rcNormalPosition_right"), wp.rcNormalPosition.right);
  pApp->WriteProfileInt(_T("WindowPlacement"), _T("rcNormalPosition_bottom"), wp.rcNormalPosition.bottom);

  CMDIFrameWnd::OnClose();
}
