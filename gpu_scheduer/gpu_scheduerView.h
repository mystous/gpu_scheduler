
// gpu_scheduerView.h : interface of the CgpuscheduerView class
//

#pragma once

#include "call_back_object.h"


class CgpuscheduerView : public CView, public call_back_object
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
  afx_msg void OnEmulationShowjoblist();
  void DrawTotalInfo(CDC& dc, CRect& rect, job_emulator& job_emul, CPoint& start_position);
  void DrawColorText(CDC& dc, CString message, CString highlighted, COLORREF col, CPoint& start_position);
  pair<int, int> DrawGPUInfo(CDC& dc, CRect& rect, job_emulator& job_emul, CPoint& start_position);
  pair<int, int> DrawGPUSingleInfo(CDC& dc, CRect& rect, server_entry& server, CPoint& start_position);
  void DrawTotalAllocationRatio(CDC& dc, CRect& rect, CPoint start_position, int reserved, int total_count);
  CString FormatWithCommas(int value);
  afx_msg BOOL OnEraseBkgnd(CDC* pDC);
  afx_msg void OnServersettingReloadserverlist();
  afx_msg void OnButtonEmulStart();
  void StartEmul();
  afx_msg void OnButtonEmulPause();
  afx_msg void OnButtonEmulStop();
  virtual void function_call() override;
};

#ifndef _DEBUG  // debug version in gpu_scheduerView.cpp
inline CgpuscheduerDoc* CgpuscheduerView::GetDocument() const
   { return reinterpret_cast<CgpuscheduerDoc*>(m_pDocument); }
#endif

