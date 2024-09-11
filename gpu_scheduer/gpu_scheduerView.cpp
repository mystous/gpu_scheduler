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
#include "enum_definition.h"
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
constexpr COLORREF whitegrayColor = RGB(214, 214, 214);
constexpr COLORREF ratioColor = RGB(102, 153, 255);
constexpr COLORREF greenColor = RGB(91, 194, 75);

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
//  ON_COMMAND(ID_FILE_SAVE_AS, &CgpuscheduerView::OnFileSaveAs)
ON_WM_HSCROLL()
END_MESSAGE_MAP()

// CgpuscheduerView construction/destruction


CgpuscheduerView::CgpuscheduerView() noexcept
{
	// TODO: add construction code here
}

CgpuscheduerView::~CgpuscheduerView()
{
  if (nullptr != old_bitmap_for_graph) {
    graph_dc.SelectObject(old_bitmap_for_graph);
  }
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

void CgpuscheduerView::function_call() {
  CRect rect;
  GetClientRect(&rect);
  InvalidateRect(rect);
}

void CgpuscheduerView::DrawGPUStatus(CDC& dc, CRect &rect)
{
  constexpr int startx = 10, starty = 10;
  CPoint start_position(startx, starty);
  job_emulator& job_emul = GetDocument()->get_job_element_obj();
  CFont font;
  font.CreatePointFont(font_size * 10, _T("Times New Roman"));
  CFont* pOldFont = dc.SelectObject(&font);

  dc.SetBkMode(TRANSPARENT);
  try {
    DrawTotalInfo(dc, rect, job_emul, start_position);
    auto [reserved, total_count] = DrawGPUInfo(dc, rect, job_emul, start_position);
    DrawTotalAllocationRatio(dc, rect, CPoint(startx, starty), reserved, total_count);
    DrawProgress(dc, rect, job_emul, start_position, reserved, total_count);
    DrawResult(dc, rect, job_emul, start_position);
  }
  catch (...) {}

  dc.SelectObject(pOldFont);
}

void CgpuscheduerView::OnEmulationStart()
{
  StartEmul();
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

  bool preemtion_enabling = job_emul.get_preemtion_enabling();
  int scheduler_selection = 0;
  bool scheduler_with_flaver = job_emul.get_scheduling_with_flavor_option();
  bool working_till_end = job_emul.get_finishing_condition();
  bool prevent_starvation = job_emul.get_prevent_starvation();

  dlg_option.set_option_value(&preemtion_enabling, &scheduler_selection, &scheduler_with_flaver, &working_till_end, &prevent_starvation);

  dlg_option.set_scheduler_type((int)job_emul.get_selction_scheduler());
  //dlg_option.using_preemtion = job_emul.get_preemtion_enabling();
  //dlg_option.scheduler_with_flavor = job_emul.get_scheduling_with_flavor_option();

  if (dlg_option.DoModal() == IDOK) {
    job_emul.set_option((scheduler_type)scheduler_selection, preemtion_enabling, scheduler_with_flaver, working_till_end, prevent_starvation);
  }
  Invalidate();
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

void CgpuscheduerView::DrawProgress(CDC& dc, CRect& rect, job_emulator& job_emul, CPoint& start_position, int reserved, int total_count) {
  CString message, total_job, total_time_slot, temp, progress, walltime, overhead, overheadtime;

  total_time_slot = FormatWithCommas(job_emul.get_total_time_slot());
  total_job = FormatWithCommas(job_emul.get_emulation_step() + 1);
  progress.Format(_T("%-2.2f %%"), (double)(job_emul.get_emulation_step() + 1) / (double)job_emul.get_total_time_slot() * 100);
  USES_CONVERSION;
  walltime = CA2T(job_emul.get_job_elapsed_time_string().c_str());
  overhead.Format(_T("%d times"), job_emul.get_job_adjust_count());
  overheadtime.Format(_T("%d mins"), job_emul.get_job_adjust_overhead_time());

  message.Format(_T("Progress : %s / %s (%s), Elapsed time - %s, Emulation walltime - %s, Pool Adjusting Overhead - %s (%s)"), 
    total_job.GetBuffer(), total_time_slot.GetBuffer(), progress.GetBuffer(),
    [](int minutes) {
      std::wstringstream ss;
      ss << std::setw(2) << std::setfill(L'0') << minutes / 1440 << L" Day(s) "
        << std::setw(2) << std::setfill(L'0') << (minutes % 1440) / 60 << L":"
        << std::setw(2) << std::setfill(L'0') << minutes % 60;
      return CString(ss.str().c_str());
    }(job_emul.get_emulation_step() + 1).GetBuffer(), 
    walltime.GetBuffer(), overhead.GetBuffer(), overheadtime.GetBuffer());

  start_position.y -= 60;
  dc.SetTextColor(defaultColor);
  dc.TextOut(start_position.x, start_position.y, message);
  DrawColorText(dc, message, progress, highlightColor, start_position);

  start_position.y += (font_size + margin);
  const int plot_width = 1750;
  const int plot_height = 300;

  CRect plotr_rect(start_position.x, start_position.y, start_position.x + plot_width, start_position.y + plot_height);
  int column_count = 20;
  int row_count = 5, i;

  CPen gray_pen(PS_DOT, 1, whitegrayColor);
  CPen* old_pen = dc.SelectObject(&gray_pen);

  for (i = 0; i < row_count - 1; ++i) {
    dc.MoveTo(start_position.x, start_position.y + (double)(plot_height /  row_count) * (i+1));
    dc.LineTo(start_position.x + plot_width, start_position.y + (double)(plot_height / row_count) * (i + 1));
  }

  for (i = 0; i < column_count - 1; ++i) {
    dc.MoveTo(start_position.x + (double)(plot_width / column_count) * (i + 1), start_position.y );
    dc.LineTo(start_position.x + (double)(plot_width / column_count) * (i + 1), start_position.y + plot_height);
  }

  dc.SelectObject(old_pen);

  double* allocation_rate = job_emul.get_allocation_rate();
  double* utilization_rate = job_emul.get_utilization_rate();

  if (emulation_status::start != job_emul.get_emulation_status() &&
    nullptr != allocation_rate && nullptr != utilization_rate) {

    draw_buffer(dc, start_position, allocation_rate, utilization_rate, job_emul, plot_width, plot_height);
    dc.BitBlt(start_position.x, start_position.y, plot_width, plot_height, &graph_dc, 0, 0, SRCCOPY);
  }

  CBrush* old_brush = (CBrush*)dc.SelectStockObject(NULL_BRUSH);
  dc.Rectangle(plotr_rect);
  dc.SelectObject(old_brush);

  start_position.y += plot_height;
  start_position.y += margin;

  vector<int> request;
  job_emul.get_wait_job_request_acclerator(request);
  int queue_stack_size = request.size();
  CString wait_queue = _T("");
  CString wait_queue_title;
  for (auto&& count : request) {
    CString request_count;
    if (-1 != count) {
      request_count.Format(_T("%d, "), count);
    }
    else {
      request_count = _T(" | ");
      queue_stack_size--;
    }
    wait_queue += request_count;
  }
  wait_queue_title.Format(_T("Waiting job request acclerator(%d): %s"), queue_stack_size, wait_queue.GetBuffer());


  dc.SetTextColor(defaultColor);
  dc.TextOut(start_position.x, start_position.y, wait_queue_title);
  start_position.y += (font_size + margin);
}

void CgpuscheduerView::draw_buffer(CDC& dc, const CPoint& start_position, double* allocation_rate, double* utilization_rate, 
  job_emulator &job_emul, const int plot_width, const int plot_height) {
  if (is_buffer_created) {
    return;
  }

  CRect rect(0, 0, plot_width, plot_height);
  int i;
  int pre_x = 0;
  int pre_y = plot_height;
  int slot_count = job_emul.get_done_emulation_step() + 2;
  double scale_x = plot_width / (double)slot_count;
  double scale_y = plot_height / 100.0;

  if (!is_grapch_dc_created) {
    graph_dc.CreateCompatibleDC(&dc);
    graph_bitmap.CreateCompatibleBitmap(&dc, plot_width, plot_height);
    old_bitmap_for_graph = graph_dc.SelectObject(&graph_bitmap);
    is_grapch_dc_created = true;
  }
  graph_dc.FillSolidRect(&rect, RGB(255, 255, 255));

  int column_count = 20;
  int row_count = 5;

  CPen gray_pen(PS_DOT, 1, whitegrayColor);
  CPen* old_pen = graph_dc.SelectObject(&gray_pen);

  for (i = 0; i < row_count - 1; ++i) {
    graph_dc.MoveTo(0, (double)(plot_height / row_count) * (i + 1));
    graph_dc.LineTo(plot_width, (double)(plot_height / row_count) * (i + 1));
  }

  for (i = 0; i < column_count - 1; ++i) {
    graph_dc.MoveTo((double)(plot_width / column_count) * (i + 1), 0);
    graph_dc.LineTo((double)(plot_width / column_count) * (i + 1), plot_height);
  }

  graph_dc.SelectObject(old_pen);

  //int allocation_rate_index = job_emul.get_rate_index();
  int allocation_rate_index = job_emul.get_done_emulation_step();

  CPen green_pen(PS_SOLID, 2, greenColor);
  old_pen = graph_dc.SelectObject(&green_pen);
  for (i = 0; i < allocation_rate_index; ++i)
  {
    int x = (int)((i + 1) * scale_x);
    int y = (int)((100.0 - allocation_rate[i]) * scale_y);
    graph_dc.MoveTo(pre_x, pre_y);
    graph_dc.LineTo(x, y);
    pre_x = x;
    pre_y = y;
  }
  graph_dc.SelectObject(old_pen);

  pre_x = 0;
  pre_y = plot_height;
  for (i = 0; i < allocation_rate_index; ++i)
  {
    int x = (int)((i + 1) * scale_x);
    int y = (int)((100.0 - utilization_rate[i]) * scale_y);
    graph_dc.MoveTo(pre_x, pre_y);
    graph_dc.LineTo(x, y);
    pre_x = x;
    pre_y = y;
  }

  CString message, time;
  
  time = [](int minutes) {
    std::wstringstream ss;
    ss << std::setw(2) << std::setfill(L'0') << minutes / 1440 << L" Day(s) "
      << std::setw(2) << std::setfill(L'0') << (minutes % 1440) / 60 << L":"
      << std::setw(2) << std::setfill(L'0') << minutes % 60;
    return CString(ss.str().c_str());
    }(job_emul.get_done_emulation_step() + 1).GetBuffer();

  message.Format(_T("Total emulation time: %s"), time.GetBuffer());

  CFont font;
  font.CreatePointFont(font_size * 8, _T("Arial"));
  CFont* pOldFont = graph_dc.SelectObject(&font);

  CPoint text_position(10, 10);
  graph_dc.SetTextColor(defaultColor);
  graph_dc.TextOut(text_position.x, text_position.y, message);
  DrawColorText(graph_dc, message, time, highlightColor, text_position);
  graph_dc.SelectObject(pOldFont);

  is_buffer_created = true;
}

void CgpuscheduerView::DrawTotalAllocationRatio(CDC& dc, CRect& rect, CPoint start_position, int reserved, int total_count) {
  CFont font;
  font.CreatePointFont(font_size * 20, _T("Arial"));
  CFont* pOldFont = dc.SelectObject(&font);

  CString allocation_rate, digit;
  digit.Format(_T("%-2.2f %%"), (double)reserved / (double)total_count * 100);
  allocation_rate.Format(_T("Total allocation: %s"), digit.GetBuffer());

  CPoint new_position(start_position.x + 1200, start_position.y + 10);

  dc.SetTextColor(defaultColor);
  dc.TextOut(new_position.x, new_position.y, allocation_rate);
  DrawColorText(dc, allocation_rate, digit, highlightColor, new_position);
  dc.SetTextColor(defaultColor);

  dc.SelectObject(pOldFont);
}

void CgpuscheduerView::DrawTotalInfo(CDC& dc, CRect& rect, job_emulator& job_emul, CPoint &start_position)
{
  CString message, total_job, total_time_slot, temp, scheduler_name, with_flavor, working_duration, preemption_enabling, starvation_prevention;

  total_job = FormatWithCommas(static_cast<int>(job_emul.get_job_list_ptr()->size()));
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

  temp = FormatWithCommas(static_cast<int>(job_emul.get_server_list()->size()));
  scheduler_name = A2CT(job_emul.get_setting_scheduling_name().c_str());
  with_flavor = job_emul.get_scheduling_with_flavor_option() ? _T("with flavor") : _T("one queue");
  working_duration = job_emul.get_finishing_condition() ? _T("working till the end") : _T("within timeslot");
  starvation_prevention = job_emul.get_starvation_prevention_option() ? _T("starvation prevention") : _T("wait until scheduling");
  preemption_enabling = job_emul.get_preemtion_enabling() ? _T("preemption enabling") : _T("without pool adjusting");
  message.Format(_T("Server - #%s, Scheduler: %s, %s, %s, %s, %s"), 
    temp.GetBuffer(), scheduler_name.GetBuffer(), with_flavor.GetBuffer(), working_duration.GetBuffer(), starvation_prevention.GetBuffer(), preemption_enabling.GetBuffer());
  dc.SetTextColor(defaultColor);
  dc.TextOut(start_position.x, start_position.y, message);
  DrawColorText(dc, message, temp, highlightColor, start_position);
  DrawColorText(dc, message, scheduler_name, highlightColor, start_position);
  DrawColorText(dc, message, with_flavor, highlightColor, start_position);
  DrawColorText(dc, message, working_duration, highlightColor, start_position);
  DrawColorText(dc, message, starvation_prevention, highlightColor, start_position);
  DrawColorText(dc, message, preemption_enabling, highlightColor, start_position);
  

  start_position.y += 2* (font_size + margin);
}

void CgpuscheduerView::DrawResult(CDC& dc, CRect& rect, job_emulator& job_emul, CPoint& start_position) {
  CString message, wait_job, remain_job, total_finished_job, total_scheduled_job;

  total_scheduled_job = FormatWithCommas(job_emul.get_scheduled_job_count());
  remain_job = FormatWithCommas(job_emul.get_remain_job_count());
  wait_job = FormatWithCommas(job_emul.get_wait_job_count());

  message.Format(_T("Processing : %s , Remainded : %s, Job in wait queue : %s"), 
    total_scheduled_job.GetBuffer(), remain_job.GetBuffer(), wait_job.GetBuffer());
  //message.Format(_T("Remainded : %s"), remain_job.GetBuffer());


  dc.SetTextColor(defaultColor);
  dc.TextOut(start_position.x, start_position.y, message);
  DrawColorText(dc, message, total_scheduled_job, highlightColor, start_position);
  DrawColorText(dc, message, remain_job, highlightColor, start_position);
  DrawColorText(dc, message, wait_job, highlightColor, start_position);

  start_position.y += (font_size + margin);
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

  int row = static_cast<int>(server_list->size()) / columun_count + 1;
  start_position.y = ( ( row + 1 ) * box_width ) + ((row - 1)*box_gap);

  dc.SelectObject(pOldFont);

  return make_pair(total_reserved_count, total_GPU_count);
}

std::pair<int, int> CgpuscheduerView::DrawGPUSingleInfo(CDC& dc, CRect& rect, server_entry& server, CPoint& start_position) {
  USES_CONVERSION;
  dc.Rectangle(rect);

  CString temp(CA2T(server.get_server_name().c_str()));
  int textHeight = dc.GetTextExtent(temp.GetBuffer()).cy;
  int textYPos = rect.top + static_cast<int>(rect.Height() * 0.1) - (textHeight / 2);
  int margin = 5;

  CSize sizeFirstLine = dc.GetTextExtent(temp);
  dc.TextOut(rect.left + (rect.Width() - sizeFirstLine.cx) / 2, textYPos, temp);

  CString strSecondLine = [](accelator_type accelerator_type)->CString {
    switch (accelerator_type) {
    case accelator_type::a100:
      return _T("A100");
      break;
    case accelator_type::a30:
      return _T("A30");
      break;
    case accelator_type::h100:
      return _T("H100");
      break;
    case accelator_type::h200:
      return _T("H200");
      break;
    case accelator_type::cpu:
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

  CString strJobCount;
  strJobCount.Format(_T("%d jobs loaded"), server.get_loaded_job_count());
  CSize sizeJobCountLine = dc.GetTextExtent(strJobCount);
  textYPos = rect.top + 110 - (textHeight / 2);
  dc.TextOut(rect.left + (rect.Width() - sizeJobCountLine.cx) / 2, textYPos + textHeight + margin, strJobCount);


  CFont font;
  font.CreatePointFont(font_size * 16, _T("Arial"));
  CFont* pOldFont = dc.SelectObject(&font);

  CString allocation_rate;
  allocation_rate.Format(_T("%2.2f %%"), (double)reserved_count / (double)total_count * 100);

  textHeight = dc.GetTextExtent(allocation_rate.GetBuffer()).cy;
  textYPos = rect.top +170 - (textHeight / 2);

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
  int insertPosition = static_cast<int>(numStr.length()) - 3;

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


void global_callback(void *object) {
  if (nullptr == object) { return; }
  CgpuscheduerView* view = (CgpuscheduerView*)object;

  view->function_call();
}

void CgpuscheduerView::StartEmul()
{
  job_emulator &emul = GetDocument()->get_job_element_obj() ;

  std::function<void(void*)> callback_func = global_callback;
  emul.set_callback(callback_func, (void*)this);
  GetDocument()->SetModifiedFlag(TRUE);
  is_buffer_created = false;
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



void CgpuscheduerView::OnHScroll(UINT nSBCode, UINT nPos, CScrollBar* pScrollBar)
{
  // TODO: 여기에 메시지 처리기 코드를 추가 및/또는 기본값을 호출합니다.

  __super::OnHScroll(nSBCode, nPos, pScrollBar);
}


