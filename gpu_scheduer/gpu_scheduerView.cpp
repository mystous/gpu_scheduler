
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

void CgpuscheduerView::OnDraw(CDC* /*pDC*/)
{
	CgpuscheduerDoc* pDoc = GetDocument();
	ASSERT_VALID(pDoc);
	if (!pDoc)
		return;

	// TODO: add draw code for native data here
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
