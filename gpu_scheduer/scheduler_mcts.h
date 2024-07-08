#pragma once
#include "job_scheduler.h"
#include <vector>
#include <memory>
#include <random>

class scheduler_mcts : public job_scheduler {
public:
  scheduler_mcts();
  virtual ~scheduler_mcts();
  virtual int arrange_server(job_entry& job, accelator_type coprocessor = accelator_type::any) override;
protected:
  virtual void postproessing_set_server() override;

private:
  struct MCTSNode {
    std::vector<std::unique_ptr<MCTSNode>> children;
    MCTSNode* parent;
    int visits;
    double value;
    int server_index;
    job_entry* job;

    MCTSNode(MCTSNode* parent, int server_index, job_entry* job)
      : parent(parent), visits(0), value(0), server_index(server_index), job(job) {}
  };

  std::unique_ptr<MCTSNode> root;
  int simulation_count;
  double exploration_parameter;
  std::mt19937 rng;

  MCTSNode* select_node(MCTSNode* node);
  void expand_node(MCTSNode* node);
  double simulate(MCTSNode* node);
  void backpropagate(MCTSNode* node, double value);
  int best_child(MCTSNode* node);
  double calculate_ucb(MCTSNode* node, MCTSNode* child);
  void clear_tree();
};