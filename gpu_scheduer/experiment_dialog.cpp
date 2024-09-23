// experiment_dialog.cpp: 구현 파일
//

#include "pch.h"
#include "gpu_scheduer.h"
#include "afxdialogex.h"
#include "experiment_dialog.h"
#include <functional>
#include "utility_class.h"


// experiment_dialog 대화 상자

IMPLEMENT_DYNAMIC(experiment_dialog, CDialogEx)

experiment_dialog::experiment_dialog(CWnd* pParent /*=nullptr*/)
	: CDialogEx(IDD_experiment_dialog, pParent)
{

}

experiment_dialog::~experiment_dialog()
{
}

void experiment_dialog::DoDataExchange(CDataExchange* pDX)
{
  CDialogEx::DoDataExchange(pDX);
  DDX_Control(pDX, IDC_EDIT_ALPHA_INTERVAL, a_interval);
  DDX_Control(pDX, IDC_EDIT_ALPHA_MAX, a_max);
  DDX_Control(pDX, IDC_EDIT_ALPHA_MIN, a_min);
  DDX_Control(pDX, IDC_EDIT_BETA_INTERVAL, b_interval);
  DDX_Control(pDX, IDC_EDIT_BETA_MAX, b_max);
  DDX_Control(pDX, IDC_EDIT_BETA_MIN, b_min);
  DDX_Control(pDX, IDC_EDIT_D_INTERVAL, d_interval);
  DDX_Control(pDX, IDC_EDIT_D_MAX, d_max);
  DDX_Control(pDX, IDC_EDIT_D_MIN, d_min);
  DDX_Control(pDX, IDC_EDIT_W_INTERVAL, w_interval);
  DDX_Control(pDX, IDC_EDIT_W_MAX, w_max);
  DDX_Control(pDX, IDC_EDIT_W_MIN, w_min);
  DDX_Control(pDX, IDC_EDIT_NUM_THREAD, thread_count);
  DDX_Control(pDX, IDC_LIST_STATUS, perform_status);
  DDX_Control(pDX, IDC_STATIC_TH_STATUS, thread_status);
  DDX_Control(pDX, IDC_STATIC_HYPER_STATUS, hyper_status);
  DDX_Control(pDX, IDC_CHECK_COMPACT, compact_sch);
  DDX_Control(pDX, IDC_CHECK_MCTS, mcts_sch);
  DDX_Control(pDX, IDC_CHECK_MOSTWANTED, mostwanted_sch);
  DDX_Control(pDX, IDC_CHECK_RR, round_robin_sch);
  DDX_Control(pDX, IDC_EDIT_TASK_FILE_NAME, file_name_ctrl);
  DDX_Control(pDX, IDC_EDIT_SERVER_FILE_NAME, server_name_ctrl);
}


BEGIN_MESSAGE_MAP(experiment_dialog, CDialogEx)
  ON_BN_CLICKED(IDC_BUTTON_PICK_FILE, &experiment_dialog::OnClickedButtonPickFile)
  ON_BN_CLICKED(IDC_BUTTON_STOP, &experiment_dialog::OnClickedButtonStop)
  ON_BN_CLICKED(IDC_BUTTON_PAUSE, &experiment_dialog::OnClickedButtonPause)
  ON_BN_CLICKED(IDC_BUTTON_PERFORM, &experiment_dialog::OnClickedButtonPerform)
  ON_BN_CLICKED(IDC_BUTTON_PICK_SERVER, &experiment_dialog::OnClickedButtonPickServer)
END_MESSAGE_MAP()


// experiment_dialog 메시지 처리기


void experiment_dialog::OnOK()
{
  // TODO: 여기에 특수화된 코드를 추가 및/또는 기본 클래스를 호출합니다.

  CWaitCursor* wait = new CWaitCursor();

  delete wait;
  CDialogEx::OnOK();
}


void experiment_dialog::OnClickedButtonPickFile()
{
  CFileDialog dlg(TRUE, _T("csv"), NULL,
    OFN_HIDEREADONLY | OFN_FILEMUSTEXIST,
    _T("CSV Files (*.csv)|*.csv|All Files (*.*)|*.*||"));

  if (dlg.DoModal() == IDOK)
  {
    CString filePath = dlg.GetPathName();
    file_name_ctrl.SetWindowText(filePath);

    CT2A asciiString(filePath);
    task_file_name = string(asciiString);
  }
}


void experiment_dialog::OnClickedButtonStop()
{
  experiment_obj.stop_experiment();
  add_string_to_status("Experiment has been stoped.");
}


void experiment_dialog::OnClickedButtonPause()
{
  // TODO: 여기에 컨트롤 알림 처리기 코드를 추가합니다.
}

