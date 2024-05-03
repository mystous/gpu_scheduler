
// gpu_scheduerDoc.cpp : implementation of the CgpuscheduerDoc class
//

#include "pch.h"
#include "framework.h"
// SHARED_HANDLERS can be defined in an ATL project implementing preview, thumbnail
// and search filter handlers and allows sharing of document code with that project.
#ifndef SHARED_HANDLERS
#include "gpu_scheduer.h"
#endif

#include "gpu_scheduerDoc.h"
#include "CSchedulerOption.h"
#include "CGPUStatus.h"
#include "enum_definition.h"

#include <propkey.h>

#include <atlstr.h>
#include <string>

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

// CgpuscheduerDoc

IMPLEMENT_DYNCREATE(CgpuscheduerDoc, CDocument)

BEGIN_MESSAGE_MAP(CgpuscheduerDoc, CDocument)
    ON_COMMAND(ID_GPUSERVERSETTING_SHOWGPULIST, &CgpuscheduerDoc::OnGpuserversettingShowgpulist)
//  ON_COMMAND(ID_GPUSERVERSETTING_ADDGPU, &CgpuscheduerDoc::OnGpuserversettingAddgpu)
  ON_BN_CLICKED(IDC_BUTTON_ADD, &CgpuscheduerDoc::OnBnClickedButtonAdd)
  ON_COMMAND(ID_SERVERSETTING_RELOADSERVERLIST, &CgpuscheduerDoc::OnServersettingReloadserverlist)
    ON_COMMAND(ID_FILE_SAVE_AS, &CgpuscheduerDoc::OnFileSaveAs)
  ON_COMMAND(ID_FILE_SAVE, &CgpuscheduerDoc::OnFileSave)
END_MESSAGE_MAP()


// CgpuscheduerDoc construction/destruction

CgpuscheduerDoc::CgpuscheduerDoc() noexcept
{
	// TODO: add one-time construction code here

}

CgpuscheduerDoc::~CgpuscheduerDoc()
{
}

BOOL CgpuscheduerDoc::OnNewDocument()
{
	if (!CDocument::OnNewDocument())
		return FALSE;

  // TODO: 여기에 명령 처리기 코드를 추가합니다.
  CFileDialog dlg(TRUE, _T("csv"), NULL,
    OFN_HIDEREADONLY | OFN_FILEMUSTEXIST,
    _T("CSV Files (*.csv)|*.csv|All Files (*.*)|*.*||"));

  if (dlg.DoModal() == IDOK)
  {
    CString filePath = dlg.GetPathName();
    AfxGetApp()->OpenDocumentFile(filePath);

    bool preemtion_enabling = false;
    int scheduler_selection = 0;
    bool scheduler_with_flaver = false;
    bool working_till_end = false;

    CSchedulerOption dlg_option;
    dlg_option.set_option_value(&preemtion_enabling, &scheduler_selection, &scheduler_with_flaver, &working_till_end);
    if (dlg_option.DoModal() != IDOK) {
      AfxMessageBox(L"Select Scheduling method first!");
      return FALSE;
    }

    job_emulator_obj.build_job_list([&](CString filaname) -> string {
      CT2A asciiString(filaname);
      return std::string(asciiString);
      }(filePath), (scheduler_type)scheduler_selection, preemtion_enabling, scheduler_with_flaver, working_till_end);

    DWORD size = MAX_PATH;
    std::vector<TCHAR> currentDir(size);
    GetCurrentDirectory(size, &currentDir[0]);

    job_emulator_obj.build_job_queue();
    job_emulator_obj.build_server_list("server.csv");

    
  }

  SetModifiedFlag();
	// TODO: add reinitialization code here
	// (SDI documents will reuse this document)

	return TRUE;
}




// CgpuscheduerDoc serialization

//void CgpuscheduerDoc::Serialize(CArchive& ar)
//{
//	if (ar.IsStoring())
//	{
		// TODO: add storing code here
//	}
//	else
//	{
//
//	}
//}

#ifdef SHARED_HANDLERS

// Support for thumbnails
void CgpuscheduerDoc::OnDrawThumbnail(CDC& dc, LPRECT lprcBounds)
{
	// Modify this code to draw the document's data
	dc.FillSolidRect(lprcBounds, RGB(255, 255, 255));

	CString strText = _T("TODO: implement thumbnail drawing here");
	LOGFONT lf;

	CFont* pDefaultGUIFont = CFont::FromHandle((HFONT) GetStockObject(DEFAULT_GUI_FONT));
	pDefaultGUIFont->GetLogFont(&lf);
	lf.lfHeight = 36;

	CFont fontDraw;
	fontDraw.CreateFontIndirect(&lf);

	CFont* pOldFont = dc.SelectObject(&fontDraw);
	dc.DrawText(strText, lprcBounds, DT_CENTER | DT_WORDBREAK);
	dc.SelectObject(pOldFont);
}

