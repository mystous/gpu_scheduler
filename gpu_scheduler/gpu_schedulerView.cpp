
// gpu_schedulerView.cpp : implementation of the CgpuschedulerView class
//

#include "pch.h"
#include "framework.h"
// SHARED_HANDLERS can be defined in an ATL project implementing preview, thumbnail
// and search filter handlers and allows sharing of document code with that project.
#ifndef SHARED_HANDLERS
#include "gpu_scheduler.h"
#endif

#include "gpu_schedulerDoc.h"
#include "gpu_schedulerView.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif


// CgpuschedulerView

IMPLEMENT_DYNCREATE(CgpuschedulerView, CView)

BEGIN_MESSAGE_MAP(CgpuschedulerView, CView)
	// Standard printing commands
	ON_COMMAND(ID_FILE_PRINT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_DIRECT, &CView::OnFilePrint)
	ON_COMMAND(ID_FILE_PRINT_PREVIEW, &CgpuschedulerView::OnFilePrintPreview)
	ON_WM_CONTEXTMENU()
	ON_WM_RBUTTONUP()
END_MESSAGE_MAP()

// CgpuschedulerView construction/destruction

CgpuschedulerView::CgpuschedulerView() noexcept
{
	// TODO: add construction code here

}

CgpuschedulerView::~CgpuschedulerView()
{
}

BOOL CgpuschedulerView::PreCreateWindow(CREATESTRUCT& cs)
{
	// TODO: Modify the Window class or styles here by modifying
	//  the CREATESTRUCT cs

	return CView::PreCreateWindow(cs);
}

// CgpuschedulerView drawing

void CgpuschedulerView::OnDraw(CDC* /*pDC*/)
{
	CgpuschedulerDoc* pDoc = GetDocument();
	ASSERT_VALID(pDoc);
	if (!pDoc)
		return;

	// TODO: add draw code for native data here
}


// CgpuschedulerView printing


void CgpuschedulerView::OnFilePrintPreview()
{
#ifndef SHARED_HANDLERS
	AFXPrintPreview(this);
#endif
}

BOOL CgpuschedulerView::OnPreparePrinting(CPrintInfo* pInfo)
{
	// default preparation
	return DoPreparePrinting(pInfo);
}

void CgpuschedulerView::OnBeginPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: add extra initialization before printing
}

void CgpuschedulerView::OnEndPrinting(CDC* /*pDC*/, CPrintInfo* /*pInfo*/)
{
	// TODO: add cleanup after printing
}

void CgpuschedulerView::OnRButtonUp(UINT /* nFlags */, CPoint point)
{
	ClientToScreen(&point);
	OnContextMenu(this, point);
}

void CgpuschedulerView::OnContextMenu(CWnd* /* pWnd */, CPoint point)
{
#ifndef SHARED_HANDLERS
	theApp.GetContextMenuManager()->ShowPopupMenu(IDR_POPUP_EDIT, point.x, point.y, this, TRUE);
#endif
}


// CgpuschedulerView diagnostics

#ifdef _DEBUG
void CgpuschedulerView::AssertValid() const
{
	CView::AssertValid();
}

void CgpuschedulerView::Dump(CDumpContext& dc) const
{
	CView::Dump(dc);
}

CgpuschedulerDoc* CgpuschedulerView::GetDocument() const // non-debug version is inline
{
	ASSERT(m_pDocument->IsKindOf(RUNTIME_CLASS(CgpuschedulerDoc)));
	return (CgpuschedulerDoc*)m_pDocument;
}
#endif //_DEBUG


// CgpuschedulerView message handlers
