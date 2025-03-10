# --------------
# --------------------
# Project: Learning to Compare: Relation Network for Few-Shot Learning
# Date: 2017.9.21
# Author: Flood Sung
# All Rights Reserved
# -------------------------------------
import gc

import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
from torch.optim.lr_scheduler import StepLR
import numpy as np
import task_generator as tg
import os
import math
import argparse
import random


from src.efficient_kan import KAN
from src import fullconnect
import CNNEncoder1
import vit
from src.fullconnect import FullyConnectedLayer
from tripletloss.tripletloss import TripletLoss

parser = argparse.ArgumentParser(description="One Shot Visual Recognition")
parser.add_argument("-f", "--feature_dim", type=int, default=128)
parser.add_argument("-r", "--relation_dim", type=int, default=8)
parser.add_argument("-w", "--class_num", type=int, default=2)
parser.add_argument("-s", "--sample_num_per_class", type=int, default=1)
parser.add_argument("-b", "--batch_num_per_class", type=int, default=4)
parser.add_argument("-e", "--episode", type=int, default=2000)
parser.add_argument("-t", "--test_episode", type=int, default=100)
parser.add_argument("-l", "--learning_rate", type=float, default=0.001)
parser.add_argument("-g", "--gpu", type=int, default=0)
parser.add_argument("-u", "--hidden_unit", type=int, default=10)
parser.add_argument("-c", "--cpu", type=int, default=0)
args = parser.parse_args()

# Hyper Parameters
FEATURE_DIM = args.feature_dim
RELATION_DIM = args.relation_dim
CLASS_NUM = args.class_num
SAMPLE_NUM_PER_CLASS = args.sample_num_per_class
BATCH_NUM_PER_CLASS = args.batch_num_per_class
EPISODE = args.episode
TEST_EPISODE = args.test_episode
LEARNING_RATE = args.learning_rate
GPU = args.gpu
HIDDEN_UNIT = args.hidden_unit

test_result = './test_result/'

label_list = ['Health', 'anomaly']


def weights_init(m):
    classname = m.__class__.__name__
    if classname.find('Conv') != -1:
        n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
        m.weight.data.normal_(0, math.sqrt(2. / n))
        if m.bias is not None:
            m.bias.data.zero_()
    elif classname.find('BatchNorm') != -1:
        m.weight.data.fill_(1)
        m.bias.data.zero_()
    elif classname.find('Linear') != -1:
        n = m.weight.size(1)
        m.weight.data.normal_(0, 0.01)
        m.bias.data = torch.ones(m.bias.data.size())


