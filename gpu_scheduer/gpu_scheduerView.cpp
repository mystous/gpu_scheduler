
// gpu_scheduerView.cpp : implementation of the CgpuscheduerView class
//

#include "pch.h"
#include "framework.h"
// SHARED_HANDLERS can be defined in an ATL project implementing preview, thumbnail
// and search filter handlers and allows sharing of document code with that project.
#ifndef SHARED_HANDLERS
#include "gpu_scheduer.h"
#endif

#include "gpu_scheduerDoc.h"
#include "gpu_scheduerView.h"

#include "CSchedulerOption.h"
#include "gpu_log_dialog.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif


// CgpuscheduerView

IMPLEMENT_DYNCREATE(CgpuscheduerView, CView)

BEGIN_MESSAGE_MAP(CgpuscheduerView, CView)
	// Standard printing commands
	ON_COMMAND(ID_FILE_PRINT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_DIRECT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_PREVIEW, &CView::OnFilePrintPreview)
  ON_COMMAND(ID_EMULATION_START, &CgpuscheduerView::OnEmulationStart)
  ON_COMMAND(ID_EMULATION_STOP, &CgpuscheduerView::OnEmulationStop)
  ON_COMMAND(ID_EMULATION_SETTING, &CgpuscheduerView::OnEmulationSetting)
  ON_COMMAND(ID_EMULATION_SAVERESULT, &CgpuscheduerView::OnEmulationSaveresult)
  ON_COMMAND(ID_EMULATION_PAUSE, &CgpuscheduerView::OnEmulationPause)
  ON_COMMAND(ID_EMULATION_SHOWJOBLIST, &CgpuscheduerView::OnEmulationShowjoblist)
END_MESSAGE_MAP()

// CgpuscheduerView construction/destruction

CgpuscheduerView::CgpuscheduerView() noexcept
{
	// TODO: add construction code here

}

CgpuscheduerView::~CgpuscheduerView()
{
}

BOOL CgpuscheduerView::PreCreateWindow(CREATESTRUCT& cs)
{
	// TODO: Modify the Window class or styles here by modifying
	//  the CREATESTRUCT cs

	return CView::PreCreateWindow(cs);
}

// CgpuscheduerView drawing

void CgpuscheduerView::OnDraw(CDC* pDC)
{
	CgpuscheduerDoc* pDoc = GetDocument();
	ASSERT_VALID(pDoc);
	if (!pDoc)
		return;

  CRect rect;
  GetClientRect(&rect);
  int width = rect.Width();
  int height = rect.Height();

  CDC memDC;
  CBitmap bitmap;
  memDC.CreateCompatibleDC(pDC);
  bitmap.CreateCompatibleBitmap(pDC, width, height);
  CBitmap* pOldBitmap = memDC.SelectObject(&bitmap);

  memDC.FillSolidRect(&rect, RGB(255, 255, 255));

  DrawGPUStatus(memDC, rect);

  pDC->BitBlt(0, 0, width, height, &memDC, 0, 0, SRCCOPY);

  memDC.SelectObject(pOldBitmap);
  bitmap.DeleteObject();
  memDC.DeleteDC();
}


// CgpuscheduerView printing

BOOL CgpuscheduerView::OnPreparePrinting(CPrintInfo* pInfo)
{
	// default preparation
	return DoPreparePrinting(pInfo);
}

void CgpuscheduerView::OnBeginPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: add extra initialization before printing
}

void CgpuscheduerView::OnEndPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: add cleanup after printing
}


// CgpuscheduerView diagnostics

#ifdef _DEBUG
void CgpuscheduerView::AssertValid() const
{
	CView::AssertValid();
}

void CgpuscheduerView::Dump(CDumpContext& dc) const
{
	CView::Dump(dc);
}

CgpuscheduerDoc* CgpuscheduerView::GetDocument() const // non-debug version is inline
{
	ASSERT(m_pDocument->IsKindOf(RUNTIME_CLASS(CgpuscheduerDoc)));
	return (CgpuscheduerDoc*)m_pDocument;
}
#endif //_DEBUG


// CgpuscheduerView message handlers


void CgpuscheduerView::DrawGPUStatus(CDC& dc, CRect &rect)
{
  // TODO: 여기에 구현 코드 추가.
}


void CgpuscheduerView::OnEmulationStart()
{
  // TODO: 여기에 명령 처리기 코드를 추가합니다.
}


void CgpuscheduerView::OnEmulationStop()
{
  // TODO: 여기에 명령 처리기 코드를 추가합니다.
}


void CgpuscheduerView::OnEmulationSetting()
{
  // TODO: 여기에 명령 처리기 코드를 추가합니다.
  CgpuscheduerDoc* pDoc = (CgpuscheduerDoc*)m_pDocument;
  job_emulator& job_emul = pDoc->get_job_element_obj();

  CSchedulerOption dlg_option;

  dlg_option.scheduler_selection = (int)job_emul.get_selction_scheduler();
  dlg_option.using_preemtion = job_emul.get_preemtion_enabling();

  if (dlg_option.DoModal() == IDOK) {
    job_emul.set_option((job_emulator::scheduler_type)dlg_option.scheduler_selection, dlg_option.using_preemtion);
  }
}


void CgpuscheduerView::OnEmulationSaveresult()
{
  // TODO: 여기에 명령 처리기 코드를 추가합니다.
}


void CgpuscheduerView::OnEmulationPause()
{
  // TODO: 여기에 명령 처리기 코드를 추가합니다.
}


void CgpuscheduerView::OnEmulationShowjoblist()
{
  gpu_log_dialog  dlg;
  CgpuscheduerDoc* pDoc = (CgpuscheduerDoc*)m_pDocument;
  job_emulator& job_emul = pDoc->get_job_element_obj();

  dlg.set_job_list(job_emul.get_job_list_ptr());
  dlg.DoModal();
}
