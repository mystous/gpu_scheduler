
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
#include "CGPUStatus.h"
#include <atlbase.h>
#include <string>
#include <algorithm>

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

using namespace std;

constexpr int font_size = 17;
constexpr int margin = 12;

constexpr COLORREF defaultColor = RGB(0, 0, 0);
constexpr COLORREF highlightColor = RGB(0, 0, 255);
constexpr COLORREF grayColor = RGB(112, 112, 112);
constexpr COLORREF ratioColor = RGB(102, 153, 255);


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
  ON_WM_ERASEBKGND()
  ON_COMMAND(ID_SERVERSETTING_RELOADSERVERLIST, &CgpuscheduerView::OnServersettingReloadserverlist)
  ON_COMMAND(ID_BUTTON_EMUL_START, &CgpuscheduerView::OnButtonEmulStart)
  ON_COMMAND(ID_BUTTON_EMUL_PAUSE, &CgpuscheduerView::OnButtonEmulPause)
  ON_COMMAND(ID_BUTTON_EMUL_STOP, &CgpuscheduerView::OnButtonEmulStop)
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
  constexpr int startx = 10, starty = 10;
  CPoint start_position(startx, starty);
  job_emulator& job_emul = GetDocument()->get_job_element_obj();
  CFont font;
  font.CreatePointFont(font_size * 10, _T("Times New Roman"));
  CFont* pOldFont = dc.SelectObject(&font);

  dc.SetBkMode(TRANSPARENT);

  DrawTotalInfo(dc, rect, job_emul, start_position);
  auto[reserved, total_count] = DrawGPUInfo(dc, rect, job_emul, start_position);
  DrawTotalAllocationRatio(dc, rect, CPoint(startx, starty), reserved, total_count);

  dc.SelectObject(pOldFont);
}


void CgpuscheduerView::OnEmulationStart()
{
  StartEmul();
}


void CgpuscheduerView::OnEmulationStop()
{
  // TODO: ���⿡ ��� ó���� �ڵ带 �߰��մϴ�.
}


void CgpuscheduerView::OnEmulationSetting()
{
  // TODO: ���⿡ ��� ó���� �ڵ带 �߰��մϴ�.
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
  // TODO: ���⿡ ��� ó���� �ڵ带 �߰��մϴ�.
}


void CgpuscheduerView::OnEmulationPause()
{
  // TODO: ���⿡ ��� ó���� �ڵ带 �߰��մϴ�.
}


void CgpuscheduerView::OnEmulationShowjoblist()
{
  gpu_log_dialog  dlg;
  CgpuscheduerDoc* pDoc = (CgpuscheduerDoc*)m_pDocument;
  job_emulator& job_emul = pDoc->get_job_element_obj();

  dlg.set_job_list(job_emul.get_job_list_ptr());
  dlg.DoModal();
}

void CgpuscheduerView::DrawTotalAllocationRatio(CDC& dc, CRect& rect, CPoint start_position, int reserved, int total_count) {
  CFont font;
  font.CreatePointFont(font_size * 20, _T("Arial"));
  CFont* pOldFont = dc.SelectObject(&font);

  CString allocation_rate, digit;
  digit.Format(_T("%-2.2f %%"), (double)reserved / (double)total_count * 100);
  allocation_rate.Format(_T("Total allocation: %s"), digit.GetBuffer());

  CPoint new_position(start_position.x + 900, start_position.y + 10);

  dc.SetTextColor(defaultColor);
  dc.TextOut(new_position.x, new_position.y, allocation_rate);
  DrawColorText(dc, allocation_rate, digit, highlightColor, new_position);
  dc.SetTextColor(defaultColor);

  dc.SelectObject(pOldFont);
}