// Support for Search Handlers
void CgpuscheduerDoc::InitializeSearchContent()
{
	CString strSearchContent;
	// Set search contents from document's data.
	// The content parts should be separated by ";"

	// For example:  strSearchContent = _T("point;rectangle;circle;ole object;");
	SetSearchContent(strSearchContent);
}

void CgpuscheduerDoc::SetSearchContent(const CString& value)
{
	if (value.IsEmpty())
	{
		RemoveChunk(PKEY_Search_Contents.fmtid, PKEY_Search_Contents.pid);
	}
	else
	{
		CMFCFilterChunkValueImpl *pChunk = nullptr;
		ATLTRY(pChunk = new CMFCFilterChunkValueImpl);
		if (pChunk != nullptr)
		{
			pChunk->SetTextValue(PKEY_Search_Contents, value, CHUNK_TEXT);
			SetChunkValue(pChunk);
		}
	}
}

#endif // SHARED_HANDLERS

// CgpuscheduerDoc diagnostics

#ifdef _DEBUG
void CgpuscheduerDoc::AssertValid() const
{
	CDocument::AssertValid();
}

void CgpuscheduerDoc::Dump(CDumpContext& dc) const
{
	CDocument::Dump(dc);
}
#endif //_DEBUG


// CgpuscheduerDoc commands


BOOL CgpuscheduerDoc::OnOpenDocument(LPCTSTR lpszPathName)
{
  if (!CDocument::OnOpenDocument(lpszPathName))
    return FALSE;

  

  return FALSE;
}


BOOL CgpuscheduerDoc::OnSaveDocument(LPCTSTR lpszPathName)
{
  AfxMessageBox(L"This application doesn't support save document", MB_ICONSTOP);

  return FALSE;

  //return CDocument::OnSaveDocument(lpszPathName);
}


void CgpuscheduerDoc::OnGpuserversettingShowgpulist()
{
  CGPUStatus dlg;
  dlg.set_server_list(job_emulator_obj.get_server_list());
  dlg.DoModal();
}


//void CgpuscheduerDoc::OnGpuserversettingAddgpu()
//{
  // TODO: 여기에 명령 처리기 코드를 추가합니다.
//}


void CgpuscheduerDoc::OnBnClickedButtonAdd()
{
  // TODO: 여기에 컨트롤 알림 처리기 코드를 추가합니다.
}


void CgpuscheduerDoc::OnServersettingReloadserverlist()
{

}


bool CgpuscheduerDoc::ReloadServerList()
{
  CFileDialog dlg(TRUE, _T("csv"), NULL,
    OFN_HIDEREADONLY | OFN_FILEMUSTEXIST,
    _T("CSV Files (*.csv)|*.csv|All Files (*.*)|*.*||"));

  if (dlg.DoModal() == IDOK)
  {
    USES_CONVERSION;
    CString filePath = dlg.GetPathName();
    string str_file = std::string(CT2CA(filePath));
    job_emulator_obj.build_server_list(str_file);
    return true;
  }
  return false;
}

void CgpuscheduerDoc::callback() {
  
}

void CgpuscheduerDoc::OnFileSaveAs()
{
  save_result();
}

void CgpuscheduerDoc::OnFileSave()
{
  save_result();
}

void CgpuscheduerDoc::save_result() {
  bool result = false;
  USES_CONVERSION;
  CFileDialog dlg(FALSE, _T("result"), A2CT(job_emulator_obj.get_savefile_candidate_name().c_str()),
    OFN_OVERWRITEPROMPT, _T("Emulation Result Files (*.result)|*.result|All Files (*.*)|*.*||"));

  if (dlg.DoModal() == IDOK)
  {
    CString filePath = dlg.GetPathName();
    string str_file = std::string(CT2CA(filePath));
    CWaitCursor *wait = new CWaitCursor();
    result = job_emulator_obj.save_result_log(str_file);
    delete wait;
  }

  if (result) {
    SetModifiedFlag(FALSE);
    AfxMessageBox(L"Result has been saved!", MB_ICONINFORMATION);
  }
  else {
    AfxMessageBox(L"Result was not saved!", MB_ICONSTOP);
  }
}