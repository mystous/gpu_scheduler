#pragma once
#include "enum_definition.h"

namespace global_structure {
  struct scheduler_option {
    scheduler_type  scheduler_index = scheduler_type::mostallocated;
    bool            using_preemetion = false;
    bool            scheduleing_with_flavor_option = false;
    bool            working_till_end = true;
    bool            prevent_starvation = false;
    double          svp_upper = global_const::starvation_upper;
    double          age_weight = global_const::age_weight;
    int             reorder_count = global_const::dp_execution_maximum;
    int             preemption_task_window = global_const::defragmentation_criteria;
  };

  using scheduler_options = struct scheduler_option;
}