
// gpu_scheduerView.h : interface of the CgpuscheduerView class
//

#pragma once


class CgpuscheduerView : public CView
{
protected: // create from serialization only
	CgpuscheduerView() noexcept;
	DECLARE_DYNCREATE(CgpuscheduerView)

// Attributes
public:
	CgpuscheduerDoc* GetDocument() const;

// Operations
public:

// Overrides
public:
	virtual void OnDraw(CDC* pDC);  // overridden to draw this view
	virtual BOOL PreCreateWindow(CREATESTRUCT& cs);
protected:
	virtual BOOL OnPreparePrinting(CPrintInfo* pInfo);
	virtual void OnBeginPrinting(CDC* pDC, CPrintInfo* pInfo);
	virtual void OnEndPrinting(CDC* pDC, CPrintInfo* pInfo);

// Implementation
public:
	virtual ~CgpuscheduerView();
#ifdef _DEBUG
	virtual void AssertValid() const;
	virtual void Dump(CDumpContext& dc) const;
#endif

protected:

// Generated message map functions
protected:
	DECLARE_MESSAGE_MAP()
public:
  void DrawGPUStatus(CDC& dc, CRect& rect);
  afx_msg void OnEmulationStart();
  afx_msg void OnEmulationStop();
  afx_msg void OnEmulationSetting();
  afx_msg void OnEmulationSaveresult();
  afx_msg void OnEmulationPause();
};

#ifndef _DEBUG  // debug version in gpu_scheduerView.cpp
inline CgpuscheduerDoc* CgpuscheduerView::GetDocument() const
   { return reinterpret_cast<CgpuscheduerDoc*>(m_pDocument); }
#endif

