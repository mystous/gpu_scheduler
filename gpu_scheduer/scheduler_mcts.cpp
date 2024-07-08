#include "pch.h"
#include "scheduler_mcts.h"
#include <cmath>
#include <algorithm>
#include <limits>
#include <iostream>

scheduler_mcts::scheduler_mcts()
  : root(nullptr), simulation_count(1000), exploration_parameter(1.414), rng(std::random_device{}()) {}

scheduler_mcts::~scheduler_mcts() {
  clear_tree();
}

int scheduler_mcts::arrange_server(job_entry& job, accelator_type coprocessor) {
  clear_tree();
  root = std::make_unique<MCTSNode>(nullptr, -1, &job);

  for (int i = 0; i < simulation_count; i++) {
    MCTSNode* node = select_node(root.get());
    expand_node(node);
    double value = simulate(node);
    backpropagate(node, value);
  }

  int best_server = best_child(root.get());

  if (best_server != -1) {
    server_entry* target = &target_server->at(best_server);
    target->assign_accelator(&job, job.get_accelerator_count());
  }

  return best_server;
}

void scheduler_mcts::postproessing_set_server() {
  // 필요한 초기화 작업 수행
  simulation_count = 1000;
  exploration_parameter = 1.414;
}

scheduler_mcts::MCTSNode* scheduler_mcts::select_node(scheduler_mcts::MCTSNode* node) {
  while (!node->children.empty()) {
    node = std::max_element(node->children.begin(), node->children.end(),
      [=](const std::unique_ptr<scheduler_mcts::MCTSNode>& a, const std::unique_ptr<scheduler_mcts::MCTSNode>& b) {
        return calculate_ucb(node, a.get()) < calculate_ucb(node, b.get());
      })->get();
  }
  return node;
}

void scheduler_mcts::expand_node(MCTSNode* node) {
  for (size_t i = 0; i < target_server->size(); i++) {
    if (target_server->at(i).get_avaliable_accelator_count() >= node->job->get_accelerator_count()) {
      node->children.push_back(std::make_unique<MCTSNode>(node, i, node->job));
    }
  }
}

double scheduler_mcts::simulate(MCTSNode* node) {
  std::vector<server_entry> simulated_servers = *target_server;
  double total_utilization = 0;
  int allocated_jobs = 0;

  std::uniform_int_distribution<> dist(0, simulated_servers.size() - 1);

  for (int i = 0; i < 100; i++) {
    int random_server = dist(rng);
    if (simulated_servers[random_server].get_avaliable_accelator_count() >= node->job->get_accelerator_count()) {
      simulated_servers[random_server].assign_accelator(node->job, node->job->get_accelerator_count());
      total_utilization += simulated_servers[random_server].get_server_utilization();
      allocated_jobs++;
    }
  }

  return allocated_jobs > 0 ? total_utilization / allocated_jobs : 0;
}

void scheduler_mcts::backpropagate(MCTSNode* node, double value) {
  while (node != nullptr) {
    node->visits++;
    node->value += value;
    node = node->parent;
  }
}

int scheduler_mcts::best_child(MCTSNode* node) {
  auto best_child = std::max_element(node->children.begin(), node->children.end(),
    [](const std::unique_ptr<MCTSNode>& a, const std::unique_ptr<MCTSNode>& b) {
      return a->value / a->visits < b->value / b->visits;
    });

  return best_child != node->children.end() ? (*best_child)->server_index : -1;
}

double scheduler_mcts::calculate_ucb(MCTSNode* node, MCTSNode* child) {
  if (child->visits == 0) {
    return (std::numeric_limits<double>::max)();
  }
  return (child->value / child->visits) +
    exploration_parameter * std::sqrt(std::log(node->visits) / child->visits);
}

void scheduler_mcts::clear_tree() {
  root.reset();
}