set -e
cd ../../../ #到federatedscope目录

# basic configuration
method=FedProto #Local FedProto FML FedGH

script_floder="model_heterogeneity/SFL_methods/"${method}
result_folder_name="time_consumption_result_1112"
result_floder=model_heterogeneity/result/${result_folder_name}

# common hyperparameters
gpu=0
data='pubmed'
client_num=5
local_update_step=4
optimizer='SGD'
seed=0
lr=0.25
total_round=200
patience=200
momentum=0.9
freq=1
global_eval=False
local_eval_whole_test_dataset=True

# Define function for model training
train_model() {
  python main.py --cfg ${main_cfg} \--client_cfg ${client_cfg} \
    federate.client_num ${client_num} \
    federate.make_global_eval ${global_eval} \
    data.local_eval_whole_test_dataset ${local_eval_whole_test_dataset} \
    seed ${seed} \
    train.local_update_steps ${local_update_step} \
    train.optimizer.lr ${lr} \
    federate.total_round_num ${total_round} \
    train.optimizer.type ${optimizer} \
    train.optimizer.momentum ${momentum} \
    device ${gpu} \
    early_stop.patience ${patience} \
    result_floder ${result_floder} \
    exp_name ${exp_name} \
    eval.freq ${freq} \
    show_detailed_communication_info False \
    vis_embedding False
}

main_cfg=$script_floder"/"$method"_on_"$data".yaml"
client_cfg="model_heterogeneity/model_settings/"$client_num"_Heterogeneous_GNNs.yaml"
exp_name="time_consumption_"$method"_on_"$data"_"$client_num"_clients"
train_model

