//Copyright [2020] [Indian Institute of Science, Bangalore & Tata Institute of Fundamental Research, Mumbai]
//SPDX-License-Identifier: Apache-2.0
#ifndef UPDATES_H_
#define UPDATES_H_

#include "models.h"
#include <vector>
#include <unordered_map> 
#include "train_loader.h"

double update_individual_lambda_h(const agent& node, int cur_time);

double update_individual_lambda_w(const agent& node, int cur_time);

double update_individual_lambda_c(const agent& node, int cur_time);

double update_individual_lambda_nbr_cell(const agent& node, int cur_time);

struct node_update_status{
  bool new_infection = false;
  bool new_symptomatic = false;
  bool new_hospitalization = false;
  bool new_infective = false;
};

//Returns whether the node was infected or turned symptomatic in this time step
node_update_status update_infection(agent& node, int cur_time);

void update_all_kappa(std::vector<agent>& nodes, 
                      std::vector<house>& homes,
                      std::vector<workplace>& workplaces, 
                      std::vector<community>& communities, 
                      matrix<nbr_cell>& nbr_cells, 
                      std::vector<intervention_params>& intv_params, 
                      int cur_time);

void updated_lambda_w_age_independent(const std::vector<agent>& nodes, 
                                      workplace& workplace);

void updated_lambda_h_age_independent(const std::vector<agent>& nodes, house& home);

double updated_travel_fraction(const std::vector<agent>& nodes, int cur_time);

void update_lambdas(agent&node, const std::vector<house>& homes, 
                    const std::vector<workplace>& workplaces, 
                    const std::vector<community>& communities, 
                    const std::vector<std::vector<nbr_cell>>& nbr_cells, 
                    const double travel_fraction, 
                    const int cur_time, 
                    std::unordered_map<count_type, std::vector<cohort_space>>& cohorts);

void updated_lambda_c_local(const std::vector<agent>& nodes, community& community);
void updated_lambda_c_local_random_community(const std::vector<agent>& nodes, 
                                              const std::vector<community>& communities, 
                                              std::vector<house>& houses);
void update_lambda_nbr_cells(const std::vector<agent>& nodes, 
                              std::vector<std::vector<nbr_cell>>& nbr_cells, 
                              const std::vector<house>& houses, 
                              const std::vector<community>& communities);

//Updating the cohort lambdas
void update_cohort_edge_weights(
      std::unordered_map<count_type, std::vector<cohort_space>>& cohorts,
      const std::vector<agent>& nodes);
void update_lambda_intra_cohort(
      std::unordered_map<count_type, std::vector<cohort_space>>& cohorts, 
      std::vector<agent>& nodes, int cur_time);
void update_lambda_inter_cohort(
    const std::unordered_map<count_type, std::vector<train_coach>>& am_coachs,
    const std::unordered_map<count_type, std::vector<train_coach>>& pm_coachs,
    std::unordered_map<count_type, std::vector<cohort_space>>& cohorts,
    const TrainLoader& trains, int cur_time);

//Update test request and test status
void update_test_request(std::vector<agent>& nodes,
                         const std::vector<house>& homes, 
                         const std::vector<workplace>& workplaces, 
                         const std::vector<community>& communities, 
                         std::vector<std::vector<nbr_cell>>& nbr_cells, 
                         const count_type current_time, 
                         const std::vector<testing_probability>& testing_protocol);
void update_test_status(std::vector<agent>& nodes, count_type current_time);


// Age stratification update functions.
void updated_lambda_w_age_dependent(const std::vector<agent>& nodes, 
                                    workplace& workplace, 
                                    const matrix<double>& workplace_tx_u, 
                                    const std::vector<double>& workplace_tx_sigma, 
                                    const matrix<double>& workplace_tx_vT);
void updated_lambda_project(const std::vector<agent>& nodes, workplace& workplace);

void updated_lambda_h_age_dependent(const std::vector<agent>& nodes, 
                                    house& home, 
                                    const matrix<double>& home_tx_u,
                                    const std::vector<double>& home_tx_sigma, 
                                    const matrix<double>& home_tx_vT);

std::vector<double> updated_lambda_c_local_age_dependent(
                      const std::vector<agent>& nodes, 
                      const community& community,
                      const matrix<double>& community_tx_u,
                      const std::vector<double>& community_tx_sigma,
                      const matrix<double>& community_tx_vT);

void update_lambda_c_global(std::vector<community>& communities, 
                            const matrix<double>& community_distance_matrix);

struct casualty_stats{
  count_type affected = 0;
  count_type hd_area_affected = 0;

  count_type susceptible = 0;
  count_type hd_area_susceptible = 0;
  count_type exposed = 0;
  count_type hd_area_exposed = 0;
  count_type infective = 0;
  count_type hd_area_infective = 0;
  count_type symptomatic = 0;
  count_type hd_area_symptomatic = 0;
  count_type hospitalised = 0;
  count_type hd_area_hospitalised = 0;
  count_type critical = 0;
  count_type hd_area_critical = 0;
  count_type dead = 0;
  count_type hd_area_dead = 0;
  count_type recovered = 0;
  count_type hd_area_recovered = 0;

  count_type recovered_from_infective = 0;
  count_type recovered_from_symptomatic = 0;
  count_type recovered_from_hospitalised = 0;
  count_type recovered_from_critical = 0;
  count_type hd_area_recovered_from_infective = 0;
  count_type hd_area_recovered_from_symptomatic = 0;
  count_type hd_area_recovered_from_hospitalised = 0;
  count_type hd_area_recovered_from_critical = 0;

};

casualty_stats get_infected_community(const std::vector<agent>& nodes, 
                                      const community& community);

void update_grid_cell_statistics(matrix<nbr_cell>& nbr_cells,
								 std::vector<house>& homes,
								 std::vector<agent>& nodes,
								 double locked_neighborhood_leakage,
								 double locked_neighborhood_threshold);

void update_individual_lambda_cohort(std::vector<agent>&nodes, 
                      const int cur_time, 
                      std::unordered_map<count_type, std::vector<cohort_space>>& cohorts);

#endif