void experiment_dialog::function_call(thread::id id) {
  string message[2] = {"", ""};
  if (experiment_obj.call_back_from_thread(id, message[0], message[1])) {
    experiment_done = experiment_obj.get_complated_experiment();
    UpdateStaticInfo();
    add_string_to_status(message[0]);
    if (!message[1].empty()) {
      add_string_to_status(message[1]);
    }
    if (hyperparameter_searchspace.size() == experiment_done) {
      chrono::duration<double> elapsed_seconds = system_clock::now() - job_start_tp;
      auto elapsed_duration = chrono::duration_cast<std::chrono::seconds>(elapsed_seconds);
      string wall_time = "Experiment is finished!(Takes - " + utility_class::format_duration(elapsed_duration) + ")";
      add_string_to_status(wall_time);
    }
  }
}

void global_experiment_callback(void* object, thread::id id) {
  if (nullptr == object) { return; }
  experiment_dialog* view = (experiment_dialog*)object;

  view->function_call(id);
}

void global_message_callback(void* object, string message) {
  if (nullptr == object) { return; }
  experiment_dialog* view = (experiment_dialog*)object;

  view->message_callback(message);
}

void experiment_dialog::message_callback(string message) {
  add_string_to_status(message);
}

void experiment_dialog::OnClickedButtonPerform()
{
  function<void(void*, thread::id)> callback_func = global_experiment_callback;
  function<void(void*, string)> message_callback_func = global_message_callback;

  experiment_done = 0;
  UpdateHyperparameters();
  UpdateStaticInfo();
  perform_status.ResetContent();
  add_string_to_status("Experiment starting...");
  experiment_obj.set_hyperparameter(&hyperparameter_searchspace);
  if (experiment_obj.set_thread_count(thread_total)) {
    experiment_obj.set_call_back(callback_func);
    experiment_obj.set_call_back_obj((void*)this);
    experiment_obj.set_message_call_back(message_callback_func);
    experiment_obj.set_file_name(task_file_name, server_file_name);
    auto && strings = experiment_obj.start_experiment();
    add_string_to_status(strings);
    job_start_tp = system_clock::now();
    return;
  }

  AfxMessageBox(L"Experiment has been failed!", MB_ICONSTOP);
}

void experiment_dialog::add_string_to_status(vector<string> list) {
  for (auto&& message : list) {
    add_string_to_status(message);
  }
}

void experiment_dialog::add_string_to_status(string message) {
  int index = perform_status.InsertString(-1, CA2T(message.c_str()));
  perform_status.SetCurSel(index);
}

BOOL experiment_dialog::OnInitDialog()
{
  CDialogEx::OnInitDialog();

  SetIntValue(thread_total, &thread_count);
  SetIntValue(d_para[0], &d_min);
  SetIntValue(d_para[1], &d_max);
  SetIntValue(d_para[2], &d_interval);
  SetIntValue(w_para[0], &w_min);
  SetIntValue(w_para[1], &w_max);
  SetIntValue(w_para[2], &w_interval);
  SetDoubleValue(alpha_para[0], &a_min);
  SetDoubleValue(alpha_para[1], &a_max);
  SetDoubleValue(alpha_para[2], &a_interval);
  SetDoubleValue(beta_para[0], &b_min);
  SetDoubleValue(beta_para[1], &b_max);
  SetDoubleValue(beta_para[2], &b_interval);

  scheduler_ctrl[0] = &mostwanted_sch;
  scheduler_ctrl[1] = &compact_sch;
  scheduler_ctrl[2] = &round_robin_sch;
  scheduler_ctrl[3] = &mcts_sch;

  SetString(task_file_name, &file_name_ctrl);
  SetString(server_file_name, &server_name_ctrl);

  for (int i = 0; i < 4; ++i) {
    scheduler_ctrl[i]->SetCheck(sch[i]);
  }

  UpdateStaticInfo();
  return TRUE;  // return TRUE unless you set the focus to a control
  // 예외: OCX 속성 페이지는 FALSE를 반환해야 합니다.
}

void experiment_dialog::SetString(string text, CEdit* control) {
  CString message(CA2T(text.c_str()));
  control->SetWindowText(message);
}

void experiment_dialog::SetIntValue(int value, CEdit* control) {
  CString message;

  message.Format(_T("%d"), value);
  control->SetWindowText(message);
}

void experiment_dialog::SetDoubleValue(double value, CEdit* control) {
  CString message;

  message.Format(_T("%f"), value);
  control->SetWindowText(message);
}

void experiment_dialog::GetIntValue(int* value, CEdit* control) {
  CString value_str;

  control->GetWindowText(value_str);
  *value = _ttoi(value_str);
}

void experiment_dialog::GetDoubleValue(double* value, CEdit* control) {
  CString value_str;

  control->GetWindowText(value_str);
  *value = _ttof(value_str);
}

void experiment_dialog::UpdateStaticInfo() {

  CString message;

  message.Format(thread_notice, thread_total);
  thread_status.SetWindowText(message);

  message.Format(task_notice, hyperpara_total, experiment_done, hyperpara_total - experiment_done);
  hyper_status.SetWindowText(message);
}