def main():
    loos_result = []
    loos_result_1 = []
    accuray_result_1_1 = []
    # Step 1: init data folders
    print("init data folders")
    print("init neural networks")

    # 定义化网络
    # 关系网络和特征提取模块的加载话
    #    feature_encoder.apply(weights_init)
    #   relation_network.apply(weights_init)
    gearbox_feature_encoder = CNNEncoder1.rsnet()  # 特征提取
    gearbox_relation_network = KAN([28 * 28, 128, 8])  # 定义关系网络
    gearbox_relation_network_2 = KAN([8 * 512, 512, 32, 2])
    motor_feature_encoder = CNNEncoder1.rsnet()  # 特征提取
    motor_relation_network = KAN([28 * 28, 128, 8])  # 定义关系网络
    motor_relation_network_2 = KAN([8 * 512, 512, 32, 2])
    leftaxlebox_feature_encoder = CNNEncoder1.rsnet()  # 特征提取
    leftaxlebox_relation_network = KAN([28 * 28, 128, 8])  # 定义关系网络
    leftaxlebox_relation_network_2 = KAN([8 * 512, 512, 32, 2])
    gearbox_feature_encoder.cuda(GPU)
    gearbox_relation_network.cuda(GPU)
    gearbox_relation_network_2.cuda(GPU)
    leftaxlebox_feature_encoder.cuda(GPU)
    leftaxlebox_relation_network.cuda(GPU)
    leftaxlebox_relation_network_2.cuda(GPU)
    motor_feature_encoder.cuda(GPU)
    motor_relation_network.cuda(GPU)
    motor_relation_network_2.cuda(GPU)

    if os.path.exists(
            str("./models/gearbox_feature_encoder_" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")):
        gearbox_feature_encoder.load_state_dict(torch.load(
            str("./models/gearbox_feature_encoder_" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")))
        print("load gearbox feature encoder success")
    if os.path.exists(
            str("./models/gearbox_relation_network_" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")):
        gearbox_relation_network.load_state_dict(torch.load(
            str("./models/gearbox_relation_network_" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")))
        print("load gearbox relation network success")
    if os.path.exists(
            str("./models/gearbox_relation_network_2" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")):
        gearbox_relation_network_2.load_state_dict(torch.load(
            str("./models/gearbox_relation_network_2" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")))
        print("load gearbox relation network2 success")
    if os.path.exists(
            str("./models/leftaxlebox_feature_encoder_" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")):
        leftaxlebox_feature_encoder.load_state_dict(torch.load(
            str("./models/leftaxlebox_feature_encoder_" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")))
        print("load leftaxlebox feature encoder success")
    if os.path.exists(
            str("./models/leftaxlebox_relation_network_" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")):
        leftaxlebox_relation_network.load_state_dict(torch.load(
            str("./models/leftaxlebox_relation_network_" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")))
        print("load leftaxlebox relation network success")
    if os.path.exists(
            str("./models/leftaxlebox_relation_network_2" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")):
        leftaxlebox_relation_network_2.load_state_dict(torch.load(
            str("./models/leftaxlebox_relation_network_2" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")))
        print("load leftaxlebox relation network2 success")

    if os.path.exists(
            str("./models/motor_feature_encoder_" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")):
        motor_feature_encoder.load_state_dict(torch.load(
            str("./models/motor_feature_encoder_" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")))
        print("load motor feature encoder success")
    if os.path.exists(
            str("./models/motor_relation_network_" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")):
        motor_relation_network.load_state_dict(torch.load(
            str("./models/motor_relation_network_" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")))
        print("load motor relation network success")
    if os.path.exists(
            str("./models/motor_relation_network_2" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")):
        motor_relation_network_2.load_state_dict(torch.load(
            str("./models/motor_relation_network_2" + str(CLASS_NUM) + "way_" + str(
                SAMPLE_NUM_PER_CLASS) + "shot.pkl")))
        print("load motor relation network2 success")

    # Step 3: build graph
    for num_wc in range(1, 9 + 1):
        relation_score_list = [[] for _ in range(5)]
        for num_fault_type in range(1, 4 + 1):
            for ten_epoches in range(1, 11):
                for i in range(TEST_EPISODE):
                    degrees = random.choice([0, 90, 180, 270])
                    metatest_character_folders1 = [f'../CWT3-1000/leftaxlebox/test/health/WC{num_wc}',
                                                   f'../CWT3-1000/leftaxlebox/test/LA{num_fault_type}/anomaly/WC{num_wc}']
                    metatrain_character_folders1 = [f'../CWT3-1000/leftaxlebox/train/health/WC{num_wc}',
                                                    '../CWT3-1000/leftaxlebox/train/anomaly']
                    task = tg.OmniglotTask(metatest_character_folders1, CLASS_NUM, SAMPLE_NUM_PER_CLASS,
                                           SAMPLE_NUM_PER_CLASS, )
                    task1 = tg.OmniglotTask(metatrain_character_folders1, CLASS_NUM, SAMPLE_NUM_PER_CLASS,
                                            BATCH_NUM_PER_CLASS)
                    sample_dataloader = tg.get_data_loader(task1, num_per_class=SAMPLE_NUM_PER_CLASS, split="train",
                                                           shuffle=False, rotation=degrees)
                    test_dataloader = tg.get_data_loader(task, num_per_class=SAMPLE_NUM_PER_CLASS, split="test",
                                                         shuffle=True, rotation=degrees)
                    sample_dataloader = iter(sample_dataloader)
                    sample_images, sample_labels = next(sample_dataloader)
                    test_dataloader = iter(test_dataloader)
                    test_images, test_labels = next(test_dataloader)
                    sample_features = leftaxlebox_feature_encoder(Variable(sample_images).cuda(GPU))  # 5x64
                    test_features = leftaxlebox_feature_encoder(Variable(test_images).cuda(GPU))  # 20x64
                    sample_features_ext = sample_features.unsqueeze(0).repeat(SAMPLE_NUM_PER_CLASS * CLASS_NUM, 1, 1, 1,
                                                                              1)
                    test_features_ext = test_features.unsqueeze(0).repeat(SAMPLE_NUM_PER_CLASS * CLASS_NUM, 1, 1, 1, 1)
                    test_features_ext = torch.transpose(test_features_ext, 0, 1)
                    relation_pairs = torch.cat((sample_features_ext, test_features_ext), 2).view(-1,
                                                                                                 FEATURE_DIM * 4,
                                                                                                 28 * 28)

                    relations1 = leftaxlebox_relation_network(relation_pairs)
                    relations1 = relations1.view(2, 8 * 512)
                    relations1 = leftaxlebox_relation_network_2(relations1)
                    relations = relations1.view(-1, CLASS_NUM)
                    # print(relations.shape)

                    # print(relations)
                    # print(relations)
                    for j in range(len(relations)):
                        if test_labels[j]==1:
                            relation_score_list[num_fault_type].append(relations[j][0].cpu().item())
                        elif num_fault_type==2:
                            relation_score_list[0].append(relations[j][0].cpu().item())

        relation_score_list=pd.DataFrame(relation_score_list).T
        file_path_rs = os.path.join('test_result', 'relation_scores','leftaxlebox', f'WC{num_wc}.csv')
        # 保存为 CSV 文件
        relation_score_list.to_csv(file_path_rs, index=False, header=False)


    return 0


if __name__ == '__main__':
    main()