void CgpuscheduerView::DrawTotalInfo(CDC& dc, CRect& rect, job_emulator& job_emul, CPoint &start_position)
{
  CString message, total_job, total_time_slot, temp;

  total_job = FormatWithCommas(job_emul.get_job_list_ptr()->size());
  total_time_slot = FormatWithCommas(job_emul.get_total_time_slot());

  message.Format(_T("Total Job : %s - Whole time slot(min) : %s"), total_job.GetBuffer(), total_time_slot.GetBuffer());

  
  dc.SetTextColor(defaultColor);
  dc.TextOut(start_position.x, start_position.y, message);
  DrawColorText(dc, message, total_job, highlightColor, start_position);
  DrawColorText(dc, message, total_time_slot, highlightColor, start_position);
 
  start_position.y += (font_size + margin);

  USES_CONVERSION;
  string filename = job_emul.get_job_file_name();
  temp = CA2T(filename.c_str());
  message.Format(_T("Job list base file : %s"), temp.GetBuffer());

  dc.SetTextColor(defaultColor);
  dc.TextOut(start_position.x, start_position.y, message);
  DrawColorText(dc, message, temp, grayColor, start_position);

  start_position.y += (font_size + margin);

  temp = FormatWithCommas(job_emul.get_server_list()->size());
  message.Format(_T("Server - #%s"), temp.GetBuffer());
  dc.SetTextColor(defaultColor);
  dc.TextOut(start_position.x, start_position.y, message);
  DrawColorText(dc, message, temp, highlightColor, start_position);

  start_position.y += 2* (font_size + margin);
}

std::pair<int, int> CgpuscheduerView::DrawGPUInfo(CDC& dc, CRect& rect, job_emulator& job_emul, CPoint& start_position) {
  vector<server_entry>* server_list = job_emul.get_server_list();

  constexpr int columun_count = 8;
  constexpr int box_width = 200;
  constexpr int box_gap = 20;

  CPoint local_position = start_position;
  CPoint local_rollback_pos = local_position;

  CFont font;
  font.CreatePointFont((font_size - 5 < 0 ? 10 : font_size - 5) * 10, _T("Times New Roman"));
  CFont* pOldFont = dc.SelectObject(&font);

  dc.SetTextColor(defaultColor);

  int total_reserved_count = 0, total_GPU_count = 0;

  int subindex = 0;
  for (int i = 0; i < server_list->size(); ++i) {
    if (0 == i % columun_count ) {
      local_position = local_rollback_pos;
      if (i > 0) {
        local_position.y += (box_width + box_gap);
      }
      local_rollback_pos = local_position;
      subindex = 0;
    }
    
    local_position.x = subindex++ * (box_width + box_gap) + box_gap;
    CRect server_rect(local_position.x, local_position.y, local_position.x + box_width, local_position.y + box_width);
    //server_entry server = server_list->at(i);
    auto[reserved_count, total_count] = DrawGPUSingleInfo(dc, server_rect, server_list->at(i), local_position);
    total_reserved_count += reserved_count;
    total_GPU_count += total_count;
  }

  int row = server_list->size() / columun_count + 1;
  start_position.y = ( row * box_width ) + ((row - 1)*box_gap);

  dc.SelectObject(pOldFont);

  return make_pair(total_reserved_count, total_GPU_count);
}