void experiment_dialog::UpdateHyperparameters() {
  GetIntValue(&thread_total, &thread_count);
  GetIntValue(&(d_para[0]), &d_min);
  GetIntValue(&(d_para[1]), &d_max);
  GetIntValue(&(d_para[2]), &d_interval);
  GetIntValue(&(w_para[0]), &w_min);
  GetIntValue(&(w_para[1]), &w_max);
  GetIntValue(&(w_para[2]), &w_interval);
  GetDoubleValue(&(alpha_para[0]), &a_min);
  GetDoubleValue(&(alpha_para[1]), &a_max);
  GetDoubleValue(&(alpha_para[2]), &a_interval);
  GetDoubleValue(&(beta_para[0]), &b_min);
  GetDoubleValue(&(beta_para[1]), &b_max);
  GetDoubleValue(&(beta_para[2]), &b_interval);

  for (int i = 0; i < 4; ++i) {
    sch[i] = false;
    if (BST_CHECKED == scheduler_ctrl[i]->GetCheck()) {
      sch[i] = true;
    }
  }

  hyperparameter_searchspace.clear();
  vector<double> alpha_values = generate_double_values(alpha_para[0], alpha_para[1], alpha_para[2]);
  vector<double> beta_values = generate_double_values(beta_para[0], beta_para[1], beta_para[2]);
  vector<int> d_values = generate_int_values(d_para[0], d_para[1], d_para[2]);
  vector<int> w_values = generate_int_values(w_para[0], w_para[1], w_para[2]);

  for (int i = 0; i < 4; ++i) {
    if (!sch[i]) continue;

        global_structure::scheduler_option option;
        option.scheduler_index = static_cast<scheduler_type>(i);
        option.working_till_end = true;
        option.scheduleing_with_flavor_option = false;

        option.prevent_starvation = false;
        option.svp_upper = 0.;
        option.age_weight = 0.;
        option.using_preemetion = false;
        option.reorder_count = 0;
        option.preemption_task_window = 0;

        hyperparameter_searchspace.push_back(option);
  }

  for (int i = 0; i < 4; ++i) {
    if (!sch[i]) continue;

    for (double alpha : alpha_values) {
      for (double beta : beta_values) {
        global_structure::scheduler_option option;
        option.scheduler_index = static_cast<scheduler_type>(i);
        option.working_till_end = true;
        option.scheduleing_with_flavor_option = false;

        option.prevent_starvation = true;
        option.svp_upper = beta;
        option.age_weight = alpha;
        option.using_preemetion = false;
        option.reorder_count = 0;
        option.preemption_task_window = 0;

        hyperparameter_searchspace.push_back(option);
      }
    }
  }

  for (int i = 0; i < 4; ++i) {
    if (!sch[i]) continue;

    for (int d : d_values) {
      for (int w : w_values) {
        global_structure::scheduler_option option;
        option.scheduler_index = static_cast<scheduler_type>(i);
        option.working_till_end = true;
        option.scheduleing_with_flavor_option = false;

        option.prevent_starvation = false;
        option.svp_upper = 0.;
        option.age_weight = 0.;
        option.using_preemetion = true;
        option.reorder_count = d;
        option.preemption_task_window = w;

        hyperparameter_searchspace.push_back(option);
      }
    }
  }


  for (int i = 0; i < 4; ++i) {
    if (!sch[i]) continue;

    for (double alpha : alpha_values) {
      for (double beta : beta_values) {
        for (int d : d_values) {
          for (int w : w_values) {
            global_structure::scheduler_option option;
            option.scheduler_index = static_cast<scheduler_type>(i);
            option.working_till_end = true;
            option.scheduleing_with_flavor_option = false;

            option.prevent_starvation = true;
            option.svp_upper = beta;
            option.age_weight = alpha;
            option.using_preemetion = true;
            option.reorder_count = d;
            option.preemption_task_window = w;

            hyperparameter_searchspace.push_back(option);
          }
        }
      }
    }
  }

  hyperpara_total = hyperparameter_searchspace.size();
}

vector<double> experiment_dialog::generate_double_values(double start, double end, double step) {
  vector<double> values;
  for (double val = start; val <= end; val += step) {
    values.push_back(val);
  }
  return values;
}

vector<int> experiment_dialog::generate_int_values(int start, int end, int step) {
  vector<int> values;
  for (int val = start; val <= end; val += step) {
    values.push_back(val);
  }
  return values;
}


void experiment_dialog::OnClickedButtonPickServer()
{
  CFileDialog dlg(TRUE, _T("csv"), NULL,
    OFN_HIDEREADONLY | OFN_FILEMUSTEXIST,
    _T("CSV Files (*.csv)|*.csv|All Files (*.*)|*.*||"));

  if (dlg.DoModal() == IDOK)
  {
    CString filePath = dlg.GetPathName();
    server_name_ctrl.SetWindowText(filePath);

    CT2A asciiString(filePath);
    server_file_name = string(asciiString);
  }
}