std::pair<int, int> CgpuscheduerView::DrawGPUSingleInfo(CDC& dc, CRect& rect, server_entry& server, CPoint& start_position) {
  USES_CONVERSION;
  dc.Rectangle(rect);

  CString temp(CA2T(server.get_server_name().c_str()));
  int textHeight = dc.GetTextExtent(temp.GetBuffer()).cy;
  int textYPos = rect.top + (rect.Height() * 0.1) - (textHeight / 2);
  int margin = 5;

  CSize sizeFirstLine = dc.GetTextExtent(temp);
  dc.TextOut(rect.left + (rect.Width() - sizeFirstLine.cx) / 2, textYPos, temp);

  CString strSecondLine = [](server_entry::accelator_type accelerator_type)->CString {
    switch (accelerator_type) {
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
    }}(server.get_accelator_type());
  
  CSize sizeSecondLine = dc.GetTextExtent(strSecondLine);
  dc.TextOut(rect.left + (rect.Width() - sizeSecondLine.cx) / 2, textYPos + textHeight + margin, strSecondLine);


  int boxSize = 20, boxSpacingW = 20, boxSpacingH = 10;

  int totalWidth = boxSize * 4 + boxSpacingW * 3;
  int totalHeight = boxSize * 2 + boxSpacingH;
  int startX = rect.left + (rect.Width() - totalWidth) / 2;
  int startY = rect.top + (rect.Height() - totalHeight) / 5 * 2;
  vector<bool>* reserved = server.get_reserved_status();

  int total_count = 0;
  int reserved_count = 0;
  for (int row = 0; row < 2; ++row)
  {
    for (int col = 0; col < 4; ++col)
    {
      CRect boxRect(
        startX + (boxSize + boxSpacingW) * col, 
        startY + (boxSize + boxSpacingH) * row, 
        startX + (boxSize + boxSpacingW) * col + boxSize, 
        startY + (boxSize + boxSpacingH) * row + boxSize);

      dc.Rectangle(boxRect);

      if (reserved->at(total_count)) {
        CRect newRect(CPoint(boxRect.left +1, boxRect.top +1), CPoint(boxRect.right -1, boxRect.bottom -1));
        dc.FillSolidRect(newRect, RGB(127, 255, 0));
        reserved_count++;
      }

      total_count++;
      if (total_count >= server.get_accelerator_count())
        break;
    }
    if (total_count >= server.get_accelerator_count())
      break;
  }

  CFont font;
  font.CreatePointFont(font_size * 16, _T("Arial"));
  CFont* pOldFont = dc.SelectObject(&font);

  CString allocation_rate;
  allocation_rate.Format(_T("%2.2f %%"), (double)reserved_count / (double)total_count * 100);

  textHeight = dc.GetTextExtent(allocation_rate.GetBuffer()).cy;
  textYPos = rect.top +160 - (textHeight / 2);


  dc.SetTextColor(ratioColor);
  sizeFirstLine = dc.GetTextExtent(allocation_rate);
  dc.TextOut(rect.left + (rect.Width() - sizeFirstLine.cx) / 2, textYPos, allocation_rate);
  dc.SetTextColor(defaultColor);

  dc.SelectObject(pOldFont);

  return make_pair(reserved_count, total_count);
}

void CgpuscheduerView::DrawColorText(CDC& dc, CString message, CString highlighted, COLORREF col, CPoint& start_position) {
  int startPos = message.Find(highlighted);
  if (startPos != -1)
  {
    CSize textSize = dc.GetTextExtent(message.Left(startPos));
    dc.SetTextColor(col);
    dc.TextOut(start_position.x + textSize.cx, start_position.y, highlighted);
  }
}

CString CgpuscheduerView::FormatWithCommas(int value) {
  std::string numStr = std::to_string(value);
  int insertPosition = numStr.length() - 3;

  while (insertPosition > 0) {
    numStr.insert(insertPosition, ",");
    insertPosition -= 3;
  }

  return CString(numStr.c_str());
}

BOOL CgpuscheduerView::OnEraseBkgnd(CDC* pDC)
{
  return TRUE;
}


void CgpuscheduerView::OnServersettingReloadserverlist()
{
  CgpuscheduerDoc* pDoc = (CgpuscheduerDoc*)m_pDocument;

  if (pDoc->ReloadServerList()) {
    Invalidate();
  }
}


void CgpuscheduerView::OnButtonEmulStart()
{
  StartEmul();
}


void CgpuscheduerView::StartEmul()
{
  job_emulator &emul = GetDocument()->get_job_element_obj();
  emul.start_progress();
}


void CgpuscheduerView::OnButtonEmulPause()
{
  job_emulator& emul = GetDocument()->get_job_element_obj();
  emul.pause_progress();

}


void CgpuscheduerView::OnButtonEmulStop()
{
  job_emulator& emul = GetDocument()->get_job_element_obj();
  emul.stop_progress();

}
